import psycopg2
import re
import uuid
import os
from datetime import datetime, timedelta

# pyrefly: ignore [missing-import]
from werkzeug.security import check_password_hash, generate_password_hash
# pyrefly: ignore [missing-import]
from werkzeug.utils import secure_filename

from config import DIAS_SEMANA, MESES_ES
from database import get_db_connection
from utils import (
    direccion_existe,
    generar_id_curso,
    normalizar_direccion,
    normalizar_vista_admin,
    obtener_direcciones,
    registrar_evento_matricula,
)


def _fecha_iso_desde_partes_curso(anio, mes_nombre, dia):
    try:
        anio_int = int(str(anio).strip())
        dia_int = int(str(dia).strip())
    except (TypeError, ValueError):
        return None

    meses_map = {nombre.lower(): idx + 1 for idx, nombre in enumerate(MESES_ES)}
    mes_int = meses_map.get((mes_nombre or '').strip().lower())
    if not mes_int:
        return None

    try:
        return datetime(anio_int, mes_int, dia_int).strftime('%Y-%m-%d')
    except ValueError:
        return None


def _fecha_mostrar_desde_iso(fecha_iso):
    if not fecha_iso:
        return ''
    if hasattr(fecha_iso, 'strftime'):
        return fecha_iso.strftime('%d/%m/%Y')
    try:
        return datetime.strptime(str(fecha_iso).strip(), '%Y-%m-%d').strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return str(fecha_iso)


def _mes_numero_desde_nombre(nombre):
    if not nombre:
        return None
    nombre_norm = (nombre or '').strip().lower()
    for idx, mes in enumerate(MESES_ES, start=1):
        if mes.lower() == nombre_norm:
            return idx
    return None


def _mes_nombre_desde_numero(valor):
    try:
        idx = int(valor)
    except (TypeError, ValueError):
        return valor or ''
    if 1 <= idx <= len(MESES_ES):
        return MESES_ES[idx - 1]
    return valor or ''


def _etiqueta_horario_edicion(jornada, hora):
    jornada_norm = _normalizar_jornada(jornada)
    hora_texto = (hora or '').strip()
    if not hora_texto:
        return _nombre_jornada(jornada_norm)
    if _nombre_jornada(jornada_norm).lower() in hora_texto.lower():
        return hora_texto
    return f"{_nombre_jornada(jornada_norm)} {hora_texto}".strip()


def _generar_id_edicion(conn, catalogo_id):
    with conn.cursor() as cur:
        cur.execute(
            'SELECT id FROM ediciones_formativas WHERE id LIKE %s ORDER BY id ASC',
            (f'{catalogo_id}-E%',),
        )
        existentes = cur.fetchall()

    ultimo = 0
    patron = re.compile(rf'^{re.escape(catalogo_id)}-E(\d{{3}})$')
    for row in existentes:
        match = patron.match((row['id'] or '').upper())
        if match:
            ultimo = max(ultimo, int(match.group(1)))

    return f'{catalogo_id}-E{ultimo + 1:03d}'


def _sincronizar_edicion_desde_sesiones(conn, edicion_id, jornada=None, hora_texto=None):
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT fecha, hora_inicio, hora_fin
            FROM sesiones_curso
            WHERE edicion_id = %s
            ORDER BY fecha ASC, hora_inicio ASC
            LIMIT 1
            ''',
            (edicion_id,),
        )
        primer = cur.fetchone()

    fecha_inicio = (primer['fecha'] or '').strip() if primer else ''
    if not hora_texto and primer:
        hora_inicio = (primer['hora_inicio'] or '').strip()[:5]
        hora_fin = (primer['hora_fin'] or '').strip()[:5]
        if hora_inicio and hora_fin:
            hora_texto = f'{hora_inicio}-{hora_fin}'

    campos = []
    params = []
    if fecha_inicio:
        campos.append('fecha_inicio = %s')
        params.append(fecha_inicio)
    if jornada:
        campos.append('jornada = %s')
        params.append(_normalizar_jornada(jornada))
    if hora_texto is not None:
        campos.append('hora = %s')
        params.append(hora_texto)

    if not campos:
        return

    params.append(edicion_id)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE ediciones_formativas SET {', '.join(campos)} WHERE id = %s",
            tuple(params),
        )


def _normalizar_duracion_tipo(valor):
    duracion = (valor or '').strip().lower()
    if duracion not in {'un_dia', 'varios_dias'}:
        return 'un_dia'
    return duracion


TIPOS_ACCION_FORMATIVA = {'CONFERENCIA', 'SEMINARIO', 'SEMINARIO-TALLER' ,'CURSO'}
JORNADAS_SESION = {'UNICA', 'MATUTINA', 'VESPERTINA', 'NOCTURNA'}
ORDEN_JORNADAS_REPORTE = ['UNICA', 'MATUTINA', 'VESPERTINA', 'NOCTURNA', 'POR_CONFIRMAR']


def _normalizar_tipo_accion(valor):
    tipo = (valor or '').strip().upper()
    if tipo not in TIPOS_ACCION_FORMATIVA:
        return 'CURSO'
    return tipo


def _normalizar_jornada(valor):
    jornada = (valor or '').strip().upper()
    if jornada not in JORNADAS_SESION:
        return 'UNICA'
    return jornada


def _nombre_jornada(jornada):
    jornada_norm = (jornada or '').strip().upper()
    nombres = {
        'UNICA': 'Unica',
        'MATUTINA': 'Matutina',
        'VESPERTINA': 'Vespertina',
        'NOCTURNA': 'Nocturna',
        'POR_CONFIRMAR': 'Por confirmar',
    }
    return nombres.get(jornada_norm, 'Unica')


def _etiqueta_horario_jornada(jornada, hora_inicio, hora_fin):
    jornada_norm = _normalizar_jornada(jornada)
    return f"{_nombre_jornada(jornada_norm)} {hora_inicio}-{hora_fin}"


def _normalizar_hora_desde_texto(valor):
    texto = (valor or '').strip().upper().replace('.', ':')
    if not texto:
        return None

    for formato in ('%H:%M', '%I:%M %p', '%I:%M%p'):
        try:
            return datetime.strptime(texto, formato).strftime('%H:%M')
        except ValueError:
            continue
    return None


def _extraer_rango_horario(texto):
    valores = re.findall(r'\d{1,2}:\d{2}(?:\s*[APap][Mm])?', texto or '')
    if len(valores) < 2:
        return None

    inicio = _normalizar_hora_desde_texto(valores[0])
    fin = _normalizar_hora_desde_texto(valores[1])
    if not inicio or not fin:
        return None
    return inicio, fin


def _resolver_jornada_desde_horario(horario_elegido, jornadas_sesiones):
    texto = (horario_elegido or '').strip()
    texto_upper = texto.upper()
    if not texto:
        return 'POR_CONFIRMAR'

    for jornada in JORNADAS_SESION:
        if jornada in texto_upper:
            return jornada

    rango = _extraer_rango_horario(texto)
    if rango:
        jornadas_match = [
            jornada
            for jornada, meta in jornadas_sesiones.items()
            if rango in meta['rangos']
        ]
        if len(jornadas_match) == 1:
            return jornadas_match[0]

    if len(jornadas_sesiones) == 1:
        return next(iter(jornadas_sesiones.keys()))

    return 'POR_CONFIRMAR'


def _normalizar_horas_totales(valor, tipo_accion):
    try:
        horas = int(valor)
    except (TypeError, ValueError):
        horas = 0

    if horas > 0:
        return horas

    tipo = _normalizar_tipo_accion(tipo_accion)
    if tipo == 'CONFERENCIA':
        return 4
    if tipo == 'SEMINARIO':
        return 16
    return 20


def _normalizar_semanas_duracion(valor):
    try:
        semanas = int(valor)
    except (TypeError, ValueError):
        semanas = 1
    return semanas if semanas > 0 else 1


def _duracion_tipo_desde_semanas(semanas_duracion):
    return 'varios_dias' if _normalizar_semanas_duracion(semanas_duracion) > 1 else 'un_dia'


def _validar_reglas_tipo_accion(tipo_accion, horas_totales, semanas_duracion):
    tipo = _normalizar_tipo_accion(tipo_accion)
    horas = _normalizar_horas_totales(horas_totales, tipo)
    semanas = _normalizar_semanas_duracion(semanas_duracion)

    if tipo == 'CONFERENCIA':
        if horas < 1 or horas > 16:
            return 'Las conferencias deben tener entre 1 y 16 horas totales.'
        if semanas < 1 or semanas > 4:
            return 'Las conferencias deben definirse entre 1 y 4 semanas.'

    if tipo == 'SEMINARIO':
        if horas < 16:
            return 'Los seminarios deben tener al menos 16 horas totales.'
        if semanas < 1:
            return 'Los seminarios deben durar al menos 1 semana.'

    if tipo == 'CURSO':
        if horas < 20:
            return 'Los cursos deben tener al menos 20 horas totales.'
        if semanas < 1:
            return 'Los cursos deben durar al menos 1 semana.'

    return None


def authenticate_admin(username, password):
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT password_hash, rol, direccion FROM admin_users WHERE username = %s',
                    (username,),
                )
                admin = cur.fetchone()
        except psycopg2.OperationalError:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT password_hash FROM admin_users WHERE username = %s',
                    (username,),
                )
                admin = cur.fetchone()
        conn.close()

        if admin and check_password_hash(admin['password_hash'], password):
            return {
                'ok': True,
                'admin_user': username,
                'admin_rol': (
                    admin['rol']
                    if 'rol' in admin.keys()
                    else ('superadmin' if username == 'admin' else 'admin')
                ),
                'admin_direccion': admin['direccion'] if 'direccion' in admin.keys() else 'IPSD',
            }

        return {'ok': False, 'error': 'Usuario o contraseña incorrectos.'}
    except psycopg2.Error:
        return {'ok': False, 'error': 'Error de conexión con la base de datos.'}


def get_admin_dashboard_payload(vista_solicitada, anio_filtro, periodo_filtro, mes_filtro, resultado_filtro, admin_rol, admin_direccion):
    admin_direccion = normalizar_direccion(admin_direccion) or 'IPSD'
    es_superadmin = admin_rol == 'superadmin'
    vista_inicial = normalizar_vista_admin(vista_solicitada, es_superadmin)

    try:
        conn = get_db_connection()
        direcciones = obtener_direcciones(conn)
        query_matriculas = '''
            SELECT
                m.id as matricula_id,
                m.numero_empleado,
                ef.id AS edicion_id,
                ca.nombre,
                ef.periodo,
                ef.fecha_inicio,
                ef.jornada,
                ef.hora,
                m.fecha_matricula,
                m.aprobado,
                EXTRACT(YEAR FROM ef.fecha_inicio) AS anio,
                EXTRACT(MONTH FROM ef.fecha_inicio) AS mes_num,
                EXTRACT(DAY FROM ef.fecha_inicio) AS dia
            FROM matriculas m
            JOIN ediciones_formativas ef ON m.edicion_id = ef.id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE 1=1
        '''
        params = []

        if not es_superadmin:
            query_matriculas += ' AND ca.direccion_codigo = %s'
            params.append(admin_direccion)

        if anio_filtro:
            query_matriculas += " AND EXTRACT(YEAR FROM ef.fecha_inicio) = %s"
            params.append(anio_filtro)
        if periodo_filtro:
            query_matriculas += ' AND ef.periodo = %s'
            params.append(periodo_filtro)
        if mes_filtro:
            mes_num = _mes_numero_desde_nombre(mes_filtro)
            if mes_num:
                query_matriculas += " AND EXTRACT(MONTH FROM ef.fecha_inicio) = %s"
                params.append(f'{mes_num:02d}')
        if resultado_filtro == 'aprobado':
            query_matriculas += ' AND m.aprobado = 1'
        elif resultado_filtro == 'reprobado':
            query_matriculas += ' AND m.aprobado = 0'
        elif resultado_filtro == 'abandono':
            query_matriculas += ' AND m.aprobado = 2'
        elif resultado_filtro == 'pendiente':
            query_matriculas += ' AND m.aprobado IS NULL'

        query_matriculas += ' ORDER BY ef.fecha_inicio DESC, ef.id, m.numero_empleado'
        with conn.cursor() as cur:
            cur.execute(query_matriculas, params)
            registros_raw = cur.fetchall()
        registros = []
        for fila in registros_raw:
            item = dict(fila)
            item['mes'] = _mes_nombre_desde_numero(item.get('mes_num'))
            registros.append(item)

        query_cursos = '''
            SELECT
                ef.id AS edicion_id,
                ca.id AS catalogo_id,
                ca.nombre,
                ca.modalidad,
                ca.tipo_accion,
                ef.periodo,
                ef.fecha_inicio,
                ef.jornada,
                ef.hora,
                ef.cupos_maximos,
                ef.enlace_acceso,
                ef.privacidad,
                ef.estado,
                ef.etiqueta_edicion,
                ef.docente_responsable,
                ef.requisitos,
                ef.duracion_horas,
                ef.calendario_academico,
                ca.id_plantilla_certificado,
                ca.requisitos AS requisitos_catalogo,
                EXTRACT(YEAR FROM ef.fecha_inicio) AS anio,
                EXTRACT(MONTH FROM ef.fecha_inicio) AS mes_num,
                EXTRACT(DAY FROM ef.fecha_inicio) AS dia,
                COUNT(DISTINCT m.numero_empleado) as total_inscritos
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            LEFT JOIN matriculas m ON m.edicion_id = ef.id
        '''
        cursos_params = []
        if not es_superadmin:
            query_cursos += ' WHERE ca.direccion_codigo = %s'
            cursos_params.append(admin_direccion)

        query_cursos += ' GROUP BY ef.id, ca.id ORDER BY ef.fecha_inicio DESC, ef.id'
        with conn.cursor() as cur:
            cur.execute(query_cursos, cursos_params)
            cursos_raw = cur.fetchall()
        cursos = []
        for fila in cursos_raw:
            item = dict(fila)
            item['id'] = item['edicion_id']
            item['mes'] = _mes_nombre_desde_numero(item.get('mes_num'))
            item['horarios_html'] = _etiqueta_horario_edicion(item.get('jornada'), item.get('hora'))
            item['horas_totales'] = _normalizar_horas_totales(None, item.get('tipo_accion'))
            item['semanas_duracion'] = 1
            if not item.get('fecha_inicio'):
                item['horarios_html'] = ''
            cursos.append(item)

        query_catalogos = '''
            SELECT
                ca.id AS catalogo_id,
                ca.nombre,
                ca.modalidad,
                ca.tipo_accion,
                ca.id_plantilla_certificado,
                ca.direccion_codigo,
                ca.requisitos,
                COUNT(DISTINCT ef.id) as total_ediciones,
                COUNT(DISTINCT m.numero_empleado) as total_inscritos
            FROM catalogo_acciones ca
            LEFT JOIN ediciones_formativas ef ON ef.catalogo_id = ca.id
            LEFT JOIN matriculas m ON m.edicion_id = ef.id
        '''
        catalogos_params = []
        if not es_superadmin:
            query_catalogos += ' WHERE ca.direccion_codigo = %s'
            catalogos_params.append(admin_direccion)

        query_catalogos += ' GROUP BY ca.id ORDER BY ca.id'
        with conn.cursor() as cur:
            cur.execute(query_catalogos, catalogos_params)
            catalogos_raw = cur.fetchall()
        catalogos = []
        for fila in catalogos_raw:
            item = dict(fila)
            item['id'] = item['catalogo_id']
            catalogos.append(item)

        query_calendario = '''
            SELECT
                s.fecha,
                s.hora_inicio,
                s.hora_fin,
                s.estado,
                ef.id AS edicion_id,
                ca.nombre AS nombre_curso,
                ca.tipo_accion
            FROM sesiones_curso s
            JOIN ediciones_formativas ef ON ef.id = s.edicion_id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
        '''
        calendario_params = []
        if not es_superadmin:
            query_calendario += ' WHERE ca.direccion_codigo = %s'
            calendario_params.append(admin_direccion)

        query_calendario += ' ORDER BY s.fecha ASC, s.hora_inicio ASC, ef.id ASC'
        with conn.cursor() as cur:
            cur.execute(query_calendario, calendario_params)
            calendario_sesiones = cur.fetchall()

        cursos_con_sesion = set()
        calendario_eventos = []
        for fila in calendario_sesiones:
            fecha_val = fila['fecha']
            if hasattr(fecha_val, 'strftime'):
                fecha_iso = fecha_val.strftime('%Y-%m-%d')
            else:
                fecha_iso = (fecha_val or '').strip()
            if not fecha_iso:
                continue

            edicion_id = (fila['edicion_id'] or '').strip().upper()
            if edicion_id:
                cursos_con_sesion.add(edicion_id)

            calendario_eventos.append(
                {
                    'tipo_evento': 'sesion',
                    'fecha_iso': fecha_iso,
                    'fecha_mostrar': _fecha_mostrar_desde_iso(fecha_val),
                    'hora_inicio': fila['hora_inicio'],
                    'hora_fin': fila['hora_fin'],
                    'id_curso': edicion_id,
                    'edicion_id': edicion_id,
                    'nombre_curso': fila['nombre_curso'],
                    'estado': fila['estado'],
                    'tipo_accion': _normalizar_tipo_accion(fila['tipo_accion']),
                }
            )

        for curso in cursos:
            edicion_id = (curso.get('edicion_id') or '').strip().upper()
            if not edicion_id or edicion_id in cursos_con_sesion:
                continue

            fecha_val = curso.get('fecha_inicio')
            if hasattr(fecha_val, 'strftime'):
                fecha_iso = fecha_val.strftime('%Y-%m-%d')
            else:
                fecha_iso = (fecha_val or '').strip()[:10]
            if not fecha_iso:
                continue

            calendario_eventos.append(
                {
                    'tipo_evento': 'curso',
                    'fecha_iso': fecha_iso,
                    'fecha_mostrar': _fecha_mostrar_desde_iso(fecha_iso),
                    'hora_inicio': None,
                    'hora_fin': None,
                    'id_curso': edicion_id,
                    'edicion_id': edicion_id,
                    'nombre_curso': curso.get('nombre'),
                    'estado': None,
                    'tipo_accion': _normalizar_tipo_accion(curso.get('tipo_accion')),
                }
            )

        calendario_eventos.sort(
            key=lambda evento: (
                evento.get('fecha_iso') or '',
                evento.get('hora_inicio') or '99:99',
                evento.get('id_curso') or '',
            )
        )

        periodo_actual = ['I PAC', 'II PAC', 'III PAC', 'III PAC'][(datetime.now().month - 1) // 3]
        query_ediciones_periodo = '''
            SELECT COUNT(*)
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE ef.periodo = %s
              AND (ef.estado IS NULL OR ef.estado NOT IN ('Finalizada', 'Cancelada'))
        '''
        periodo_params = [periodo_actual]
        if not es_superadmin:
            query_ediciones_periodo += ' AND ca.direccion_codigo = %s'
            periodo_params.append(admin_direccion)

        with conn.cursor() as cur:
            cur.execute(
                query_ediciones_periodo,
                periodo_params,
            )
            ediciones_periodo_actual = cur.fetchone()[0]

        if es_superadmin:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM matriculas')
                total_matriculas = cur.fetchone()[0]
                cur.execute('SELECT COUNT(*) FROM ediciones_formativas')
                total_cursos = cur.fetchone()[0]
                cur.execute('SELECT COUNT(DISTINCT numero_empleado) FROM matriculas')
                total_profesores = cur.fetchone()[0]
        else:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT COUNT(*)
                    FROM matriculas m
                    JOIN ediciones_formativas ef ON ef.id = m.edicion_id
                    JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                    WHERE ca.direccion_codigo = %s
                    ''',
                    (admin_direccion,),
                )
                total_matriculas = cur.fetchone()[0]

                cur.execute(
                    '''
                    SELECT COUNT(*)
                    FROM ediciones_formativas ef
                    JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                    WHERE ca.direccion_codigo = %s
                    ''',
                    (admin_direccion,),
                )
                total_cursos = cur.fetchone()[0]

                cur.execute(
                    '''
                    SELECT COUNT(DISTINCT m.numero_empleado)
                    FROM matriculas m
                    JOIN ediciones_formativas ef ON ef.id = m.edicion_id
                    JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                    WHERE ca.direccion_codigo = %s
                    ''',
                    (admin_direccion,),
                )
                total_profesores = cur.fetchone()[0]

        stats = {
            'total_matriculas': total_matriculas,
            'total_cursos': total_cursos,
            'total_profesores': total_profesores,
            'ediciones_periodo_actual': ediciones_periodo_actual,
            'periodo_actual': periodo_actual,
        }

        usuarios_admin = []
        direcciones_gestion = []
        if es_superadmin:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT username, rol, direccion
                    FROM admin_users
                    ORDER BY CASE WHEN rol = 'superadmin' THEN 0 ELSE 1 END, username
                    '''
                )
                usuarios_admin = cur.fetchall()

                cur.execute(
                    '''
                    SELECT
                        d.codigo,
                        d.nombre,
                        d.ruta_firma_img,
                        COUNT(DISTINCT a.id) AS total_admins,
                        COUNT(DISTINCT ca.id) AS total_cursos
                    FROM direcciones d
                    LEFT JOIN admin_users a
                        ON a.direccion = d.codigo AND a.rol = 'admin'
                    LEFT JOIN catalogo_acciones ca
                        ON ca.direccion_codigo = d.codigo
                    GROUP BY d.codigo, d.nombre, d.ruta_firma_img
                    ORDER BY d.codigo
                    '''
                )
                direcciones_gestion = cur.fetchall()

        conn.close()

        return {
            'ok': True,
            'admin_direccion': admin_direccion,
            'es_superadmin': es_superadmin,
            'vista_inicial': vista_inicial,
            'direcciones': direcciones,
            'registros': registros,
            'cursos': cursos,
            'catalogos': catalogos,
            'calendario_eventos': calendario_eventos,
            'stats': stats,
            'usuarios_admin': usuarios_admin,
            'direcciones_gestion': direcciones_gestion,
            'filtros': {
                'anio': anio_filtro,
                'periodo': periodo_filtro,
                'mes': mes_filtro,
                'resultado': resultado_filtro,
            },
        }
    except psycopg2.Error:
        return {
            'ok': False,
            'admin_direccion': admin_direccion,
            'es_superadmin': es_superadmin,
            'vista_inicial': vista_inicial,
            'direcciones': [],
            'registros': [],
            'cursos': [],
            'catalogos': [],
            'calendario_eventos': [],
            'stats': {
                'total_matriculas': 0,
                'total_cursos': 0,
                'total_profesores': 0,
                'ediciones_periodo_actual': 0,
                'periodo_actual': 'I',
            },
            'usuarios_admin': [],
            'direcciones_gestion': [],
            'filtros': {
                'anio': anio_filtro,
                'periodo': periodo_filtro,
                'mes': mes_filtro,
                'resultado': resultado_filtro,
            },
        }


def get_admin_stats_payload(admin_rol, admin_direccion):
    admin_direccion = normalizar_direccion(admin_direccion) or 'IPSD'

    try:
        conn = get_db_connection()

        where_stats = ''
        params = []
        if admin_rol != 'superadmin':
            where_stats = ' WHERE ca.direccion_codigo = %s '
            params.append(admin_direccion)

        with conn.cursor() as cur:
            cur.execute(
                f'''
                SELECT ca.nombre, COUNT(m.numero_empleado) as total
                FROM ediciones_formativas ef
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                LEFT JOIN matriculas m ON ef.id = m.edicion_id
                {where_stats}
                GROUP BY ef.id, ca.id
                ORDER BY total DESC
                LIMIT 10
                ''',
                params,
            )
            datos_cursos = cur.fetchall()

            cur.execute(
                f'''
                SELECT TO_CHAR(m.fecha_matricula, 'MM YYYY') as periodo, COUNT(m.id) as total
                FROM matriculas m
                JOIN ediciones_formativas ef ON m.edicion_id = ef.id
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                {where_stats}
                GROUP BY periodo
                ORDER BY MAX(m.fecha_matricula) DESC
                LIMIT 12
                ''',
                params,
            )
            datos_meses = cur.fetchall()

        conn.close()

        return {
            'ok': True,
            'cursos': {
                'labels': [r['nombre'] for r in datos_cursos],
                'data': [r['total'] for r in datos_cursos],
            },
            'meses': {
                'labels': [r['periodo'] for r in datos_meses],
                'data': [r['total'] for r in datos_meses],
            },
        }
    except psycopg2.Error:
        return {'ok': False, 'cursos': {'labels': [], 'data': []}, 'meses': {'labels': [], 'data': []}}


def fetch_export_records(anio_filtro, periodo_filtro, mes_filtro, resultado_filtro, admin_rol, admin_direccion):
    admin_direccion = normalizar_direccion(admin_direccion) or 'IPSD'

    try:
        conn = get_db_connection()

        query = '''
            SELECT m.numero_empleado,
                   ef.id AS edicion_id,
                   ca.nombre,
                   ef.periodo,
                   ef.fecha_inicio,
                   ef.jornada,
                   ef.hora,
                   m.fecha_matricula,
                   m.aprobado,
                   EXTRACT(YEAR FROM ef.fecha_inicio) AS anio,
                   EXTRACT(MONTH FROM ef.fecha_inicio) AS mes_num
            FROM matriculas m
            JOIN ediciones_formativas ef ON m.edicion_id = ef.id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE 1=1
        '''
        params = []
        if admin_rol != 'superadmin':
            query += ' AND ca.direccion_codigo = %s'
            params.append(admin_direccion)
        if anio_filtro:
            query += " AND EXTRACT(YEAR FROM ef.fecha_inicio) = %s"
            params.append(anio_filtro)
        if periodo_filtro:
            query += ' AND ef.periodo = %s'
            params.append(periodo_filtro)
        if mes_filtro:
            mes_num = _mes_numero_desde_nombre(mes_filtro)
            if mes_num:
                query += " AND EXTRACT(MONTH FROM ef.fecha_inicio) = %s"
                params.append(f'{mes_num:02d}')
        if resultado_filtro == 'aprobado':
            query += ' AND m.aprobado = 1'
        elif resultado_filtro == 'reprobado':
            query += ' AND m.aprobado = 0'
        elif resultado_filtro == 'abandono':
            query += ' AND m.aprobado = 2'
        elif resultado_filtro == 'pendiente':
            query += ' AND m.aprobado IS NULL'

        query += ' ORDER BY ef.fecha_inicio DESC, ef.id, m.numero_empleado'
        with conn.cursor() as cur:
            cur.execute(query, params)
            registros_raw = cur.fetchall()
        registros = []
        for fila in registros_raw:
            item = dict(fila)
            item['mes'] = _mes_nombre_desde_numero(item.get('mes_num'))
            registros.append(item)
        conn.close()
        return {'ok': True, 'registros': registros}
    except psycopg2.Error:
        return {'ok': False, 'registros': []}


def update_matricula_resultado(
    numero_empleado,
    edicion_id,
    matricula_id,
    aprobado,
    estado_codigo,
    admin_rol,
    admin_direccion,
    comentario_validacion=None,
):
    admin_direccion = normalizar_direccion(admin_direccion) or 'IPSD'

    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT m.id, ca.nombre, m.edicion_id, ca.direccion_codigo
                FROM matriculas m
                JOIN ediciones_formativas ef ON ef.id = m.edicion_id
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                WHERE m.id = %s AND m.numero_empleado = %s
                ''',
                (matricula_id, numero_empleado),
            )
            matricula_actual = cur.fetchone()

        if not matricula_actual:
            conn.close()
            return {'ok': False, 'error': 'Matrícula no encontrada', 'status_code': 404}

        real_edicion_id = matricula_actual['edicion_id']
        
        if admin_rol != 'superadmin':
            if matricula_actual['direccion_codigo'] != admin_direccion:
                conn.close()
                return {'ok': False, 'error': 'No autorizado para esta acción', 'status_code': 403}

        comentario_limpio = (comentario_validacion or '').strip()
        comentario_db = comentario_limpio if comentario_limpio else None

        # Actualizar aprobación y fecha de aprobación si corresponde
        if aprobado == 1:
            fecha_aprobacion = datetime.now().strftime('%Y-%m-%d')
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE matriculas SET aprobado = %s, fecha_aprobacion = %s, comentario_validacion = %s WHERE id = %s',
                    (aprobado, fecha_aprobacion, comentario_db, matricula_id),
                )
                rowcount = cur.rowcount
        else:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE matriculas SET aprobado = %s, fecha_aprobacion = NULL, comentario_validacion = %s WHERE id = %s',
                    (aprobado, comentario_db, matricula_id),
                )
                rowcount = cur.rowcount

        detalle_evento = 'Resultado actualizado desde panel administrativo'
        if comentario_limpio:
            detalle_evento = f"{detalle_evento}. Comentario: {comentario_limpio}"

        registrar_evento_matricula(
            conn,
            numero_empleado=numero_empleado,
            edicion_id=real_edicion_id,
            nombre_accion=matricula_actual['nombre'],
            estado_codigo=estado_codigo,
            matricula_id=matricula_id,
            detalle=detalle_evento,
        )

        conn.commit()
        conn.close()

        if rowcount == 0:
            return {'ok': False, 'error': 'Matrícula no encontrada', 'status_code': 404}

        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudo actualizar el resultado', 'status_code': 500}


def actualizar_catalogo_accion(catalogo_id, nombre, modalidad, tipo_accion, id_plantilla_certificado=None, requisitos=None):
    catalogo_id = (catalogo_id or '').strip().upper()
    if not catalogo_id or not nombre:
        return {'ok': False, 'error': 'ID y nombre son obligatorios.'}
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE catalogo_acciones
                SET nombre = %s, modalidad = %s, tipo_accion = %s, id_plantilla_certificado = %s, requisitos = %s
                WHERE id = %s
                ''',
                (nombre, modalidad, tipo_accion, id_plantilla_certificado or None, requisitos or '', catalogo_id)
            )
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error as e:
        return {'ok': False, 'error': f'Error al actualizar catálogo: {str(e)}'}

def eliminar_catalogo_accion(catalogo_id):
    catalogo_id = (catalogo_id or '').strip().upper()
    if not catalogo_id:
        return {'ok': False, 'error': 'ID de catálogo inválido.'}
        
    try:
        conn = get_db_connection()
        # El ON DELETE CASCADE se encarga de las ediciones y matrículas
        with conn.cursor() as cur:
            cur.execute('DELETE FROM catalogo_acciones WHERE id = %s', (catalogo_id,))
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error as e:
        return {'ok': False, 'error': f'Error al eliminar catálogo: {str(e)}'}


def create_curso_records(
    nombre_curso,
    modalidad,
    tipo_accion,
    direccion_curso,
    id_plantilla_certificado=None,
):
    try:
        conn = get_db_connection()
        if not direccion_existe(conn, direccion_curso):
            conn.close()
            return {'ok': False, 'invalid_direction': True}

        tipo_accion_norm = _normalizar_tipo_accion(tipo_accion)

        catalogo_id = generar_id_curso(conn, direccion_curso, modalidad)
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO catalogo_acciones
                (id, nombre, modalidad, tipo_accion, id_plantilla_certificado, direccion_codigo)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    catalogo_id,
                    nombre_curso,
                    modalidad,
                    tipo_accion_norm,
                    id_plantilla_certificado,
                    direccion_curso,
                ),
            )

        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.IntegrityError as e:
        print(f"Error al crear: {e}")
        return {'ok': False}
    except psycopg2.Error as e:
        print(f"Error al crear: {e}")
        return {'ok': False}
    except Exception as e:
        print(f"Error al crear: {e}")
        return {'ok': False}


def update_edicion_metadata(
    edicion_id,
    periodo=None,
    fecha_inicio=None,
    cupos_maximos=None,
    jornada=None,
    hora=None,
    docente_responsable=None,
    persona_apoyo=None,
    etiqueta_edicion=None,
    privacidad=None,
    fecha_limite_matricula=None,
    enlace_acceso=None,
    requisitos=None,
    duracion_horas=None,
    estado=None,
    calendario_academico=None,
):
    try:
        conn = get_db_connection()

        campos = []
        params = []

        if periodo:
            campos.append('periodo = %s')
            params.append(periodo)

        if fecha_inicio:
            campos.append('fecha_inicio = %s')
            params.append(fecha_inicio)

        if cupos_maximos is not None:
            campos.append('cupos_maximos = %s')
            params.append(cupos_maximos)

        if jornada is not None:
            campos.append('jornada = %s')
            params.append(_normalizar_jornada(jornada))

        if hora is not None:
            campos.append('hora = %s')
            params.append(hora)

        if docente_responsable is not None:
            campos.append('docente_responsable = %s')
            params.append(docente_responsable)

        if persona_apoyo is not None:
            campos.append('persona_apoyo = %s')
            params.append(persona_apoyo)

        if etiqueta_edicion is not None:
            campos.append('etiqueta_edicion = %s')
            params.append(etiqueta_edicion)

        if privacidad is not None:
            campos.append('privacidad = %s')
            params.append(privacidad)

        if fecha_limite_matricula is not None:
            campos.append('fecha_limite_matricula = %s')
            valor_fecha_limite = fecha_limite_matricula or None
            params.append(valor_fecha_limite)

        if enlace_acceso is not None:
            campos.append('enlace_acceso = %s')
            params.append(enlace_acceso)

        if requisitos is not None:
            campos.append('requisitos = %s')
            params.append(requisitos)

        if duracion_horas is not None:
            campos.append('duracion_horas = %s')
            params.append(duracion_horas)

        if estado is not None:
            campos.append('estado = %s')
            params.append(estado)

        if calendario_academico is not None:
            campos.append('calendario_academico = %s')
            params.append(calendario_academico)

        if not campos:
            conn.close()
            return {'ok': True}

        params.append(edicion_id)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE ediciones_formativas SET {', '.join(campos)} WHERE id = %s",
                tuple(params),
            )
            rowcount = cur.rowcount
        conn.commit()
        conn.close()

        if rowcount == 0:
            return {'ok': False, 'not_found': True}
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}


def obtener_catalogo_id_por_edicion(edicion_id):
    edicion_id_limpio = (edicion_id or '').strip().upper()
    if not edicion_id_limpio:
        return None

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT catalogo_id FROM ediciones_formativas WHERE id = %s LIMIT 1',
                (edicion_id_limpio,),
            )
            fila = cur.fetchone()
        conn.close()
        return fila['catalogo_id'] if fila else None
    except psycopg2.Error:
        return None


def listar_ediciones_catalogo(catalogo_id):
    catalogo_id_limpio = (catalogo_id or '').strip().upper()
    if not catalogo_id_limpio:
        return []

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, catalogo_id, etiqueta_edicion, periodo, fecha_inicio, fecha_limite_matricula,
                         jornada, hora, cupos_maximos, enlace_acceso, docente_responsable, persona_apoyo,
                         privacidad, estado, requisitos, duracion_horas, calendario_academico
                FROM ediciones_formativas
                WHERE catalogo_id = %s
                ORDER BY id ASC
                ''',
                (catalogo_id_limpio,),
            )
            ediciones = cur.fetchall()
        conn.close()
        return ediciones
    except psycopg2.Error:
        return []


def crear_edicion_formativa(
    catalogo_id,
    periodo=None,
    fecha_inicio=None,
    fecha_limite_matricula=None,
    jornada='UNICA',
    hora='',
    cupos_maximos=None,
    enlace_acceso=None,
    docente_responsable='',
    persona_apoyo='',
    privacidad='Abierta',
    estado='En Edicion',
    etiqueta_edicion='',
    requisitos='',
    duracion_horas=None,
    calendario_academico=None,
    mensaje_bienvenida=''
):
    catalogo_id_limpio = (catalogo_id or '').strip().upper()
    if not catalogo_id_limpio:
        return {'ok': False, 'error': 'Catalogo invalido'}

    try:
        conn = get_db_connection()
        edicion_id = _generar_id_edicion(conn, catalogo_id_limpio)
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO ediciones_formativas
                (id, catalogo_id, etiqueta_edicion, periodo, fecha_inicio, fecha_limite_matricula, jornada,
                 hora, cupos_maximos, enlace_acceso, docente_responsable, persona_apoyo, privacidad, estado,
                 requisitos, duracion_horas, calendario_academico, mensaje_bienvenida)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    edicion_id,
                    catalogo_id_limpio,
                    etiqueta_edicion,
                    periodo,
                    fecha_inicio,
                    fecha_limite_matricula,
                    _normalizar_jornada(jornada),
                    hora,
                    cupos_maximos,
                    enlace_acceso,
                    docente_responsable,
                    persona_apoyo,
                    privacidad or 'Abierta',
                    estado or 'En Edicion',
                    requisitos or '',
                    duracion_horas,
                    calendario_academico,
                    mensaje_bienvenida or '',
                ),
            )
        conn.commit()
        conn.close()
        return {'ok': True, 'edicion_id': edicion_id}
    except psycopg2.Error:
        return {'ok': False}


def update_curso_record(
    id_curso,
    nombre_curso,
    anio,
    periodo,
    mes,
    dia,
    modalidad,
    tipo_accion,
    horas_totales,
    semanas_duracion,
    cupos_maximos,
    enlace_virtual,
    dia_semana,
    id_plantilla_certificado=None,
):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT catalogo_id FROM ediciones_formativas WHERE id = %s',
                (id_curso,),
            )
            curso = cur.fetchone()

        if not curso:
            conn.close()
            return {'ok': False, 'not_found': True}

        tipo_accion_norm = _normalizar_tipo_accion(tipo_accion)
        horas_totales_norm = _normalizar_horas_totales(horas_totales, tipo_accion_norm)
        semanas_duracion_norm = _normalizar_semanas_duracion(semanas_duracion)
        error_regla = _validar_reglas_tipo_accion(tipo_accion_norm, horas_totales_norm, semanas_duracion_norm)
        if error_regla:
            conn.close()
            return {'ok': False, 'validation_error': error_regla}

        fecha_iso = _fecha_iso_desde_partes_curso(anio, mes, dia)

        if fecha_iso:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    UPDATE ediciones_formativas
                    SET periodo = %s,
                        fecha_inicio = %s,
                        fecha_limite_matricula = %s,
                        cupos_maximos = %s,
                        enlace_acceso = %s
                    WHERE id = %s
                    ''',
                    (
                        periodo,
                        fecha_iso,
                        fecha_iso,
                        cupos_maximos,
                        enlace_virtual,
                        id_curso,
                    ),
                )

        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE catalogo_acciones
                SET nombre = %s, modalidad = %s, tipo_accion = %s, id_plantilla_certificado = %s
                WHERE id = %s
                ''',
                (
                    nombre_curso,
                    modalidad,
                    tipo_accion_norm,
                    id_plantilla_certificado,
                    curso['catalogo_id'],
                ),
            )

        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}


def create_admin_user_record(username, password, direccion):
    try:
        conn = get_db_connection()

        if not direccion_existe(conn, direccion):
            conn.close()
            return {'ok': False, 'invalid_direction': True}

        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO admin_users (username, password_hash, rol, direccion) VALUES (%s, %s, %s, %s)',
                (username, generate_password_hash(password), 'admin', direccion),
            )
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.IntegrityError:
        return {'ok': False}
    except psycopg2.Error:
        return {'ok': False}


def update_admin_user_record(username, new_password, direccion):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT rol FROM admin_users WHERE username = %s',
                (username,),
            )
            admin_objetivo = cur.fetchone()

        if not admin_objetivo or admin_objetivo['rol'] == 'superadmin' or not direccion_existe(conn, direccion):
            conn.close()
            return {'ok': False, 'not_allowed': True}

        if new_password:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE admin_users SET direccion = %s, password_hash = %s WHERE username = %s',
                    (direccion, generate_password_hash(new_password), username),
                )
        else:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE admin_users SET direccion = %s WHERE username = %s',
                    (direccion, username),
                )

        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}


def delete_admin_user_record(username):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT rol FROM admin_users WHERE username = %s',
                (username,),
            )
            admin_objetivo = cur.fetchone()

        if not admin_objetivo or admin_objetivo['rol'] == 'superadmin':
            conn.close()
            return {'ok': False, 'not_allowed': True}

        with conn.cursor() as cur:
            cur.execute('DELETE FROM admin_users WHERE username = %s', (username,))
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}


def create_direccion_record(codigo, nombre):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO direcciones (codigo, nombre) VALUES (%s, %s)',
                (codigo, nombre),
            )
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.IntegrityError:
        return {'ok': False}
    except psycopg2.Error:
        return {'ok': False}


def update_direccion_record(codigo_actual, codigo_nuevo, nombre_nuevo, ruta_firma_img=None, ruta_logo_img=None):
    try:
        conn = get_db_connection()

        if not direccion_existe(conn, codigo_actual):
            conn.close()
            return {'ok': False, 'not_found': True}

        if codigo_actual != codigo_nuevo:
            if direccion_existe(conn, codigo_nuevo):
                conn.close()
                return {'ok': False, 'duplicate': True}

            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE catalogo_acciones SET direccion_codigo = %s WHERE direccion_codigo = %s',
                    (codigo_nuevo, codigo_actual),
                )

                cur.execute(
                    'UPDATE admin_users SET direccion = %s WHERE direccion = %s AND rol = %s',
                    (codigo_nuevo, codigo_actual, 'admin'),
                )

                cur.execute(
                    'UPDATE direcciones SET codigo = %s, nombre = %s WHERE codigo = %s',
                    (codigo_nuevo, nombre_nuevo, codigo_actual),
                )
        else:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE direcciones SET nombre = %s WHERE codigo = %s',
                    (nombre_nuevo, codigo_actual),
                )

        if ruta_firma_img is not None:
            codigo_destino = codigo_nuevo if codigo_actual != codigo_nuevo else codigo_actual
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE direcciones SET ruta_firma_img = %s WHERE codigo = %s',
                    (ruta_firma_img, codigo_destino),
                )

        if ruta_logo_img is not None:
            codigo_destino = codigo_nuevo if codigo_actual != codigo_nuevo else codigo_actual
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE direcciones SET ruta_logo_img = %s WHERE codigo = %s',
                    (ruta_logo_img, codigo_destino),
                )

        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}


def actualizar_identidad_direccion(direccion_codigo, file_firma, file_logo, upload_folder):
    try:
        conn = get_db_connection()
        if not direccion_existe(conn, direccion_codigo):
            conn.close()
            return {'ok': False, 'error': 'Dirección no encontrada.'}
            
        dir_path = os.path.join(upload_folder, direccion_codigo)
        os.makedirs(dir_path, exist_ok=True)
        
        if file_firma and file_firma.filename:
            filename_firma = 'firma.png'
            ruta_guardado_firma = os.path.join(dir_path, filename_firma)
            file_firma.save(ruta_guardado_firma)
            ruta_firma_web = f'/uploads/direcciones/{direccion_codigo}/{filename_firma}'
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE direcciones SET ruta_firma_img = %s WHERE codigo = %s',
                    (ruta_firma_web, direccion_codigo),
                )
            
        if file_logo and file_logo.filename:
            filename_orig = secure_filename(file_logo.filename)
            ext = os.path.splitext(filename_orig)[1].lower()
            filename_logo = f'logo{ext}'
            ruta_guardado_logo = os.path.join(dir_path, filename_logo)
            file_logo.save(ruta_guardado_logo)
            ruta_logo_web = f'/uploads/direcciones/{direccion_codigo}/{filename_logo}'
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE direcciones SET ruta_logo_img = %s WHERE codigo = %s',
                    (ruta_logo_web, direccion_codigo),
                )

        conn.commit()
        conn.close()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def delete_direccion_record(codigo):
    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM direcciones')
            total_direcciones = cur.fetchone()[0]
            cur.execute(
                'SELECT COUNT(*) FROM admin_users WHERE direccion = %s AND rol = %s',
                (codigo, 'admin'),
            )
            total_admins = cur.fetchone()[0]
            cur.execute(
                'SELECT COUNT(*) FROM catalogo_acciones WHERE direccion_codigo = %s',
                (codigo,),
            )
            total_cursos = cur.fetchone()[0]

        if total_direcciones <= 1 or total_admins > 0 or total_cursos > 0:
            conn.close()
            return {'ok': False, 'blocked': True}

        with conn.cursor() as cur:
            cur.execute('DELETE FROM direcciones WHERE codigo = %s', (codigo,))
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}


def delete_curso_record(id_curso):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT catalogo_id FROM ediciones_formativas WHERE id = %s',
                (id_curso,),
            )
            catalogo = cur.fetchone()

            cur.execute('DELETE FROM certificados_emitidos WHERE edicion_id = %s', (id_curso,))
            cur.execute('DELETE FROM matricula_historial WHERE edicion_id = %s', (id_curso,))
            cur.execute('DELETE FROM matriculas WHERE edicion_id = %s', (id_curso,))
            cur.execute('DELETE FROM sesiones_curso WHERE edicion_id = %s', (id_curso,))
            cur.execute('DELETE FROM ediciones_formativas WHERE id = %s', (id_curso,))

            if catalogo:
                cur.execute(
                    'SELECT 1 FROM ediciones_formativas WHERE catalogo_id = %s LIMIT 1',
                    (catalogo['catalogo_id'],),
                )
                restante = cur.fetchone()
                if not restante:
                    cur.execute('DELETE FROM catalogo_acciones WHERE id = %s', (catalogo['catalogo_id'],))
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}


def _normalizar_fecha_iso(fecha_raw):
    fecha_str = (fecha_raw or '').strip()
    if not fecha_str:
        return None
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def _normalizar_hora_24(hora_raw):
    hora_str = (hora_raw or '').strip()
    if not hora_str:
        return None

    formatos = ('%H:%M', '%H:%M:%S')
    for formato in formatos:
        try:
            return datetime.strptime(hora_str, formato).strftime('%H:%M')
        except ValueError:
            continue
    return None


def _normalizar_dias_semana(dias_semana):
    if not dias_semana:
        return []

    dias_norm = set()
    for dia in dias_semana:
        try:
            valor = int(dia)
        except (TypeError, ValueError):
            continue
        if 0 <= valor <= 6:
            dias_norm.add(valor)
    return sorted(dias_norm)


def _normalizar_fechas_manual(fechas, fecha_inicio_obj=None, fecha_fin_obj=None):
    if not fechas:
        return []

    fechas_norm = set()
    for fecha_raw in fechas:
        fecha_obj = _normalizar_fecha_iso(fecha_raw)
        if not fecha_obj:
            continue
        if fecha_inicio_obj and fecha_obj < fecha_inicio_obj:
            continue
        if fecha_fin_obj and fecha_obj > fecha_fin_obj:
            continue
        fechas_norm.add(fecha_obj)

    return sorted(fechas_norm)


def _normalizar_bloques_horarios(horas):
    bloques = []
    for bloque in horas or []:
        if isinstance(bloque, dict):
            inicio_raw = bloque.get('hora_inicio') or bloque.get('inicio')
            fin_raw = bloque.get('hora_fin') or bloque.get('fin')
        elif isinstance(bloque, (list, tuple)) and len(bloque) >= 2:
            inicio_raw = bloque[0]
            fin_raw = bloque[1]
        else:
            continue

        inicio = _normalizar_hora_24(inicio_raw)
        fin = _normalizar_hora_24(fin_raw)
        if not inicio or not fin or inicio >= fin:
            continue

        bloques.append((inicio, fin))

    return bloques


def _generar_token_asistencia_unico(conn):
    for _ in range(10):
        token = uuid.uuid4().hex[:8]
        with conn.cursor() as cur:
            cur.execute(
                'SELECT 1 FROM sesiones_curso WHERE token_asistencia = %s LIMIT 1',
                (token,),
            )
            token_en_uso = cur.fetchone()
        if not token_en_uso:
            return token

    return uuid.uuid4().hex


def _recalcular_duracion_desde_sesiones(conn, edicion_id):
    _sincronizar_edicion_desde_sesiones(conn, edicion_id)


def _sincronizar_horarios_desde_sesiones(conn, edicion_id):
    _sincronizar_edicion_desde_sesiones(conn, edicion_id)


def listar_sesiones_curso(id_target):
    id_limpio = (id_target or '').strip().upper()
    if not id_limpio:
        return {'ok': False, 'error': 'Identificador inválido'}

    try:
        conn = get_db_connection()
        # Intentar buscar por edicion_id directamente primero
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT s.id_sesion, s.edicion_id, s.fecha, s.hora_inicio, s.hora_fin, s.estado, s.token_asistencia,
                       ef.jornada, ef.docente_responsable, ef.etiqueta_edicion
                FROM sesiones_curso s
                JOIN ediciones_formativas ef ON ef.id = s.edicion_id
                WHERE s.edicion_id = %s
                ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
                ''',
                (id_limpio,),
            )
            sesiones = cur.fetchall()
        
        if not sesiones:
            # Si no hay, intentar buscar todas las sesiones de todas las ediciones de un catalogo_id
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT s.id_sesion, s.edicion_id, s.fecha, s.hora_inicio, s.hora_fin, s.estado, s.token_asistencia,
                           ef.jornada, ef.docente_responsable, ef.etiqueta_edicion
                    FROM sesiones_curso s
                    JOIN ediciones_formativas ef ON ef.id = s.edicion_id
                    WHERE ef.catalogo_id = %s
                    ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
                    ''',
                    (id_limpio,),
                )
                sesiones = cur.fetchall()
            
        conn.close()
        return {'ok': True, 'sesiones': sesiones}
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudieron cargar las sesiones'}


def crear_sesion_manual(edicion_id, fecha, hora_inicio, hora_fin, jornada='UNICA', docente_sesion='', edicion=''):
    edicion_id_limpio = (edicion_id or '').strip().upper()
    fecha_obj = _normalizar_fecha_iso(fecha)
    hora_inicio_norm = _normalizar_hora_24(hora_inicio)
    hora_fin_norm = _normalizar_hora_24(hora_fin)

    if not edicion_id_limpio:
        return {'ok': False, 'error': 'Curso inválido'}
    if not fecha_obj or not hora_inicio_norm or not hora_fin_norm:
        return {'ok': False, 'error': 'Fecha u horas inválidas'}
    if hora_inicio_norm >= hora_fin_norm:
        return {'ok': False, 'error': 'La hora de fin debe ser mayor a la de inicio'}

    jornada_norm = _normalizar_jornada(jornada)

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM ediciones_formativas WHERE id = %s LIMIT 1',
                (edicion_id_limpio,),
            )
            curso = cur.fetchone()
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Curso no encontrado'}

        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT 1
                FROM sesiones_curso
                WHERE edicion_id = %s AND fecha = %s AND hora_inicio = %s AND hora_fin = %s
                LIMIT 1
                ''',
                (edicion_id_limpio, fecha_obj.isoformat(), hora_inicio_norm, hora_fin_norm),
            )
            existe = cur.fetchone()
        if existe:
            conn.close()
            return {'ok': False, 'error': 'La sesión ya existe para ese horario y jornada'}

        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO sesiones_curso (edicion_id, fecha, hora_inicio, hora_fin, estado, token_asistencia)
                VALUES (%s, %s, %s, %s, 0, NULL)
                RETURNING id_sesion
                ''',
                (
                    edicion_id_limpio,
                    fecha_obj.isoformat(),
                    hora_inicio_norm,
                    hora_fin_norm,
                ),
            )
            nueva_sesion = cur.fetchone()
        _sincronizar_edicion_desde_sesiones(conn, edicion_id_limpio, jornada=jornada_norm)
        conn.commit()
        id_sesion = nueva_sesion['id_sesion'] if nueva_sesion else None
        conn.close()
        return {'ok': True, 'id_sesion': id_sesion}
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudo crear la sesión'}


def editar_sesion(id_sesion, fecha, hora_inicio, hora_fin, jornada='UNICA', docente_sesion='', edicion=''):
    fecha_obj = _normalizar_fecha_iso(fecha)
    hora_inicio_norm = _normalizar_hora_24(hora_inicio)
    hora_fin_norm = _normalizar_hora_24(hora_fin)

    try:
        id_sesion_int = int(id_sesion)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Sesión inválida'}

    if not fecha_obj or not hora_inicio_norm or not hora_fin_norm:
        return {'ok': False, 'error': 'Fecha u horas inválidas'}
    if hora_inicio_norm >= hora_fin_norm:
        return {'ok': False, 'error': 'La hora de fin debe ser mayor a la de inicio'}

    jornada_norm = _normalizar_jornada(jornada)

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT edicion_id, estado FROM sesiones_curso WHERE id_sesion = %s LIMIT 1',
                (id_sesion_int,),
            )
            sesion = cur.fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada'}

        if sesion['estado'] != 0:
            conn.close()
            return {'ok': False, 'error': 'Solo se pueden editar sesiones cerradas'}

        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT 1
                FROM sesiones_curso
                WHERE edicion_id = %s AND fecha = %s AND hora_inicio = %s AND hora_fin = %s AND id_sesion <> %s
                LIMIT 1
                ''',
                (
                    sesion['edicion_id'],
                    fecha_obj.isoformat(),
                    hora_inicio_norm,
                    hora_fin_norm,
                    id_sesion_int,
                ),
            )
            existe = cur.fetchone()
        if existe:
            conn.close()
            return {'ok': False, 'error': 'Ya existe otra sesión con el mismo horario y jornada'}

        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE sesiones_curso
                SET fecha = %s, hora_inicio = %s, hora_fin = %s
                WHERE id_sesion = %s
                ''',
                (
                    fecha_obj.isoformat(),
                    hora_inicio_norm,
                    hora_fin_norm,
                    id_sesion_int,
                ),
            )
        _sincronizar_edicion_desde_sesiones(conn, sesion['edicion_id'], jornada=jornada_norm)
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudo editar la sesión'}


def eliminar_sesion(id_sesion):
    try:
        id_sesion_int = int(id_sesion)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Sesión inválida'}

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT edicion_id, estado FROM sesiones_curso WHERE id_sesion = %s LIMIT 1',
                (id_sesion_int,),
            )
            sesion = cur.fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada'}

        with conn.cursor() as cur:
            cur.execute(
                'SELECT COUNT(*) FROM registro_asistencia WHERE id_sesion = %s',
                (id_sesion_int,),
            )
            total_asistencia = cur.fetchone()[0]
        if total_asistencia > 0:
            conn.close()
            return {'ok': False, 'error': 'No se puede eliminar una sesión con asistencia registrada'}

        if sesion['estado'] == 1:
            conn.close()
            return {'ok': False, 'error': 'No se puede eliminar una sesión abierta'}

        with conn.cursor() as cur:
            cur.execute('DELETE FROM sesiones_curso WHERE id_sesion = %s', (id_sesion_int,))
        _sincronizar_edicion_desde_sesiones(conn, sesion['edicion_id'])
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudo eliminar la sesión'}


def generar_calendario_base(edicion_id, fecha_inicio, fecha_fin, dias_semana, horas, jornada='UNICA', docente_sesion='', edicion='', fechas_manual=None):
    edicion_id_limpio = (edicion_id or '').strip().upper()
    fecha_inicio_obj = _normalizar_fecha_iso(fecha_inicio)
    fecha_fin_obj = _normalizar_fecha_iso(fecha_fin)
    dias_norm = _normalizar_dias_semana(dias_semana)
    fechas_manual_norm = _normalizar_fechas_manual(fechas_manual, fecha_inicio_obj, fecha_fin_obj)
    bloques_horarios = _normalizar_bloques_horarios(horas)

    if not edicion_id_limpio:
        return {'ok': False, 'error': 'Curso inválido'}
    if not fecha_inicio_obj or not fecha_fin_obj:
        return {'ok': False, 'error': 'Fechas inválidas'}
    if fecha_inicio_obj > fecha_fin_obj:
        return {'ok': False, 'error': 'La fecha de inicio no puede ser mayor que la fecha de fin'}
    if fechas_manual and not fechas_manual_norm:
        return {'ok': False, 'error': 'Debes seleccionar fechas manuales validas'}
    if not fechas_manual_norm and not dias_norm:
        return {'ok': False, 'error': 'Debes seleccionar al menos un día de la semana'}
    if not bloques_horarios:
        return {'ok': False, 'error': 'Debes enviar al menos un bloque horario válido'}

    jornada_norm = _normalizar_jornada(jornada)

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM ediciones_formativas WHERE id = %s LIMIT 1',
                (edicion_id_limpio,),
            )
            curso = cur.fetchone()
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Curso no encontrado'}

        sesiones_creadas = 0
        fechas_iter = []

        if fechas_manual_norm:
            fechas_iter = fechas_manual_norm
        else:
            fecha_cursor = fecha_inicio_obj
            while fecha_cursor <= fecha_fin_obj:
                if fecha_cursor.weekday() in dias_norm:
                    fechas_iter.append(fecha_cursor)
                fecha_cursor += timedelta(days=1)

        with conn.cursor() as cur:
            for fecha_cursor in fechas_iter:
                fecha_iso = fecha_cursor.isoformat()
                for hora_inicio_norm, hora_fin_norm in bloques_horarios:
                    cur.execute(
                        '''
                        SELECT 1
                        FROM sesiones_curso
                        WHERE edicion_id = %s AND fecha = %s AND hora_inicio = %s AND hora_fin = %s
                        LIMIT 1
                        ''',
                        (edicion_id_limpio, fecha_iso, hora_inicio_norm, hora_fin_norm),
                    )
                    existe = cur.fetchone()
                    if existe:
                        continue

                    cur.execute(
                        '''
                        INSERT INTO sesiones_curso (edicion_id, fecha, hora_inicio, hora_fin, estado, token_asistencia)
                        VALUES (%s, %s, %s, %s, 0, NULL)
                        ''',
                        (
                            edicion_id_limpio,
                            fecha_iso,
                            hora_inicio_norm,
                            hora_fin_norm,
                        ),
                    )
                    sesiones_creadas += 1

        hora_texto = None
        if len(bloques_horarios) == 1:
            hora_texto = f"{bloques_horarios[0][0]}-{bloques_horarios[0][1]}"
        elif len(bloques_horarios) > 1:
            hora_texto = 'Varias'
        _sincronizar_edicion_desde_sesiones(conn, edicion_id_limpio, jornada=jornada_norm, hora_texto=hora_texto)
        conn.commit()
        conn.close()
        return {'ok': True, 'sesiones_creadas': sesiones_creadas}
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudo generar el calendario base'}


def obtener_reporte_asistencia_curso(id_target):
    id_limpio = (id_target or '').strip().upper()
    if not id_limpio:
        return {'ok': False, 'error': 'Identificador inválido'}

    try:
        conn = get_db_connection()
        # Intentar obtener detalle como edicion
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT ef.id, ca.nombre, ef.periodo, ef.fecha_inicio, ca.modalidad, ca.tipo_accion, ef.jornada, ef.hora, ca.id as catalogo_id
                FROM ediciones_formativas ef
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                WHERE ef.id = %s
                LIMIT 1
                ''',
                (id_limpio,),
            )
            curso = cur.fetchone()
        
        es_catalogo = False
        if not curso:
            # Intentar como catalogo
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id as catalogo_id, id, nombre, modalidad, tipo_accion, NULL as periodo, NULL as fecha_inicio, 'UNICA' as jornada, '' as hora
                    FROM catalogo_acciones
                    WHERE id = %s
                    LIMIT 1
                    ''',
                    (id_limpio,),
                )
                curso = cur.fetchone()
            es_catalogo = True
            
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Registro no encontrado'}

        if es_catalogo:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT s.id_sesion, s.hora_inicio, s.hora_fin, s.fecha, s.estado, s.edicion_id
                    FROM sesiones_curso s
                    JOIN ediciones_formativas ef ON ef.id = s.edicion_id
                    WHERE ef.catalogo_id = %s
                    ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
                    ''',
                    (id_limpio,),
                )
                sesiones = cur.fetchall()
        else:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id_sesion, hora_inicio, hora_fin, fecha, estado, edicion_id
                    FROM sesiones_curso
                    WHERE edicion_id = %s
                    ORDER BY fecha ASC, hora_inicio ASC, id_sesion ASC
                    ''',
                    (id_limpio,),
                )
                sesiones = cur.fetchall()

        jornada_edicion = _normalizar_jornada(curso['jornada'])
        sesiones_curso_ordenadas = []
        total_sesiones_curso = 0
        for sesion in sesiones:
            id_sesion = int(sesion['id_sesion']) if sesion['id_sesion'] is not None else None
            
            hora_val = sesion['hora_inicio']
            hora_inicio = hora_val.strftime('%H:%M:%S')[:5] if hasattr(hora_val, 'strftime') else (hora_val or '').strip()[:5]
            
            hora_fin_val = sesion['hora_fin']
            hora_fin = hora_fin_val.strftime('%H:%M:%S')[:5] if hasattr(hora_fin_val, 'strftime') else (hora_fin_val or '').strip()[:5]
            
            fecha_val = sesion['fecha']
            fecha_iso = fecha_val.strftime('%Y-%m-%d') if hasattr(fecha_val, 'strftime') else (fecha_val or '').strip()
            
            estado_sesion = int(sesion['estado'] or 0)

            sesiones_curso_ordenadas.append(
                {
                    'id_sesion': id_sesion,
                    'jornada': jornada_edicion,
                    'fecha': fecha_iso,
                    'hora_inicio': hora_inicio,
                    'hora_fin': hora_fin,
                    'estado': estado_sesion,
                }
            )
            total_sesiones_curso += 1

        if es_catalogo:
            query_matriculas = '''
                WITH asistencia AS (
                    SELECT
                        ra.numero_empleado,
                        COUNT(*) AS total_asistencias,
                        MAX(
                            CASE
                                WHEN ra.fecha_marcado IS NOT NULL AND ra.fecha_marcado <> ''
                                     AND ra.hora_marcado IS NOT NULL AND ra.hora_marcado <> ''
                                THEN ra.fecha_marcado || ' ' || ra.hora_marcado
                            END
                        ) AS ultima_marcacion,
                        ARRAY_AGG(ra.id_sesion) AS sesiones_asistidas
                    FROM registro_asistencia ra
                    JOIN sesiones_curso s ON s.id_sesion = ra.id_sesion
                    JOIN ediciones_formativas ef ON ef.id = s.edicion_id
                    WHERE ef.catalogo_id = %s
                    GROUP BY ra.numero_empleado
                )
                SELECT DISTINCT ON (m.numero_empleado)
                    m.id AS matricula_id,
                    m.numero_empleado,
                    m.aprobado,
                    m.comentario_validacion,
                    d.nombre_completo,
                    COALESCE(a.total_asistencias, 0) AS total_asistencias,
                    a.ultima_marcacion,
                    a.sesiones_asistidas
                FROM matriculas m
                JOIN ediciones_formativas ef ON ef.id = m.edicion_id
                LEFT JOIN docentes d ON d.numero_empleado = m.numero_empleado
                LEFT JOIN asistencia a ON a.numero_empleado = m.numero_empleado
                WHERE ef.catalogo_id = %s
                ORDER BY m.numero_empleado, m.id DESC
            '''
            query_params = (id_limpio, id_limpio)
        else:
            query_matriculas = '''
                WITH asistencia AS (
                    SELECT
                        ra.numero_empleado,
                        COUNT(*) AS total_asistencias,
                        MAX(
                            CASE
                                WHEN ra.fecha_marcado IS NOT NULL AND ra.fecha_marcado <> ''
                                     AND ra.hora_marcado IS NOT NULL AND ra.hora_marcado <> ''
                                THEN ra.fecha_marcado || ' ' || ra.hora_marcado
                            END
                        ) AS ultima_marcacion,
                        ARRAY_AGG(ra.id_sesion) AS sesiones_asistidas
                    FROM registro_asistencia ra
                    JOIN sesiones_curso s ON s.id_sesion = ra.id_sesion
                    WHERE s.edicion_id = %s
                    GROUP BY ra.numero_empleado
                )
                SELECT DISTINCT ON (m.numero_empleado)
                    m.id AS matricula_id,
                    m.numero_empleado,
                    m.aprobado,
                    m.comentario_validacion,
                    d.nombre_completo,
                    COALESCE(a.total_asistencias, 0) AS total_asistencias,
                    a.ultima_marcacion,
                    a.sesiones_asistidas
                FROM matriculas m
                LEFT JOIN docentes d ON d.numero_empleado = m.numero_empleado
                LEFT JOIN asistencia a ON a.numero_empleado = m.numero_empleado
                WHERE m.edicion_id = %s
                ORDER BY m.numero_empleado, m.id DESC
            '''
            query_params = (id_limpio, id_limpio)

        with conn.cursor() as cur:
            cur.execute(query_matriculas, query_params)
            matriculas_raw = cur.fetchall()

        matriculas_por_docente = {}
        for fila in matriculas_raw:
            numero_empleado = (fila['numero_empleado'] or '').strip()
            if not numero_empleado:
                continue

            sesiones_raw = fila.get('sesiones_asistidas') or []
            sesiones_asistidas = set()
            for sesion_id in sesiones_raw:
                try:
                    sesiones_asistidas.add(int(sesion_id))
                except (TypeError, ValueError):
                    continue

            item = dict(fila)
            item['sesiones_asistidas'] = sesiones_asistidas
            matriculas_por_docente[numero_empleado] = item

        def _formatear_fecha_mes(fecha_iso):
            if not fecha_iso:
                return None
            if hasattr(fecha_iso, 'strftime'):
                fecha_obj = fecha_iso
            else:
                fecha_limpia = str(fecha_iso).strip()
                if not fecha_limpia:
                    return None
                try:
                    fecha_obj = datetime.strptime(fecha_limpia, '%Y-%m-%d')
                except ValueError:
                    return None
            try:
                mes_nombre = MESES_ES[fecha_obj.month - 1].capitalize()
                return f"{fecha_obj.day:02d}/{mes_nombre}"
            except (ValueError, IndexError):
                return fecha_limpia

        def _parsear_ultima_marcacion(valor):
            if not valor:
                return None
            if isinstance(valor, datetime):
                return valor
            valor_limpio = str(valor).strip()
            if not valor_limpio:
                return None
            for formato in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    return datetime.strptime(valor_limpio, formato)
                except ValueError:
                    continue
            return None

        def _formatear_ultima_marcacion(marca_dt):
            if not marca_dt:
                return None
            mes_nombre = MESES_ES[marca_dt.month - 1].capitalize()
            return f"{marca_dt.day:02d}/{mes_nombre} - {marca_dt.strftime('%H:%M')}"

        grupos = {
            jornada_edicion: {
                'codigo': jornada_edicion,
                'nombre': _nombre_jornada(jornada_edicion),
                'total_sesiones': total_sesiones_curso,
                'docentes': [],
                'total_inscritos': 0,
                'total_asistencias': 0,
                'porcentaje_cobertura': 0.0,
            }
        }

        hora_etiqueta = _etiqueta_horario_edicion(jornada_edicion, curso['hora'])

        # Pre-compilar set de sesiones asistidas para búsqueda O(1)
        sesiones_asistidas_sets = {}
        for numero_empleado, fila in matriculas_por_docente.items():
            sesiones_raw = fila.get('sesiones_asistidas') or []
            sesiones_set = set()
            for sesion_id in sesiones_raw:
                try:
                    sesiones_set.add(int(sesion_id))
                except (TypeError, ValueError):
                    pass
            sesiones_asistidas_sets[numero_empleado] = sesiones_set

        for numero_empleado, fila in matriculas_por_docente.items():
            total_sesiones_jornada = total_sesiones_curso
            asistencias_docente = int(fila.get('total_asistencias') or 0)
            porcentaje_docente = 0.0
            if total_sesiones_jornada > 0:
                porcentaje_docente = round((asistencias_docente / total_sesiones_jornada) * 100, 1)

            sesiones_docente = sesiones_asistidas_sets.get(numero_empleado, set())
            mapa_asistencia = []
            fechas_ausentes = []
            for sesion in sesiones_curso_ordenadas:
                id_sesion = sesion['id_sesion']
                if id_sesion in sesiones_docente:
                    mapa_asistencia.append({'estado': 'presente'})
                elif int(sesion['estado'] or 0) == 2:
                    mapa_asistencia.append({'estado': 'ausente'})
                    fecha_formateada = _formatear_fecha_mes(sesion['fecha'])
                    if fecha_formateada:
                        fechas_ausentes.append(fecha_formateada)
                else:
                    mapa_asistencia.append({'estado': 'futura'})

            ultima_marcacion = _formatear_ultima_marcacion(
                _parsear_ultima_marcacion(fila.get('ultima_marcacion'))
            )

            aprobado = fila['aprobado']
            estado_texto = (
                'Aprobado' if aprobado == 1 else
                'No aprobado' if aprobado == 0 else
                'Abandono' if aprobado == 2 else
                'Pendiente'
            )

            grupos[jornada_edicion]['docentes'].append(
                {
                    'numero_empleado': numero_empleado,
                    'matricula_id': fila['matricula_id'],
                    'aprobado': fila['aprobado'],
                    'comentario_validacion': fila['comentario_validacion'],
                    'nombre_completo': (fila['nombre_completo'] or '').strip() or 'Docente sin nombre',
                    'horario_elegido': hora_etiqueta or 'Sin horario definido',
                    'asistencias': asistencias_docente,
                    'sesiones_programadas': total_sesiones_jornada,
                    'porcentaje': porcentaje_docente,
                    'estado_matricula': estado_texto,
                    'ultima_marcacion': ultima_marcacion,
                    'fechas_ausentes': fechas_ausentes,
                    'mapa_asistencia': mapa_asistencia,
                }
            )

        jornadas_ordenadas = []
        for codigo in ORDEN_JORNADAS_REPORTE:
            grupo = grupos.get(codigo)
            if not grupo:
                continue

            grupo['docentes'].sort(key=lambda item: (item['nombre_completo'].lower(), item['numero_empleado']))
            grupo['total_inscritos'] = len(grupo['docentes'])
            grupo['total_asistencias'] = sum(item['asistencias'] for item in grupo['docentes'])

            denominador = grupo['total_inscritos'] * grupo['total_sesiones']
            if denominador > 0:
                grupo['porcentaje_cobertura'] = round((grupo['total_asistencias'] / denominador) * 100, 1)
            else:
                grupo['porcentaje_cobertura'] = 0.0

            jornadas_ordenadas.append(grupo)

        total_inscritos = sum(grupo['total_inscritos'] for grupo in jornadas_ordenadas)

        docentes_con_asistencia = []
        docentes_pendientes_asistencia = []
        for grupo in jornadas_ordenadas:
            for docente in grupo['docentes']:
                registro = {
                    **docente,
                    'jornada_codigo': grupo['codigo'],
                    'jornada_nombre': grupo['nombre'],
                }
                if int(docente['asistencias'] or 0) > 0:
                    docentes_con_asistencia.append(registro)
                else:
                    docentes_pendientes_asistencia.append(registro)

        docentes_con_asistencia.sort(key=lambda item: (item['nombre_completo'].lower(), item['numero_empleado']))
        docentes_pendientes_asistencia.sort(key=lambda item: (item['nombre_completo'].lower(), item['numero_empleado']))

        conn.close()
        return {
            'ok': True,
            'curso': {
                'id': curso['id'],
                'nombre': curso['nombre'],
                'periodo': curso['periodo'],
                'fecha_inicio': curso['fecha_inicio'],
                'modalidad': curso['modalidad'],
                'tipo_accion': curso['tipo_accion'],
                'jornada': curso['jornada'],
                'hora': curso['hora'],
            },
            'jornadas': jornadas_ordenadas,
            'total_sesiones': total_sesiones_curso,
            'total_inscritos': total_inscritos,
            'docentes_con_asistencia': docentes_con_asistencia,
            'docentes_pendientes_asistencia': docentes_pendientes_asistencia,
        }
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudo cargar el reporte de asistencias'}


def abrir_asistencia_sesion(id_sesion):
    try:
        id_sesion_int = int(id_sesion)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Sesión inválida'}

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id_sesion, estado
                FROM sesiones_curso
                WHERE id_sesion = %s
                LIMIT 1
                ''',
                (id_sesion_int,),
            )
            sesion = cur.fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada'}

        if sesion['estado'] == 1:
            conn.close()
            return {'ok': False, 'error': 'La asistencia ya está habilitada en esta sesión'}

        token = _generar_token_asistencia_unico(conn)
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE sesiones_curso
                SET estado = 1,
                    token_asistencia = %s
                WHERE id_sesion = %s
                ''',
                (token, id_sesion_int),
            )

        conn.commit()
        conn.close()
        return {'ok': True, 'token_asistencia': token}
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudo abrir la asistencia'}


def cerrar_asistencia_sesion(id_sesion):
    try:
        id_sesion_int = int(id_sesion)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Sesión inválida'}

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id_sesion, estado
                FROM sesiones_curso
                WHERE id_sesion = %s
                LIMIT 1
                ''',
                (id_sesion_int,),
            )
            sesion = cur.fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada'}

        if sesion['estado'] != 1:
            conn.close()
            return {'ok': False, 'error': 'Solo se puede desactivar asistencia en sesiones abiertas'}

        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE sesiones_curso
                SET estado = 2
                WHERE id_sesion = %s
                ''',
                (id_sesion_int,),
            )

        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False, 'error': 'No se pudo desactivar la asistencia'}


def delete_matricula_record(numero_empleado, edicion_id, matricula_id=None):
    try:
        conn = get_db_connection()
        if matricula_id:
            with conn.cursor() as cur:
                cur.execute(
                    'DELETE FROM matriculas WHERE id = %s AND numero_empleado = %s AND edicion_id = %s',
                    (matricula_id, numero_empleado, edicion_id),
                )
        else:
            with conn.cursor() as cur:
                cur.execute(
                    'DELETE FROM matriculas WHERE numero_empleado = %s AND edicion_id = %s AND aprobado IS NULL',
                    (numero_empleado, edicion_id),
                )
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}


def vaciar_matriculas_records():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('DELETE FROM matriculas')
        conn.commit()
        conn.close()
        return {'ok': True}
    except psycopg2.Error:
        return {'ok': False}
