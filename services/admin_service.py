import sqlite3
import re
import uuid
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

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


def _normalizar_duracion_tipo(valor):
    duracion = (valor or '').strip().lower()
    if duracion not in {'un_dia', 'varios_dias'}:
        return 'un_dia'
    return duracion


TIPOS_ACCION_FORMATIVA = {'CONFERENCIA', 'SEMINARIO', 'CURSO'}
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
            SELECT m.id as matricula_id, m.numero_empleado, c.id, c.nombre, c.anio, c.trimestre, c.mes, m.horario_elegido, m.fecha_matricula, m.aprobado
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            WHERE 1=1
        '''
        params = []

        if not es_superadmin:
            query_matriculas += ' AND c.id LIKE ?'
            params.append(f'AF-{admin_direccion}-%')

        if anio_filtro:
            query_matriculas += ' AND c.anio = ?'
            params.append(anio_filtro)
        if trimestre_filtro:
            query_matriculas += ' AND c.trimestre = ?'
            params.append(trimestre_filtro)
        if mes_filtro:
            query_matriculas += ' AND c.mes = ?'
            params.append(mes_filtro)
        if resultado_filtro == 'aprobado':
            query_matriculas += ' AND m.aprobado = 1'
        elif resultado_filtro == 'reprobado':
            query_matriculas += ' AND m.aprobado = 0'
        elif resultado_filtro == 'abandono':
            query_matriculas += ' AND m.aprobado = 2'
        elif resultado_filtro == 'pendiente':
            query_matriculas += ' AND m.aprobado IS NULL'

        query_matriculas += ' ORDER BY c.anio DESC, c.mes, c.id, m.numero_empleado'
        registros = conn.execute(query_matriculas, params).fetchall()

        query_cursos = '''
                 SELECT c.id, c.nombre, c.anio, c.trimestre, c.mes, c.dia, c.modalidad, c.cupos_maximos, c.enlace_virtual,
                                     c.duracion_tipo, c.tipo_accion, c.horas_totales, c.semanas_duracion,
                                     c.id_plantilla_certificado,
                   GROUP_CONCAT(h.horario, '<br>') as horarios_html,
                   COUNT(DISTINCT m.numero_empleado) as total_inscritos
            FROM capacitaciones c
            LEFT JOIN horarios_curso h ON c.id = h.id_capacitacion
            LEFT JOIN matriculas m ON c.id = m.id_capacitacion
        '''
        cursos_params = []
        if not es_superadmin:
            query_cursos += ' WHERE c.id LIKE ?'
            cursos_params.append(f'AF-{admin_direccion}-%')

        query_cursos += ' GROUP BY c.id ORDER BY c.anio DESC, c.mes'
        cursos = conn.execute(query_cursos, cursos_params).fetchall()

        query_calendario = '''
            SELECT s.fecha, s.hora_inicio, s.hora_fin, s.estado, c.id AS id_curso, c.nombre AS nombre_curso, c.tipo_accion
            FROM sesiones_curso s
            JOIN capacitaciones c ON c.id = s.id_curso
        '''
        calendario_params = []
        if not es_superadmin:
            query_calendario += ' WHERE c.id LIKE ?'
            calendario_params.append(f'AF-{admin_direccion}-%')

        query_calendario += ' ORDER BY s.fecha ASC, s.hora_inicio ASC, c.id ASC'
        calendario_sesiones = conn.execute(query_calendario, calendario_params).fetchall()

        cursos_con_sesion = set()
        calendario_eventos = []
        for fila in calendario_sesiones:
            fecha_iso = (fila['fecha'] or '').strip()
            if not fecha_iso:
                continue

            id_curso = (fila['id_curso'] or '').strip().upper()
            if id_curso:
                cursos_con_sesion.add(id_curso)

            calendario_eventos.append(
                {
                    'tipo_evento': 'sesion',
                    'fecha_iso': fecha_iso,
                    'fecha_mostrar': _fecha_mostrar_desde_iso(fecha_iso),
                    'hora_inicio': fila['hora_inicio'],
                    'hora_fin': fila['hora_fin'],
                    'id_curso': id_curso,
                    'nombre_curso': fila['nombre_curso'],
                    'estado': fila['estado'],
                    'tipo_accion': _normalizar_tipo_accion(fila['tipo_accion']),
                }
            )

        for curso in cursos:
            id_curso = (curso['id'] or '').strip().upper()
            if not id_curso or id_curso in cursos_con_sesion:
                continue

            fecha_iso = _fecha_iso_desde_partes_curso(curso['anio'], curso['mes'], curso['dia'])
            if not fecha_iso:
                continue

            calendario_eventos.append(
                {
                    'tipo_evento': 'curso',
                    'fecha_iso': fecha_iso,
                    'fecha_mostrar': _fecha_mostrar_desde_iso(fecha_iso),
                    'hora_inicio': None,
                    'hora_fin': None,
                    'id_curso': id_curso,
                    'nombre_curso': curso['nombre'],
                    'estado': None,
                    'tipo_accion': _normalizar_tipo_accion(curso['tipo_accion']),
                }
            )

        calendario_eventos.sort(
            key=lambda evento: (
                evento.get('fecha_iso') or '',
                evento.get('hora_inicio') or '99:99',
                evento.get('id_curso') or '',
            )
        )

        if es_superadmin:
            total_matriculas = conn.execute('SELECT COUNT(*) FROM matriculas').fetchone()[0]
            total_cursos = conn.execute('SELECT COUNT(*) FROM capacitaciones').fetchone()[0]
            total_profesores = conn.execute('SELECT COUNT(DISTINCT numero_empleado) FROM matriculas').fetchone()[0]
        else:
            total_matriculas = conn.execute(
                '''
                SELECT COUNT(*)
                FROM matriculas m
                JOIN capacitaciones c ON c.id = m.id_capacitacion
                WHERE c.id LIKE ?
                ''',
                (f'AF-{admin_direccion}-%',),
            ).fetchone()[0]

            total_cursos = conn.execute(
                'SELECT COUNT(*) FROM capacitaciones WHERE id LIKE ?',
                (f'AF-{admin_direccion}-%',),
            ).fetchone()[0]

            total_profesores = conn.execute(
                '''
                SELECT COUNT(DISTINCT m.numero_empleado)
                FROM matriculas m
                JOIN capacitaciones c ON c.id = m.id_capacitacion
                WHERE c.id LIKE ?
                ''',
                (f'AF-{admin_direccion}-%',),
            ).fetchone()[0]

        stats = {
            'total_matriculas': total_matriculas,
            'total_cursos': total_cursos,
            'total_profesores': total_profesores,
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
                       (SELECT COUNT(*) FROM capacitaciones c WHERE c.id LIKE 'AF-' || d.codigo || '-%') as total_cursos
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
            'calendario_eventos': [],
            'stats': {'total_matriculas': 0, 'total_cursos': 0, 'total_profesores': 0},
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
            where_stats = ' WHERE c.id LIKE ? '
            params.append(f'AF-{admin_direccion}-%')

        datos_cursos = conn.execute(
            f'''
            SELECT c.nombre, COUNT(m.numero_empleado) as total
            FROM capacitaciones c
            LEFT JOIN matriculas m ON c.id = m.id_capacitacion
            {where_stats}
            GROUP BY c.id
            ORDER BY total DESC
            LIMIT 10
            ''',
            params,
        ).fetchall()

        datos_meses = conn.execute(
            f'''
            SELECT c.mes || ' ' || c.anio as periodo, COUNT(m.id) as total
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            {where_stats}
            GROUP BY periodo
            ORDER BY c.anio DESC, c.mes
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
            SELECT m.numero_empleado, c.id, c.nombre, c.anio, c.trimestre, c.mes,
                   m.horario_elegido, m.fecha_matricula, m.aprobado
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            WHERE 1=1
        '''
        params = []
        if admin_rol != 'superadmin':
            query += ' AND c.id LIKE ?'
            params.append(f'AF-{admin_direccion}-%')
        if anio_filtro:
            query += ' AND c.anio = ?'
            params.append(anio_filtro)
        if trimestre_filtro:
            query += ' AND c.trimestre = ?'
            params.append(trimestre_filtro)
        if mes_filtro:
            query += ' AND c.mes = ?'
            params.append(mes_filtro)
        if resultado_filtro == 'aprobado':
            query += ' AND m.aprobado = 1'
        elif resultado_filtro == 'reprobado':
            query += ' AND m.aprobado = 0'
        elif resultado_filtro == 'abandono':
            query += ' AND m.aprobado = 2'
        elif resultado_filtro == 'pendiente':
            query += ' AND m.aprobado IS NULL'

        query += ' ORDER BY c.anio DESC, c.mes, c.id, m.numero_empleado'
        registros = conn.execute(query, params).fetchall()
        conn.close()
        return {'ok': True, 'registros': registros}
    except sqlite3.Error:
        return {'ok': False, 'registros': []}


def update_matricula_resultado(numero_empleado, id_capacitacion, matricula_id, aprobado, estado_codigo, admin_rol, admin_direccion):
    admin_direccion = normalizar_direccion(admin_direccion) or 'IPSD'

    if admin_rol != 'superadmin' and not id_capacitacion.upper().startswith(f'AF-{admin_direccion}-'):
        return {'ok': False, 'error': 'No autorizado para este curso', 'status_code': 403}

    try:
        conn = get_db_connection()
        matricula_actual = conn.execute(
            '''
            SELECT m.id, m.horario_elegido, c.nombre
            FROM matriculas m
            JOIN capacitaciones c ON c.id = m.id_capacitacion
            WHERE m.id = ? AND m.numero_empleado = ? AND m.id_capacitacion = ?
            ''',
            (matricula_id, numero_empleado, id_capacitacion),
        ).fetchone()

        if not matricula_actual:
            conn.close()
            return {'ok': False, 'error': 'Matrícula no encontrada', 'status_code': 404}

        # Actualizar aprobación y fecha de aprobación si corresponde
        if aprobado == 1:
            fecha_aprobacion = datetime.now().strftime('%Y-%m-%d')
            cursor = conn.execute(
                'UPDATE matriculas SET aprobado = ?, fecha_aprobacion = ? WHERE id = ? AND numero_empleado = ? AND id_capacitacion = ?',
                (aprobado, fecha_aprobacion, matricula_id, numero_empleado, id_capacitacion),
            )
        else:
            cursor = conn.execute(
                'UPDATE matriculas SET aprobado = ?, fecha_aprobacion = NULL WHERE id = ? AND numero_empleado = ? AND id_capacitacion = ?',
                (aprobado, matricula_id, numero_empleado, id_capacitacion),
            )

        registrar_evento_matricula(
            conn,
            numero_empleado=numero_empleado,
            id_capacitacion=id_capacitacion,
            nombre_curso=matricula_actual['nombre'],
            horario_elegido=matricula_actual['horario_elegido'],
            estado_codigo=estado_codigo,
            matricula_id=matricula_id,
            detalle='Resultado actualizado desde panel administrativo',
        )

        conn.commit()
        conn.close()

        if cursor.rowcount == 0:
            return {'ok': False, 'error': 'Matrícula no encontrada', 'status_code': 404}

        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo actualizar el resultado', 'status_code': 500}


def create_curso_records(
    nombre_curso,
    trimestre,
    modalidad,
    tipo_accion,
    horas_totales,
    semanas_duracion,
    cupos_maximos,
    enlace_virtual,
    direccion_curso,
    fechas_objetivo,
    franjas_horarias,
    id_plantilla_certificado=None,
):
    try:
        conn = get_db_connection()
        if not direccion_existe(conn, direccion_curso):
            conn.close()
            return {'ok': False, 'invalid_direction': True}

        franjas_norm = [str(franja).strip() for franja in (franjas_horarias or []) if str(franja).strip()]
        if not franjas_norm:
            franjas_norm = ['Por definir']

        tipo_accion_norm = _normalizar_tipo_accion(tipo_accion)
        horas_totales_norm = _normalizar_horas_totales(horas_totales, tipo_accion_norm)
        semanas_duracion_norm = _normalizar_semanas_duracion(semanas_duracion)
        error_regla = _validar_reglas_tipo_accion(tipo_accion_norm, horas_totales_norm, semanas_duracion_norm)
        if error_regla:
            conn.close()
            return {'ok': False, 'validation_error': error_regla}

        duracion_tipo_norm = _duracion_tipo_desde_semanas(semanas_duracion_norm)

        for fecha_actual in fechas_objetivo:
            anio_actual = str(fecha_actual.year)
            mes_actual = MESES_ES[fecha_actual.month - 1]
            dia_actual = str(fecha_actual.day)
            dia_semana_actual = DIAS_SEMANA[fecha_actual.weekday()]

            id_curso = generar_id_curso(conn, direccion_curso, modalidad)
            conn.execute(
                '''
                INSERT INTO capacitaciones
                (id, nombre, anio, trimestre, mes, dia, anio_fin, mes_fin, dia_fin,
                 modalidad, cupos_maximos, enlace_virtual, duracion_tipo,
                 tipo_accion, horas_totales, semanas_duracion, id_plantilla_certificado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    id_curso,
                    nombre_curso,
                    anio_actual,
                    trimestre,
                    mes_actual,
                    dia_actual,
                    anio_actual,
                    mes_actual,
                    dia_actual,
                    modalidad,
                    cupos_maximos,
                    enlace_virtual,
                    duracion_tipo_norm,
                    tipo_accion_norm,
                    horas_totales_norm,
                    semanas_duracion_norm,
                    id_plantilla_certificado,
                ),
            )
            for franja in franjas_norm:
                conn.execute(
                    'INSERT INTO horarios_curso (id_capacitacion, horario) VALUES (?, ?)',
                    (id_curso, f'{dia_semana_actual} {franja}'),
                )

        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.IntegrityError:
        return {'ok': False}
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
            'SELECT id FROM capacitaciones WHERE id = ?',
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

        duracion_tipo_norm = _duracion_tipo_desde_semanas(semanas_duracion_norm)

        conn.execute(
            '''
            UPDATE capacitaciones
            SET nombre = ?, anio = ?, trimestre = ?, mes = ?, dia = ?, modalidad = ?, duracion_tipo = ?,
                tipo_accion = ?, horas_totales = ?, semanas_duracion = ?, cupos_maximos = ?, enlace_virtual = ?,
                id_plantilla_certificado = ?,
                anio_fin = COALESCE(NULLIF(anio_fin, ''), ?),
                mes_fin = COALESCE(NULLIF(mes_fin, ''), ?),
                dia_fin = COALESCE(NULLIF(dia_fin, ''), ?)
            WHERE id = ?
            ''',
            (
                nombre_curso,
                anio,
                trimestre,
                mes,
                dia,
                modalidad,
                duracion_tipo_norm,
                tipo_accion_norm,
                horas_totales_norm,
                semanas_duracion_norm,
                cupos_maximos,
                enlace_virtual,
                id_plantilla_certificado,
                anio,
                mes,
                dia,
                id_curso,
            ),
        )

        horarios = conn.execute(
            'SELECT id, horario FROM horarios_curso WHERE id_capacitacion = ?',
            (id_curso,),
        ).fetchall()
        for h in horarios:
            partes = (h['horario'] or '').split(' ', 1)
            franja = partes[1] if len(partes) == 2 else h['horario']
            nuevo_horario = f'{dia_semana} {franja}'
            conn.execute(
                'UPDATE horarios_curso SET horario = ? WHERE id = ?',
                (nuevo_horario, h['id']),
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

            existe_destino = conn.execute(
                'SELECT 1 FROM capacitaciones WHERE id LIKE ? LIMIT 1',
                (f'AF-{codigo_nuevo}-%',),
            ).fetchone()
            if existe_destino:
                conn.close()
                return {'ok': False, 'duplicate': True}

            cursos_a_renombrar = conn.execute(
                'SELECT id FROM capacitaciones WHERE id LIKE ?',
                (f'AF-{codigo_actual}-%',),
            ).fetchall()

            for fila in cursos_a_renombrar:
                id_anterior = fila['id']
                sufijo = id_anterior[len(f'AF-{codigo_actual}-'):]
                id_nuevo = f'AF-{codigo_nuevo}-{sufijo}'

                conn.execute(
                    'UPDATE horarios_curso SET id_capacitacion = ? WHERE id_capacitacion = ?',
                    (id_nuevo, id_anterior),
                )
                conn.execute(
                    'UPDATE matriculas SET id_capacitacion = ? WHERE id_capacitacion = ?',
                    (id_nuevo, id_anterior),
                )
                conn.execute(
                    'UPDATE capacitaciones SET id = ? WHERE id = ?',
                    (id_nuevo, id_anterior),
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
    import os
    from werkzeug.utils import secure_filename
    
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
            'SELECT COUNT(*) FROM capacitaciones WHERE id LIKE ?',
            (f'AF-{codigo}-%',),
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
        conn.execute('DELETE FROM matriculas WHERE id_capacitacion = ?', (id_curso,))
        conn.execute('DELETE FROM horarios_curso WHERE id_capacitacion = ?', (id_curso,))
        conn.execute('DELETE FROM capacitaciones WHERE id = ?', (id_curso,))
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


def _recalcular_duracion_desde_sesiones(conn, id_curso):
    fila = conn.execute(
        '''
        SELECT MIN(fecha) AS fecha_inicio, MAX(fecha) AS fecha_fin
        FROM sesiones_curso
        WHERE id_curso = ?
        ''',
        (id_curso,),
    ).fetchone()

    semanas = 1
    fecha_inicio = (fila['fecha_inicio'] or '').strip() if fila else ''
    fecha_fin = (fila['fecha_fin'] or '').strip() if fila else ''

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            delta_dias = max(0, (fecha_fin_dt - fecha_inicio_dt).days)
            semanas = (delta_dias // 7) + 1
        except ValueError:
            semanas = 1

    semanas = _normalizar_semanas_duracion(semanas)
    conn.execute(
        '''
        UPDATE capacitaciones
        SET semanas_duracion = ?,
            duracion_tipo = ?
        WHERE id = ?
        ''',
        (semanas, _duracion_tipo_desde_semanas(semanas), id_curso),
    )


def _sincronizar_horarios_desde_sesiones(conn, id_curso):
    franjas = conn.execute(
        '''
        SELECT jornada, hora_inicio, hora_fin, MIN(fecha) AS primera_fecha
        FROM sesiones_curso
        WHERE id_curso = ?
        GROUP BY jornada, hora_inicio, hora_fin
        ORDER BY primera_fecha ASC, hora_inicio ASC, hora_fin ASC
        ''',
        (id_curso,),
    ).fetchall()

    conn.execute('DELETE FROM horarios_curso WHERE id_capacitacion = ?', (id_curso,))

    for fila in franjas:
        jornada = _normalizar_jornada(fila['jornada'])
        hora_inicio = (fila['hora_inicio'] or '').strip()[:5]
        hora_fin = (fila['hora_fin'] or '').strip()[:5]
        if not hora_inicio or not hora_fin:
            continue

        horario_legible = _etiqueta_horario_jornada(jornada, hora_inicio, hora_fin)
        conn.execute(
            'INSERT INTO horarios_curso (id_capacitacion, horario) VALUES (?, ?)',
            (id_curso, horario_legible),
        )


def listar_sesiones_curso(id_curso):
    id_curso_limpio = (id_curso or '').strip().upper()
    if not id_curso_limpio:
        return {'ok': False, 'error': 'Curso inválido'}

    try:
        conn = get_db_connection()
        sesiones = conn.execute(
            '''
            SELECT id_sesion, id_curso, fecha, hora_inicio, hora_fin, jornada, docente_sesion, edicion, estado, token_asistencia
            FROM sesiones_curso
            WHERE id_curso = ?
            ORDER BY fecha ASC, hora_inicio ASC, id_sesion ASC
            ''',
            (id_curso_limpio,),
        ).fetchall()
        conn.close()
        return {'ok': True, 'sesiones': sesiones}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudieron cargar las sesiones'}


def crear_sesion_manual(id_curso, fecha, hora_inicio, hora_fin, jornada='UNICA', docente_sesion='', edicion=''):
    id_curso_limpio = (id_curso or '').strip().upper()
    fecha_obj = _normalizar_fecha_iso(fecha)
    hora_inicio_norm = _normalizar_hora_24(hora_inicio)
    hora_fin_norm = _normalizar_hora_24(hora_fin)

    if not id_curso_limpio:
        return {'ok': False, 'error': 'Curso inválido'}
    if not fecha_obj or not hora_inicio_norm or not hora_fin_norm:
        return {'ok': False, 'error': 'Fecha u horas inválidas'}
    if hora_inicio_norm >= hora_fin_norm:
        return {'ok': False, 'error': 'La hora de fin debe ser mayor a la de inicio'}

    jornada_norm = _normalizar_jornada(jornada)
    docente_sesion_norm = (docente_sesion or '').strip()
    edicion_norm = (edicion or '').strip().upper()

    try:
        conn = get_db_connection()
        curso = conn.execute(
            'SELECT id FROM capacitaciones WHERE id = ? LIMIT 1',
            (id_curso_limpio,),
        ).fetchone()
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Curso no encontrado'}

        existe = conn.execute(
            '''
            SELECT 1
            FROM sesiones_curso
            WHERE id_curso = ? AND fecha = ? AND hora_inicio = ? AND hora_fin = ? AND jornada = ?
            LIMIT 1
            ''',
            (id_curso_limpio, fecha_obj.isoformat(), hora_inicio_norm, hora_fin_norm, jornada_norm),
        ).fetchone()
        if existe:
            conn.close()
            return {'ok': False, 'error': 'La sesión ya existe para ese horario y jornada'}

        cursor = conn.execute(
            '''
            INSERT INTO sesiones_curso (id_curso, fecha, hora_inicio, hora_fin, jornada, docente_sesion, edicion, estado, token_asistencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)
            ''',
            (
                id_curso_limpio,
                fecha_obj.isoformat(),
                hora_inicio_norm,
                hora_fin_norm,
                jornada_norm,
                docente_sesion_norm or None,
                edicion_norm or None,
            ),
        )
        _recalcular_duracion_desde_sesiones(conn, id_curso_limpio)
        _sincronizar_horarios_desde_sesiones(conn, id_curso_limpio)
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
    docente_sesion_norm = (docente_sesion or '').strip()
    edicion_norm = (edicion or '').strip().upper()

    try:
        conn = get_db_connection()
        sesion = conn.execute(
            'SELECT id_curso, estado FROM sesiones_curso WHERE id_sesion = ? LIMIT 1',
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
            WHERE id_curso = ? AND fecha = ? AND hora_inicio = ? AND hora_fin = ? AND jornada = ? AND id_sesion <> ?
            LIMIT 1
            ''',
            (
                sesion['id_curso'],
                fecha_obj.isoformat(),
                hora_inicio_norm,
                hora_fin_norm,
                jornada_norm,
                id_sesion_int,
            ),
        ).fetchone()
        if existe:
            conn.close()
            return {'ok': False, 'error': 'Ya existe otra sesión con el mismo horario y jornada'}

        conn.execute(
            '''
            UPDATE sesiones_curso
            SET fecha = ?, hora_inicio = ?, hora_fin = ?, jornada = ?, docente_sesion = ?, edicion = ?
            WHERE id_sesion = ?
            ''',
            (
                fecha_obj.isoformat(),
                hora_inicio_norm,
                hora_fin_norm,
                jornada_norm,
                docente_sesion_norm or None,
                edicion_norm or None,
                id_sesion_int,
            ),
        )
        _recalcular_duracion_desde_sesiones(conn, sesion['id_curso'])
        _sincronizar_horarios_desde_sesiones(conn, sesion['id_curso'])
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
            'SELECT id_curso, estado FROM sesiones_curso WHERE id_sesion = ? LIMIT 1',
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
        _recalcular_duracion_desde_sesiones(conn, sesion['id_curso'])
        _sincronizar_horarios_desde_sesiones(conn, sesion['id_curso'])
        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo eliminar la sesión'}


def generar_calendario_base(id_curso, fecha_inicio, fecha_fin, dias_semana, horas, jornada='UNICA', docente_sesion='', edicion=''):
    id_curso_limpio = (id_curso or '').strip().upper()
    fecha_inicio_obj = _normalizar_fecha_iso(fecha_inicio)
    fecha_fin_obj = _normalizar_fecha_iso(fecha_fin)
    dias_norm = _normalizar_dias_semana(dias_semana)
    bloques_horarios = _normalizar_bloques_horarios(horas)

    if not id_curso_limpio:
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
    docente_sesion_norm = (docente_sesion or '').strip()
    edicion_norm = (edicion or '').strip().upper()

    try:
        conn = get_db_connection()
        curso = conn.execute(
            'SELECT id FROM capacitaciones WHERE id = ? LIMIT 1',
            (id_curso_limpio,),
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
                        WHERE id_curso = ? AND fecha = ? AND hora_inicio = ? AND hora_fin = ? AND jornada = ?
                        LIMIT 1
                        ''',
                        (id_curso_limpio, fecha_iso, hora_inicio_norm, hora_fin_norm, jornada_norm),
                    ).fetchone()
                    if existe:
                        continue

                    conn.execute(
                        '''
                        INSERT INTO sesiones_curso (id_curso, fecha, hora_inicio, hora_fin, jornada, docente_sesion, edicion, estado, token_asistencia)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)
                        ''',
                        (
                            id_curso_limpio,
                            fecha_iso,
                            hora_inicio_norm,
                            hora_fin_norm,
                            jornada_norm,
                            docente_sesion_norm or None,
                            edicion_norm or None,
                        ),
                    )
                    sesiones_creadas += 1

            fecha_cursor += timedelta(days=1)

        _recalcular_duracion_desde_sesiones(conn, id_curso_limpio)
        _sincronizar_horarios_desde_sesiones(conn, id_curso_limpio)
        conn.commit()
        conn.close()
        return {'ok': True, 'sesiones_creadas': sesiones_creadas}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo generar el calendario base'}


def obtener_reporte_asistencia_curso(id_curso):
    id_curso_limpio = (id_curso or '').strip().upper()
    if not id_curso_limpio:
        return {'ok': False, 'error': 'Curso inválido'}

    try:
        conn = get_db_connection()
        curso = conn.execute(
            '''
            SELECT id, nombre, anio, trimestre, mes, dia, modalidad, tipo_accion
            FROM capacitaciones
            WHERE id = ?
            LIMIT 1
            ''',
            (id_curso_limpio,),
        ).fetchone()
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Curso no encontrado'}

        sesiones = conn.execute(
            '''
            SELECT id_sesion, jornada, hora_inicio, hora_fin, fecha, estado
            FROM sesiones_curso
            WHERE id_curso = ?
            ORDER BY fecha ASC, hora_inicio ASC, id_sesion ASC
            ''',
            (id_curso_limpio,),
        ).fetchall()

        jornadas_sesiones = {}
        sesiones_curso_ordenadas = []
        total_sesiones_curso = 0
        for sesion in sesiones:
            id_sesion = int(sesion['id_sesion']) if sesion['id_sesion'] is not None else None
            jornada = _normalizar_jornada(sesion['jornada'])
            hora_inicio = (sesion['hora_inicio'] or '').strip()[:5]
            hora_fin = (sesion['hora_fin'] or '').strip()[:5]
            fecha_iso = (sesion['fecha'] or '').strip()
            estado_sesion = int(sesion['estado'] or 0)
            if not jornada:
                jornada = 'UNICA'

            if jornada not in jornadas_sesiones:
                jornadas_sesiones[jornada] = {
                    'codigo': jornada,
                    'nombre': _nombre_jornada(jornada),
                    'total_sesiones': 0,
                    'rangos': set(),
                }

            sesiones_curso_ordenadas.append(
                {
                    'id_sesion': id_sesion,
                    'jornada': jornada,
                    'fecha': fecha_iso,
                    'hora_inicio': hora_inicio,
                    'hora_fin': hora_fin,
                    'estado': estado_sesion,
                }
            )

            jornadas_sesiones[jornada]['total_sesiones'] += 1
            if hora_inicio and hora_fin:
                jornadas_sesiones[jornada]['rangos'].add((hora_inicio, hora_fin))
            total_sesiones_curso += 1

        matriculas_raw = conn.execute(
            '''
            SELECT
                m.id,
                m.numero_empleado,
                m.horario_elegido,
                m.aprobado,
                d.nombre_completo
            FROM matriculas m
            LEFT JOIN docentes d ON d.numero_empleado = m.numero_empleado
            WHERE m.id_capacitacion = ?
            ORDER BY m.id DESC
            ''',
            (id_curso_limpio,),
        ).fetchall()

        matriculas_por_docente = {}
        for fila in matriculas_raw:
            numero_empleado = (fila['numero_empleado'] or '').strip()
            if not numero_empleado or numero_empleado in matriculas_por_docente:
                continue
            matriculas_por_docente[numero_empleado] = fila

        asistencia_por_docente_jornada = {}
        asistencia_raw = conn.execute(
            '''
            SELECT ra.numero_empleado, s.jornada, COUNT(*) AS total_asistencias
            FROM registro_asistencia ra
            JOIN sesiones_curso s ON s.id_sesion = ra.id_sesion
            WHERE s.id_curso = ?
            GROUP BY ra.numero_empleado, s.jornada
            ''',
            (id_curso_limpio,),
        ).fetchall()
        for fila in asistencia_raw:
            numero_empleado = (fila['numero_empleado'] or '').strip()
            jornada = _normalizar_jornada(fila['jornada'])
            asistencia_por_docente_jornada[(numero_empleado, jornada)] = int(fila['total_asistencias'] or 0)

        asistencia_detalle_raw = conn.execute(
            '''
            SELECT ra.numero_empleado, ra.id_sesion, ra.fecha_marcado, ra.hora_marcado
            FROM registro_asistencia ra
            JOIN sesiones_curso s ON s.id_sesion = ra.id_sesion
            WHERE s.id_curso = ?
            ''',
            (id_curso_limpio,),
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

        grupos = {}
        for codigo in ORDEN_JORNADAS_REPORTE:
            if codigo == 'POR_CONFIRMAR' or codigo in jornadas_sesiones:
                total_sesiones = jornadas_sesiones[codigo]['total_sesiones'] if codigo in jornadas_sesiones else total_sesiones_curso
                grupos[codigo] = {
                    'codigo': codigo,
                    'nombre': _nombre_jornada(codigo),
                    'total_sesiones': total_sesiones,
                    'docentes': [],
                    'total_inscritos': 0,
                    'total_asistencias': 0,
                    'porcentaje_cobertura': 0.0,
                }

        for numero_empleado, fila in matriculas_por_docente.items():
            horario_elegido = (fila['horario_elegido'] or '').strip()
            jornada_resuelta = _resolver_jornada_desde_horario(horario_elegido, jornadas_sesiones)
            if jornada_resuelta not in grupos:
                grupos[jornada_resuelta] = {
                    'codigo': jornada_resuelta,
                    'nombre': _nombre_jornada(jornada_resuelta),
                    'total_sesiones': total_sesiones_curso,
                    'docentes': [],
                    'total_inscritos': 0,
                    'total_asistencias': 0,
                    'porcentaje_cobertura': 0.0,
                }

            total_sesiones_jornada = grupos[jornada_resuelta]['total_sesiones']
            if jornada_resuelta == 'POR_CONFIRMAR':
                asistencias_docente = sum(
                    asistencia_por_docente_jornada.get((numero_empleado, codigo_jornada), 0)
                    for codigo_jornada in jornadas_sesiones.keys()
                )
            else:
                asistencias_docente = asistencia_por_docente_jornada.get((numero_empleado, jornada_resuelta), 0)

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

            grupos[jornada_resuelta]['docentes'].append(
                {
                    'numero_empleado': numero_empleado,
                    'nombre_completo': (fila['nombre_completo'] or '').strip() or 'Docente sin nombre',
                    'horario_elegido': horario_elegido or 'Sin horario definido',
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

            if grupo['total_inscritos'] > 0 or grupo['total_sesiones'] > 0:
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
                'anio': curso['anio'],
                'trimestre': curso['trimestre'],
                'mes': curso['mes'],
                'dia': curso['dia'],
                'modalidad': curso['modalidad'],
                'tipo_accion': curso['tipo_accion'],
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


def delete_matricula_record(numero_empleado, id_capacitacion, matricula_id=None):
    try:
        conn = get_db_connection()
        if matricula_id:
            conn.execute(
                'DELETE FROM matriculas WHERE id = ? AND numero_empleado = ? AND id_capacitacion = ?',
                (matricula_id, numero_empleado, id_capacitacion),
            )
        else:
            conn.execute(
                'DELETE FROM matriculas WHERE numero_empleado = ? AND id_capacitacion = ? AND aprobado IS NULL',
                (numero_empleado, id_capacitacion),
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
