import sqlite3
import re
import uuid
import os
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash
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
    try:
        return datetime.strptime((fecha_iso or '').strip(), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return fecha_iso or ''


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
    existentes = conn.execute(
        'SELECT id FROM ediciones_formativas WHERE id LIKE ? ORDER BY id ASC',
        (f'{catalogo_id}-E%',),
    ).fetchall()

    ultimo = 0
    patron = re.compile(rf'^{re.escape(catalogo_id)}-E(\d{{3}})$')
    for row in existentes:
        match = patron.match((row['id'] or '').upper())
        if match:
            ultimo = max(ultimo, int(match.group(1)))

    return f'{catalogo_id}-E{ultimo + 1:03d}'


def _sincronizar_edicion_desde_sesiones(conn, edicion_id, jornada=None, hora_texto=None):
    primer = conn.execute(
        '''
        SELECT fecha, hora_inicio, hora_fin
        FROM sesiones_curso
        WHERE edicion_id = ?
        ORDER BY fecha ASC, hora_inicio ASC
        LIMIT 1
        ''',
        (edicion_id,),
    ).fetchone()

    fecha_inicio = (primer['fecha'] or '').strip() if primer else ''
    if not hora_texto and primer:
        hora_inicio = (primer['hora_inicio'] or '').strip()[:5]
        hora_fin = (primer['hora_fin'] or '').strip()[:5]
        if hora_inicio and hora_fin:
            hora_texto = f'{hora_inicio}-{hora_fin}'

    campos = []
    params = []
    if fecha_inicio:
        campos.append('fecha_inicio = ?')
        params.append(fecha_inicio)
    if jornada:
        campos.append('jornada = ?')
        params.append(_normalizar_jornada(jornada))
    if hora_texto is not None:
        campos.append('hora = ?')
        params.append(hora_texto)

    if not campos:
        return

    params.append(edicion_id)
    conn.execute(
        f"UPDATE ediciones_formativas SET {', '.join(campos)} WHERE id = ?",
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
            admin = conn.execute(
                'SELECT password_hash, rol, direccion FROM admin_users WHERE username = ?',
                (username,),
            ).fetchone()
        except sqlite3.OperationalError:
            admin = conn.execute(
                'SELECT password_hash FROM admin_users WHERE username = ?',
                (username,),
            ).fetchone()
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
    except sqlite3.Error:
        return {'ok': False, 'error': 'Error de conexión con la base de datos.'}


def get_admin_dashboard_payload(vista_solicitada, anio_filtro, trimestre_filtro, mes_filtro, resultado_filtro, admin_rol, admin_direccion):
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
                ef.trimestre,
                ef.fecha_inicio,
                ef.jornada,
                ef.hora,
                m.fecha_matricula,
                m.aprobado,
                strftime('%Y', ef.fecha_inicio) AS anio,
                strftime('%m', ef.fecha_inicio) AS mes_num,
                strftime('%d', ef.fecha_inicio) AS dia
            FROM matriculas m
            JOIN ediciones_formativas ef ON m.edicion_id = ef.id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE 1=1
        '''
        params = []

        if not es_superadmin:
            query_matriculas += ' AND ca.direccion_codigo = ?'
            params.append(admin_direccion)

        if anio_filtro:
            query_matriculas += " AND strftime('%Y', ef.fecha_inicio) = ?"
            params.append(anio_filtro)
        if trimestre_filtro:
            query_matriculas += ' AND ef.trimestre = ?'
            params.append(trimestre_filtro)
        if mes_filtro:
            mes_num = _mes_numero_desde_nombre(mes_filtro)
            if mes_num:
                query_matriculas += " AND strftime('%m', ef.fecha_inicio) = ?"
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
        registros_raw = conn.execute(query_matriculas, params).fetchall()
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
                ef.trimestre,
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
                ca.id_plantilla_certificado,
                ca.requisitos AS requisitos_catalogo,
                strftime('%Y', ef.fecha_inicio) AS anio,
                strftime('%m', ef.fecha_inicio) AS mes_num,
                strftime('%d', ef.fecha_inicio) AS dia,
                COUNT(DISTINCT m.numero_empleado) as total_inscritos
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            LEFT JOIN matriculas m ON m.edicion_id = ef.id
        '''
        cursos_params = []
        if not es_superadmin:
            query_cursos += ' WHERE ca.direccion_codigo = ?'
            cursos_params.append(admin_direccion)

        query_cursos += ' GROUP BY ef.id ORDER BY ef.fecha_inicio DESC, ef.id'
        cursos_raw = conn.execute(query_cursos, cursos_params).fetchall()
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
            query_catalogos += ' WHERE ca.direccion_codigo = ?'
            catalogos_params.append(admin_direccion)

        query_catalogos += ' GROUP BY ca.id ORDER BY ca.id'
        catalogos_raw = conn.execute(query_catalogos, catalogos_params).fetchall()
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
            query_calendario += ' WHERE ca.direccion_codigo = ?'
            calendario_params.append(admin_direccion)

        query_calendario += ' ORDER BY s.fecha ASC, s.hora_inicio ASC, ef.id ASC'
        calendario_sesiones = conn.execute(query_calendario, calendario_params).fetchall()

        cursos_con_sesion = set()
        calendario_eventos = []
        for fila in calendario_sesiones:
            fecha_iso = (fila['fecha'] or '').strip()
            if not fecha_iso:
                continue

            edicion_id = (fila['edicion_id'] or '').strip().upper()
            if edicion_id:
                cursos_con_sesion.add(edicion_id)

            calendario_eventos.append(
                {
                    'tipo_evento': 'sesion',
                    'fecha_iso': fecha_iso,
                    'fecha_mostrar': _fecha_mostrar_desde_iso(fecha_iso),
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

            fecha_iso = (curso.get('fecha_inicio') or '').strip()[:10]
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

        trimestre_actual = ['I', 'II', 'III', 'IV'][(datetime.now().month - 1) // 3]
        query_ediciones_trimestre = '''
            SELECT COUNT(*)
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE ef.trimestre = ?
              AND (ef.estado IS NULL OR ef.estado NOT IN ('Finalizada', 'Cancelada'))
        '''
        trimestre_params = [trimestre_actual]
        if not es_superadmin:
            query_ediciones_trimestre += ' AND ca.direccion_codigo = ?'
            trimestre_params.append(admin_direccion)

        ediciones_trimestre_actual = conn.execute(
            query_ediciones_trimestre,
            trimestre_params,
        ).fetchone()[0]

        if es_superadmin:
            total_matriculas = conn.execute('SELECT COUNT(*) FROM matriculas').fetchone()[0]
            total_cursos = conn.execute('SELECT COUNT(*) FROM ediciones_formativas').fetchone()[0]
            total_profesores = conn.execute('SELECT COUNT(DISTINCT numero_empleado) FROM matriculas').fetchone()[0]
        else:
            total_matriculas = conn.execute(
                '''
                SELECT COUNT(*)
                FROM matriculas m
                JOIN ediciones_formativas ef ON ef.id = m.edicion_id
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                WHERE ca.direccion_codigo = ?
                ''',
                (admin_direccion,),
            ).fetchone()[0]

            total_cursos = conn.execute(
                '''
                SELECT COUNT(*)
                FROM ediciones_formativas ef
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                WHERE ca.direccion_codigo = ?
                ''',
                (admin_direccion,),
            ).fetchone()[0]

            total_profesores = conn.execute(
                '''
                SELECT COUNT(DISTINCT m.numero_empleado)
                FROM matriculas m
                JOIN ediciones_formativas ef ON ef.id = m.edicion_id
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                WHERE ca.direccion_codigo = ?
                ''',
                (admin_direccion,),
            ).fetchone()[0]

        stats = {
            'total_matriculas': total_matriculas,
            'total_cursos': total_cursos,
            'total_profesores': total_profesores,
            'ediciones_trimestre_actual': ediciones_trimestre_actual,
            'trimestre_actual': trimestre_actual,
        }

        usuarios_admin = []
        direcciones_gestion = []
        if es_superadmin:
            usuarios_admin = conn.execute(
                '''
                SELECT username, rol, direccion
                FROM admin_users
                ORDER BY CASE WHEN rol = 'superadmin' THEN 0 ELSE 1 END, username
                '''
            ).fetchall()

            direcciones_gestion = conn.execute(
                '''
                SELECT d.codigo, d.nombre, d.ruta_firma_img,
                       (SELECT COUNT(*) FROM admin_users a WHERE a.direccion = d.codigo AND a.rol = 'admin') as total_admins,
                       (SELECT COUNT(*) FROM catalogo_acciones ca WHERE ca.direccion_codigo = d.codigo) as total_cursos
                FROM direcciones d
                ORDER BY d.codigo
                '''
            ).fetchall()

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
                'trimestre': trimestre_filtro,
                'mes': mes_filtro,
                'resultado': resultado_filtro,
            },
        }
    except sqlite3.Error:
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
                'ediciones_trimestre_actual': 0,
                'trimestre_actual': 'I',
            },
            'usuarios_admin': [],
            'direcciones_gestion': [],
            'filtros': {
                'anio': anio_filtro,
                'trimestre': trimestre_filtro,
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
            where_stats = ' WHERE ca.direccion_codigo = ? '
            params.append(admin_direccion)

        datos_cursos = conn.execute(
            f'''
            SELECT ca.nombre, COUNT(m.numero_empleado) as total
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            LEFT JOIN matriculas m ON ef.id = m.edicion_id
            {where_stats}
            GROUP BY ef.id
            ORDER BY total DESC
            LIMIT 10
            ''',
            params,
        ).fetchall()

        datos_meses = conn.execute(
            f'''
            SELECT strftime('%m %Y', m.fecha_matricula) as periodo, COUNT(m.id) as total
            FROM matriculas m
            JOIN ediciones_formativas ef ON m.edicion_id = ef.id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            {where_stats}
            GROUP BY periodo
            ORDER BY MAX(m.fecha_matricula) DESC
            LIMIT 12
            ''',
            params,
        ).fetchall()

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
    except sqlite3.Error:
        return {'ok': False, 'cursos': {'labels': [], 'data': []}, 'meses': {'labels': [], 'data': []}}


def fetch_export_records(anio_filtro, trimestre_filtro, mes_filtro, resultado_filtro, admin_rol, admin_direccion):
    admin_direccion = normalizar_direccion(admin_direccion) or 'IPSD'

    try:
        conn = get_db_connection()

        query = '''
            SELECT m.numero_empleado,
                   ef.id AS edicion_id,
                   ca.nombre,
                   ef.trimestre,
                   ef.fecha_inicio,
                   ef.jornada,
                   ef.hora,
                   m.fecha_matricula,
                   m.aprobado,
                   strftime('%Y', ef.fecha_inicio) AS anio,
                   strftime('%m', ef.fecha_inicio) AS mes_num
            FROM matriculas m
            JOIN ediciones_formativas ef ON m.edicion_id = ef.id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE 1=1
        '''
        params = []
        if admin_rol != 'superadmin':
            query += ' AND ca.direccion_codigo = ?'
            params.append(admin_direccion)
        if anio_filtro:
            query += " AND strftime('%Y', ef.fecha_inicio) = ?"
            params.append(anio_filtro)
        if trimestre_filtro:
            query += ' AND ef.trimestre = ?'
            params.append(trimestre_filtro)
        if mes_filtro:
            mes_num = _mes_numero_desde_nombre(mes_filtro)
            if mes_num:
                query += " AND strftime('%m', ef.fecha_inicio) = ?"
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
        registros_raw = conn.execute(query, params).fetchall()
        registros = []
        for fila in registros_raw:
            item = dict(fila)
            item['mes'] = _mes_nombre_desde_numero(item.get('mes_num'))
            registros.append(item)
        conn.close()
        return {'ok': True, 'registros': registros}
    except sqlite3.Error:
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
        
        matricula_actual = conn.execute(
            '''
            SELECT m.id, ca.nombre, m.edicion_id, ca.direccion_codigo
            FROM matriculas m
            JOIN ediciones_formativas ef ON ef.id = m.edicion_id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE m.id = ? AND m.numero_empleado = ?
            ''',
            (matricula_id, numero_empleado),
        ).fetchone()

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
            cursor = conn.execute(
                'UPDATE matriculas SET aprobado = ?, fecha_aprobacion = ?, comentario_validacion = ? WHERE id = ?',
                (aprobado, fecha_aprobacion, comentario_db, matricula_id),
            )
        else:
            cursor = conn.execute(
                'UPDATE matriculas SET aprobado = ?, fecha_aprobacion = NULL, comentario_validacion = ? WHERE id = ?',
                (aprobado, comentario_db, matricula_id),
            )

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

        if cursor.rowcount == 0:
            return {'ok': False, 'error': 'Matrícula no encontrada', 'status_code': 404}

        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo actualizar el resultado', 'status_code': 500}


def actualizar_catalogo_accion(catalogo_id, nombre, modalidad, tipo_accion, id_plantilla_certificado=None, requisitos=None):
    catalogo_id = (catalogo_id or '').strip().upper()
    if not catalogo_id or not nombre:
        return {'ok': False, 'error': 'ID y nombre son obligatorios.'}
        
    try:
        conn = get_db_connection()
        conn.execute(
            '''
            UPDATE catalogo_acciones
            SET nombre = ?, modalidad = ?, tipo_accion = ?, id_plantilla_certificado = ?, requisitos = ?
            WHERE id = ?
            ''',
            (nombre, modalidad, tipo_accion, id_plantilla_certificado or None, requisitos or '', catalogo_id)
        )
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error as e:
        return {'ok': False, 'error': f'Error al actualizar catálogo: {str(e)}'}

def eliminar_catalogo_accion(catalogo_id):
    catalogo_id = (catalogo_id or '').strip().upper()
    if not catalogo_id:
        return {'ok': False, 'error': 'ID de catálogo inválido.'}
        
    try:
        conn = get_db_connection()
        # El ON DELETE CASCADE se encarga de las ediciones y matrículas
        conn.execute('DELETE FROM catalogo_acciones WHERE id = ?', (catalogo_id,))
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error as e:
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
        conn.execute(
            '''
            INSERT INTO catalogo_acciones
            (id, nombre, modalidad, tipo_accion, id_plantilla_certificado, direccion_codigo)
            VALUES (?, ?, ?, ?, ?, ?)
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
    except sqlite3.IntegrityError as e:
        print(f"Error al crear: {e}")
        return {'ok': False}
    except sqlite3.Error as e:
        print(f"Error al crear: {e}")
        return {'ok': False}
    except Exception as e:
        print(f"Error al crear: {e}")
        return {'ok': False}


def update_edicion_metadata(
    edicion_id,
    trimestre=None,
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
):
    try:
        conn = get_db_connection()

        campos = []
        params = []

        if trimestre:
            campos.append('trimestre = ?')
            params.append(trimestre)

        if fecha_inicio:
            campos.append('fecha_inicio = ?')
            params.append(fecha_inicio)

        if cupos_maximos is not None:
            campos.append('cupos_maximos = ?')
            params.append(cupos_maximos)

        if jornada is not None:
            campos.append('jornada = ?')
            params.append(_normalizar_jornada(jornada))

        if hora is not None:
            campos.append('hora = ?')
            params.append(hora)

        if docente_responsable is not None:
            campos.append('docente_responsable = ?')
            params.append(docente_responsable)

        if persona_apoyo is not None:
            campos.append('persona_apoyo = ?')
            params.append(persona_apoyo)

        if etiqueta_edicion is not None:
            campos.append('etiqueta_edicion = ?')
            params.append(etiqueta_edicion)

        if privacidad is not None:
            campos.append('privacidad = ?')
            params.append(privacidad)

        if fecha_limite_matricula is not None:
            campos.append('fecha_limite_matricula = ?')
            valor_fecha_limite = fecha_limite_matricula or None
            params.append(valor_fecha_limite)

        if enlace_acceso is not None:
            campos.append('enlace_acceso = ?')
            params.append(enlace_acceso)

        if requisitos is not None:
            campos.append('requisitos = ?')
            params.append(requisitos)

        if duracion_horas is not None:
            campos.append('duracion_horas = ?')
            params.append(duracion_horas)

        if estado is not None:
            campos.append('estado = ?')
            params.append(estado)

        if not campos:
            conn.close()
            return {'ok': True}

        params.append(edicion_id)
        cursor = conn.execute(
            f"UPDATE ediciones_formativas SET {', '.join(campos)} WHERE id = ?",
            tuple(params),
        )
        conn.commit()
        conn.close()

        if cursor.rowcount == 0:
            return {'ok': False, 'not_found': True}
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False}


def obtener_catalogo_id_por_edicion(edicion_id):
    edicion_id_limpio = (edicion_id or '').strip().upper()
    if not edicion_id_limpio:
        return None

    try:
        conn = get_db_connection()
        fila = conn.execute(
            'SELECT catalogo_id FROM ediciones_formativas WHERE id = ? LIMIT 1',
            (edicion_id_limpio,),
        ).fetchone()
        conn.close()
        return fila['catalogo_id'] if fila else None
    except sqlite3.Error:
        return None


def listar_ediciones_catalogo(catalogo_id):
    catalogo_id_limpio = (catalogo_id or '').strip().upper()
    if not catalogo_id_limpio:
        return []

    try:
        conn = get_db_connection()
        ediciones = conn.execute(
            '''
            SELECT id, catalogo_id, etiqueta_edicion, trimestre, fecha_inicio, fecha_limite_matricula,
                     jornada, hora, cupos_maximos, enlace_acceso, docente_responsable, persona_apoyo,
                     privacidad, estado, requisitos, duracion_horas
            FROM ediciones_formativas
            WHERE catalogo_id = ?
            ORDER BY id ASC
            ''',
            (catalogo_id_limpio,),
        ).fetchall()
        conn.close()
        return ediciones
    except sqlite3.Error:
        return []


def crear_edicion_formativa(
    catalogo_id,
    trimestre=None,
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
):
    catalogo_id_limpio = (catalogo_id or '').strip().upper()
    if not catalogo_id_limpio:
        return {'ok': False, 'error': 'Catalogo invalido'}

    try:
        conn = get_db_connection()
        edicion_id = _generar_id_edicion(conn, catalogo_id_limpio)
        conn.execute(
            '''
            INSERT INTO ediciones_formativas
            (id, catalogo_id, etiqueta_edicion, trimestre, fecha_inicio, fecha_limite_matricula, jornada,
             hora, cupos_maximos, enlace_acceso, docente_responsable, persona_apoyo, privacidad, estado,
             requisitos, duracion_horas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                edicion_id,
                catalogo_id_limpio,
                etiqueta_edicion,
                trimestre,
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
            ),
        )
        conn.commit()
        conn.close()
        return {'ok': True, 'edicion_id': edicion_id}
    except sqlite3.Error:
        return {'ok': False}


def update_curso_record(
    id_curso,
    nombre_curso,
    anio,
    trimestre,
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
        curso = conn.execute(
            'SELECT catalogo_id FROM ediciones_formativas WHERE id = ?',
            (id_curso,),
        ).fetchone()

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
            conn.execute(
                '''
                UPDATE ediciones_formativas
                SET trimestre = ?,
                    fecha_inicio = ?,
                    fecha_limite_matricula = ?,
                    cupos_maximos = ?,
                    enlace_acceso = ?
                WHERE id = ?
                ''',
                (
                    trimestre,
                    fecha_iso,
                    fecha_iso,
                    cupos_maximos,
                    enlace_virtual,
                    id_curso,
                ),
            )

        conn.execute(
            '''
            UPDATE catalogo_acciones
            SET nombre = ?, modalidad = ?, tipo_accion = ?, id_plantilla_certificado = ?
            WHERE id = ?
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
    except sqlite3.Error:
        return {'ok': False}


def create_admin_user_record(username, password, direccion):
    try:
        conn = get_db_connection()

        if not direccion_existe(conn, direccion):
            conn.close()
            return {'ok': False, 'invalid_direction': True}

        conn.execute(
            'INSERT INTO admin_users (username, password_hash, rol, direccion) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(password), 'admin', direccion),
        )
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.IntegrityError:
        return {'ok': False}
    except sqlite3.Error:
        return {'ok': False}


def update_admin_user_record(username, new_password, direccion):
    try:
        conn = get_db_connection()
        admin_objetivo = conn.execute(
            'SELECT rol FROM admin_users WHERE username = ?',
            (username,),
        ).fetchone()

        if not admin_objetivo or admin_objetivo['rol'] == 'superadmin' or not direccion_existe(conn, direccion):
            conn.close()
            return {'ok': False, 'not_allowed': True}

        if new_password:
            conn.execute(
                'UPDATE admin_users SET direccion = ?, password_hash = ? WHERE username = ?',
                (direccion, generate_password_hash(new_password), username),
            )
        else:
            conn.execute(
                'UPDATE admin_users SET direccion = ? WHERE username = ?',
                (direccion, username),
            )

        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False}


def delete_admin_user_record(username):
    try:
        conn = get_db_connection()
        admin_objetivo = conn.execute(
            'SELECT rol FROM admin_users WHERE username = ?',
            (username,),
        ).fetchone()

        if not admin_objetivo or admin_objetivo['rol'] == 'superadmin':
            conn.close()
            return {'ok': False, 'not_allowed': True}

        conn.execute('DELETE FROM admin_users WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False}


def create_direccion_record(codigo, nombre):
    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO direcciones (codigo, nombre) VALUES (?, ?)',
            (codigo, nombre),
        )
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.IntegrityError:
        return {'ok': False}
    except sqlite3.Error:
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

            conn.execute(
                'UPDATE catalogo_acciones SET direccion_codigo = ? WHERE direccion_codigo = ?',
                (codigo_nuevo, codigo_actual),
            )

            conn.execute(
                'UPDATE admin_users SET direccion = ? WHERE direccion = ? AND rol = ?',
                (codigo_nuevo, codigo_actual, 'admin'),
            )

            conn.execute(
                'UPDATE direcciones SET codigo = ?, nombre = ? WHERE codigo = ?',
                (codigo_nuevo, nombre_nuevo, codigo_actual),
            )
        else:
            conn.execute(
                'UPDATE direcciones SET nombre = ? WHERE codigo = ?',
                (nombre_nuevo, codigo_actual),
            )

        if ruta_firma_img is not None:
            codigo_destino = codigo_nuevo if codigo_actual != codigo_nuevo else codigo_actual
            conn.execute(
                'UPDATE direcciones SET ruta_firma_img = ? WHERE codigo = ?',
                (ruta_firma_img, codigo_destino),
            )

        if ruta_logo_img is not None:
            codigo_destino = codigo_nuevo if codigo_actual != codigo_nuevo else codigo_actual
            conn.execute(
                'UPDATE direcciones SET ruta_logo_img = ? WHERE codigo = ?',
                (ruta_logo_img, codigo_destino),
            )

        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
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
            conn.execute(
                'UPDATE direcciones SET ruta_firma_img = ? WHERE codigo = ?',
                (ruta_firma_web, direccion_codigo),
            )
            
        if file_logo and file_logo.filename:
            filename_orig = secure_filename(file_logo.filename)
            ext = os.path.splitext(filename_orig)[1].lower()
            filename_logo = f'logo{ext}'
            ruta_guardado_logo = os.path.join(dir_path, filename_logo)
            file_logo.save(ruta_guardado_logo)
            ruta_logo_web = f'/uploads/direcciones/{direccion_codigo}/{filename_logo}'
            conn.execute(
                'UPDATE direcciones SET ruta_logo_img = ? WHERE codigo = ?',
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

        total_direcciones = conn.execute('SELECT COUNT(*) FROM direcciones').fetchone()[0]
        total_admins = conn.execute(
            'SELECT COUNT(*) FROM admin_users WHERE direccion = ? AND rol = ?',
            (codigo, 'admin'),
        ).fetchone()[0]
        total_cursos = conn.execute(
            'SELECT COUNT(*) FROM catalogo_acciones WHERE direccion_codigo = ?',
            (codigo,),
        ).fetchone()[0]

        if total_direcciones <= 1 or total_admins > 0 or total_cursos > 0:
            conn.close()
            return {'ok': False, 'blocked': True}

        conn.execute('DELETE FROM direcciones WHERE codigo = ?', (codigo,))
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False}


def delete_curso_record(id_curso):
    try:
        conn = get_db_connection()
        catalogo = conn.execute(
            'SELECT catalogo_id FROM ediciones_formativas WHERE id = ?',
            (id_curso,),
        ).fetchone()

        conn.execute('DELETE FROM certificados_emitidos WHERE edicion_id = ?', (id_curso,))
        conn.execute('DELETE FROM matricula_historial WHERE edicion_id = ?', (id_curso,))
        conn.execute('DELETE FROM matriculas WHERE edicion_id = ?', (id_curso,))
        conn.execute('DELETE FROM sesiones_curso WHERE edicion_id = ?', (id_curso,))
        conn.execute('DELETE FROM ediciones_formativas WHERE id = ?', (id_curso,))

        if catalogo:
            restante = conn.execute(
                'SELECT 1 FROM ediciones_formativas WHERE catalogo_id = ? LIMIT 1',
                (catalogo['catalogo_id'],),
            ).fetchone()
            if not restante:
                conn.execute('DELETE FROM catalogo_acciones WHERE id = ?', (catalogo['catalogo_id'],))
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
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
        token_en_uso = conn.execute(
            'SELECT 1 FROM sesiones_curso WHERE token_asistencia = ? LIMIT 1',
            (token,),
        ).fetchone()
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
        sesiones = conn.execute(
            '''
            SELECT s.id_sesion, s.edicion_id, s.fecha, s.hora_inicio, s.hora_fin, s.estado, s.token_asistencia,
                   ef.jornada, ef.docente_responsable, ef.etiqueta_edicion
            FROM sesiones_curso s
            JOIN ediciones_formativas ef ON ef.id = s.edicion_id
            WHERE s.edicion_id = ?
            ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
            ''',
            (id_limpio,),
        ).fetchall()
        
        if not sesiones:
            # Si no hay, intentar buscar todas las sesiones de todas las ediciones de un catalogo_id
            sesiones = conn.execute(
                '''
                SELECT s.id_sesion, s.edicion_id, s.fecha, s.hora_inicio, s.hora_fin, s.estado, s.token_asistencia,
                       ef.jornada, ef.docente_responsable, ef.etiqueta_edicion
                FROM sesiones_curso s
                JOIN ediciones_formativas ef ON ef.id = s.edicion_id
                WHERE ef.catalogo_id = ?
                ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
                ''',
                (id_limpio,),
            ).fetchall()
            
        conn.close()
        return {'ok': True, 'sesiones': sesiones}
    except sqlite3.Error:
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
        curso = conn.execute(
            'SELECT id FROM ediciones_formativas WHERE id = ? LIMIT 1',
            (edicion_id_limpio,),
        ).fetchone()
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Curso no encontrado'}

        existe = conn.execute(
            '''
            SELECT 1
            FROM sesiones_curso
            WHERE edicion_id = ? AND fecha = ? AND hora_inicio = ? AND hora_fin = ?
            LIMIT 1
            ''',
            (edicion_id_limpio, fecha_obj.isoformat(), hora_inicio_norm, hora_fin_norm),
        ).fetchone()
        if existe:
            conn.close()
            return {'ok': False, 'error': 'La sesión ya existe para ese horario y jornada'}

        cursor = conn.execute(
            '''
            INSERT INTO sesiones_curso (edicion_id, fecha, hora_inicio, hora_fin, estado, token_asistencia)
            VALUES (?, ?, ?, ?, 0, NULL)
            ''',
            (
                edicion_id_limpio,
                fecha_obj.isoformat(),
                hora_inicio_norm,
                hora_fin_norm,
            ),
        )
        _sincronizar_edicion_desde_sesiones(conn, edicion_id_limpio, jornada=jornada_norm)
        conn.commit()
        id_sesion = cursor.lastrowid
        conn.close()
        return {'ok': True, 'id_sesion': id_sesion}
    except sqlite3.Error:
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
        sesion = conn.execute(
            'SELECT edicion_id, estado FROM sesiones_curso WHERE id_sesion = ? LIMIT 1',
            (id_sesion_int,),
        ).fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada'}

        if sesion['estado'] != 0:
            conn.close()
            return {'ok': False, 'error': 'Solo se pueden editar sesiones cerradas'}

        existe = conn.execute(
            '''
            SELECT 1
            FROM sesiones_curso
            WHERE edicion_id = ? AND fecha = ? AND hora_inicio = ? AND hora_fin = ? AND id_sesion <> ?
            LIMIT 1
            ''',
            (
                sesion['edicion_id'],
                fecha_obj.isoformat(),
                hora_inicio_norm,
                hora_fin_norm,
                id_sesion_int,
            ),
        ).fetchone()
        if existe:
            conn.close()
            return {'ok': False, 'error': 'Ya existe otra sesión con el mismo horario y jornada'}

        conn.execute(
            '''
            UPDATE sesiones_curso
            SET fecha = ?, hora_inicio = ?, hora_fin = ?
            WHERE id_sesion = ?
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
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo editar la sesión'}


def eliminar_sesion(id_sesion):
    try:
        id_sesion_int = int(id_sesion)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Sesión inválida'}

    try:
        conn = get_db_connection()
        sesion = conn.execute(
            'SELECT edicion_id, estado FROM sesiones_curso WHERE id_sesion = ? LIMIT 1',
            (id_sesion_int,),
        ).fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada'}

        total_asistencia = conn.execute(
            'SELECT COUNT(*) FROM registro_asistencia WHERE id_sesion = ?',
            (id_sesion_int,),
        ).fetchone()[0]
        if total_asistencia > 0:
            conn.close()
            return {'ok': False, 'error': 'No se puede eliminar una sesión con asistencia registrada'}

        if sesion['estado'] == 1:
            conn.close()
            return {'ok': False, 'error': 'No se puede eliminar una sesión abierta'}

        conn.execute('DELETE FROM sesiones_curso WHERE id_sesion = ?', (id_sesion_int,))
        _sincronizar_edicion_desde_sesiones(conn, sesion['edicion_id'])
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo eliminar la sesión'}


def generar_calendario_base(edicion_id, fecha_inicio, fecha_fin, dias_semana, horas, jornada='UNICA', docente_sesion='', edicion=''):
    edicion_id_limpio = (edicion_id or '').strip().upper()
    fecha_inicio_obj = _normalizar_fecha_iso(fecha_inicio)
    fecha_fin_obj = _normalizar_fecha_iso(fecha_fin)
    dias_norm = _normalizar_dias_semana(dias_semana)
    bloques_horarios = _normalizar_bloques_horarios(horas)

    if not edicion_id_limpio:
        return {'ok': False, 'error': 'Curso inválido'}
    if not fecha_inicio_obj or not fecha_fin_obj:
        return {'ok': False, 'error': 'Fechas inválidas'}
    if fecha_inicio_obj > fecha_fin_obj:
        return {'ok': False, 'error': 'La fecha de inicio no puede ser mayor que la fecha de fin'}
    if not dias_norm:
        return {'ok': False, 'error': 'Debes seleccionar al menos un día de la semana'}
    if not bloques_horarios:
        return {'ok': False, 'error': 'Debes enviar al menos un bloque horario válido'}

    jornada_norm = _normalizar_jornada(jornada)

    try:
        conn = get_db_connection()
        curso = conn.execute(
            'SELECT id FROM ediciones_formativas WHERE id = ? LIMIT 1',
            (edicion_id_limpio,),
        ).fetchone()
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Curso no encontrado'}

        sesiones_creadas = 0
        fecha_cursor = fecha_inicio_obj

        while fecha_cursor <= fecha_fin_obj:
            if fecha_cursor.weekday() in dias_norm:
                fecha_iso = fecha_cursor.isoformat()
                for hora_inicio_norm, hora_fin_norm in bloques_horarios:
                    existe = conn.execute(
                        '''
                        SELECT 1
                        FROM sesiones_curso
                        WHERE edicion_id = ? AND fecha = ? AND hora_inicio = ? AND hora_fin = ?
                        LIMIT 1
                        ''',
                        (edicion_id_limpio, fecha_iso, hora_inicio_norm, hora_fin_norm),
                    ).fetchone()
                    if existe:
                        continue

                    conn.execute(
                        '''
                        INSERT INTO sesiones_curso (edicion_id, fecha, hora_inicio, hora_fin, estado, token_asistencia)
                        VALUES (?, ?, ?, ?, 0, NULL)
                        ''',
                        (
                            edicion_id_limpio,
                            fecha_iso,
                            hora_inicio_norm,
                            hora_fin_norm,
                        ),
                    )
                    sesiones_creadas += 1

            fecha_cursor += timedelta(days=1)

        hora_texto = None
        if len(bloques_horarios) == 1:
            hora_texto = f"{bloques_horarios[0][0]}-{bloques_horarios[0][1]}"
        elif len(bloques_horarios) > 1:
            hora_texto = 'Varias'
        _sincronizar_edicion_desde_sesiones(conn, edicion_id_limpio, jornada=jornada_norm, hora_texto=hora_texto)
        conn.commit()
        conn.close()
        return {'ok': True, 'sesiones_creadas': sesiones_creadas}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo generar el calendario base'}


def obtener_reporte_asistencia_curso(id_target):
    id_limpio = (id_target or '').strip().upper()
    if not id_limpio:
        return {'ok': False, 'error': 'Identificador inválido'}

    try:
        conn = get_db_connection()
        # Intentar obtener detalle como edicion
        curso = conn.execute(
            '''
            SELECT ef.id, ca.nombre, ef.trimestre, ef.fecha_inicio, ca.modalidad, ca.tipo_accion, ef.jornada, ef.hora, ca.id as catalogo_id
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE ef.id = ?
            LIMIT 1
            ''',
            (id_limpio,),
        ).fetchone()
        
        es_catalogo = False
        if not curso:
            # Intentar como catalogo
            curso = conn.execute(
                '''
                SELECT id as catalogo_id, id, nombre, modalidad, tipo_accion, NULL as trimestre, NULL as fecha_inicio, 'UNICA' as jornada, '' as hora
                FROM catalogo_acciones
                WHERE id = ?
                LIMIT 1
                ''',
                (id_limpio,),
            ).fetchone()
            es_catalogo = True
            
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Registro no encontrado'}

        if es_catalogo:
            sesiones = conn.execute(
                '''
                SELECT s.id_sesion, s.hora_inicio, s.hora_fin, s.fecha, s.estado, s.edicion_id
                FROM sesiones_curso s
                JOIN ediciones_formativas ef ON ef.id = s.edicion_id
                WHERE ef.catalogo_id = ?
                ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
                ''',
                (id_limpio,),
            ).fetchall()
        else:
            sesiones = conn.execute(
                '''
                SELECT id_sesion, hora_inicio, hora_fin, fecha, estado, edicion_id
                FROM sesiones_curso
                WHERE edicion_id = ?
                ORDER BY fecha ASC, hora_inicio ASC, id_sesion ASC
                ''',
                (id_limpio,),
            ).fetchall()

        jornada_edicion = _normalizar_jornada(curso['jornada'])
        sesiones_curso_ordenadas = []
        total_sesiones_curso = 0
        for sesion in sesiones:
            id_sesion = int(sesion['id_sesion']) if sesion['id_sesion'] is not None else None
            hora_inicio = (sesion['hora_inicio'] or '').strip()[:5]
            hora_fin = (sesion['hora_fin'] or '').strip()[:5]
            fecha_iso = (sesion['fecha'] or '').strip()
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
            matriculas_raw = conn.execute(
                '''
                SELECT
                    m.id AS matricula_id,
                    m.numero_empleado,
                    m.aprobado,
                    m.comentario_validacion,
                    d.nombre_completo
                FROM matriculas m
                JOIN ediciones_formativas ef ON ef.id = m.edicion_id
                LEFT JOIN docentes d ON d.numero_empleado = m.numero_empleado
                WHERE ef.catalogo_id = ?
                ORDER BY m.id DESC
                ''',
                (id_limpio,),
            ).fetchall()
        else:
            matriculas_raw = conn.execute(
                '''
                SELECT
                    m.id AS matricula_id,
                    m.numero_empleado,
                    m.aprobado,
                    m.comentario_validacion,
                    d.nombre_completo
                FROM matriculas m
                LEFT JOIN docentes d ON d.numero_empleado = m.numero_empleado
                WHERE m.edicion_id = ?
                ORDER BY m.id DESC
                ''',
                (id_limpio,),
            ).fetchall()

        matriculas_por_docente = {}
        for fila in matriculas_raw:
            numero_empleado = (fila['numero_empleado'] or '').strip()
            if not numero_empleado or numero_empleado in matriculas_por_docente:
                continue
            matriculas_por_docente[numero_empleado] = fila

        asistencia_por_docente = {}
        if es_catalogo:
            asistencia_raw = conn.execute(
                '''
                SELECT ra.numero_empleado, COUNT(*) AS total_asistencias
                FROM registro_asistencia ra
                JOIN sesiones_curso s ON s.id_sesion = ra.id_sesion
                JOIN ediciones_formativas ef ON ef.id = s.edicion_id
                WHERE ef.catalogo_id = ?
                GROUP BY ra.numero_empleado
                ''',
                (id_limpio,),
            ).fetchall()
        else:
            asistencia_raw = conn.execute(
                '''
                SELECT ra.numero_empleado, COUNT(*) AS total_asistencias
                FROM registro_asistencia ra
                JOIN sesiones_curso s ON s.id_sesion = ra.id_sesion
                WHERE s.edicion_id = ?
                GROUP BY ra.numero_empleado
                ''',
                (id_limpio,),
            ).fetchall()
        for fila in asistencia_raw:
            numero_empleado = (fila['numero_empleado'] or '').strip()
            asistencia_por_docente[numero_empleado] = int(fila['total_asistencias'] or 0)

        if es_catalogo:
            asistencia_detalle_raw = conn.execute(
                '''
                SELECT ra.numero_empleado, ra.id_sesion, ra.fecha_marcado, ra.hora_marcado
                FROM registro_asistencia ra
                JOIN sesiones_curso s ON s.id_sesion = ra.id_sesion
                JOIN ediciones_formativas ef ON ef.id = s.edicion_id
                WHERE ef.catalogo_id = ?
                ''',
                (id_limpio,),
            ).fetchall()
        else:
            asistencia_detalle_raw = conn.execute(
                '''
                SELECT ra.numero_empleado, ra.id_sesion, ra.fecha_marcado, ra.hora_marcado
                FROM registro_asistencia ra
                JOIN sesiones_curso s ON s.id_sesion = ra.id_sesion
                WHERE s.edicion_id = ?
                ''',
                (id_limpio,),
            ).fetchall()

        asistencias_por_docente_sesion = {}
        ultima_marcacion_por_docente = {}
        for fila in asistencia_detalle_raw:
            numero_empleado = (fila['numero_empleado'] or '').strip()
            if not numero_empleado:
                continue

            try:
                id_sesion_asistencia = int(fila['id_sesion'])
            except (TypeError, ValueError):
                continue

            if numero_empleado not in asistencias_por_docente_sesion:
                asistencias_por_docente_sesion[numero_empleado] = set()
            asistencias_por_docente_sesion[numero_empleado].add(id_sesion_asistencia)

            fecha_marcado = (fila['fecha_marcado'] or '').strip()
            hora_marcado = (fila['hora_marcado'] or '').strip()[:5]
            marca_dt = None
            if fecha_marcado and hora_marcado:
                try:
                    marca_dt = datetime.strptime(f"{fecha_marcado} {hora_marcado}", '%Y-%m-%d %H:%M')
                except ValueError:
                    marca_dt = None

            if marca_dt:
                actual = ultima_marcacion_por_docente.get(numero_empleado)
                if not actual or marca_dt > actual:
                    ultima_marcacion_por_docente[numero_empleado] = marca_dt

        def _formatear_fecha_mes(fecha_iso):
            fecha_limpia = (fecha_iso or '').strip()
            if not fecha_limpia:
                return None
            try:
                fecha_obj = datetime.strptime(fecha_limpia, '%Y-%m-%d')
                mes_nombre = MESES_ES[fecha_obj.month - 1].capitalize()
                return f"{fecha_obj.day:02d}/{mes_nombre}"
            except (ValueError, IndexError):
                return fecha_limpia

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

        for numero_empleado, fila in matriculas_por_docente.items():
            total_sesiones_jornada = total_sesiones_curso
            asistencias_docente = asistencia_por_docente.get(numero_empleado, 0)
            porcentaje_docente = 0.0
            if total_sesiones_jornada > 0:
                porcentaje_docente = round((asistencias_docente / total_sesiones_jornada) * 100, 1)

            sesiones_docente = asistencias_por_docente_sesion.get(numero_empleado, set())
            mapa_asistencia = []
            fechas_ausentes = []
            for sesion in sesiones_curso_ordenadas:
                id_sesion = sesion['id_sesion']
                estado_sesion = int(sesion['estado'] or 0)
                if id_sesion and id_sesion in sesiones_docente:
                    mapa_asistencia.append({'estado': 'presente'})
                    continue

                if estado_sesion == 2:
                    mapa_asistencia.append({'estado': 'ausente'})
                    fecha_formateada = _formatear_fecha_mes(sesion['fecha'])
                    if fecha_formateada:
                        fechas_ausentes.append(fecha_formateada)
                else:
                    mapa_asistencia.append({'estado': 'futura'})

            ultima_marcacion = _formatear_ultima_marcacion(ultima_marcacion_por_docente.get(numero_empleado))

            estado_matricula = fila['aprobado']
            if estado_matricula == 1:
                estado_texto = 'Aprobado'
            elif estado_matricula == 0:
                estado_texto = 'No aprobado'
            elif estado_matricula == 2:
                estado_texto = 'Abandono'
            else:
                estado_texto = 'Pendiente'

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
                'trimestre': curso['trimestre'],
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
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo cargar el reporte de asistencias'}


def abrir_asistencia_sesion(id_sesion):
    try:
        id_sesion_int = int(id_sesion)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Sesión inválida'}

    try:
        conn = get_db_connection()
        sesion = conn.execute(
            '''
            SELECT id_sesion, estado
            FROM sesiones_curso
            WHERE id_sesion = ?
            LIMIT 1
            ''',
            (id_sesion_int,),
        ).fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada'}

        if sesion['estado'] == 1:
            conn.close()
            return {'ok': False, 'error': 'La asistencia ya está habilitada en esta sesión'}

        token = _generar_token_asistencia_unico(conn)
        conn.execute(
            '''
            UPDATE sesiones_curso
            SET estado = 1,
                token_asistencia = ?
            WHERE id_sesion = ?
            ''',
            (token, id_sesion_int),
        )

        conn.commit()
        conn.close()
        return {'ok': True, 'token_asistencia': token}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo abrir la asistencia'}


def cerrar_asistencia_sesion(id_sesion):
    try:
        id_sesion_int = int(id_sesion)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Sesión inválida'}

    try:
        conn = get_db_connection()
        sesion = conn.execute(
            '''
            SELECT id_sesion, estado
            FROM sesiones_curso
            WHERE id_sesion = ?
            LIMIT 1
            ''',
            (id_sesion_int,),
        ).fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada'}

        if sesion['estado'] != 1:
            conn.close()
            return {'ok': False, 'error': 'Solo se puede desactivar asistencia en sesiones abiertas'}

        conn.execute(
            '''
            UPDATE sesiones_curso
            SET estado = 2
            WHERE id_sesion = ?
            ''',
            (id_sesion_int,),
        )

        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo desactivar la asistencia'}


def delete_matricula_record(numero_empleado, edicion_id, matricula_id=None):
    try:
        conn = get_db_connection()
        if matricula_id:
            conn.execute(
                'DELETE FROM matriculas WHERE id = ? AND numero_empleado = ? AND edicion_id = ?',
                (matricula_id, numero_empleado, edicion_id),
            )
        else:
            conn.execute(
                'DELETE FROM matriculas WHERE numero_empleado = ? AND edicion_id = ? AND aprobado IS NULL',
                (numero_empleado, edicion_id),
            )
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False}


def vaciar_matriculas_records():
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM matriculas')
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False}
