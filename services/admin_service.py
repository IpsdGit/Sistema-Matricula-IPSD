import sqlite3

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
                SELECT d.codigo, d.nombre,
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

        cursor = conn.execute(
            'UPDATE matriculas SET aprobado = ? WHERE id = ? AND numero_empleado = ? AND id_capacitacion = ?',
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
    cupos_maximos,
    enlace_virtual,
    direccion_curso,
    fechas_objetivo,
    franjas_horarias,
):
    try:
        conn = get_db_connection()
        if not direccion_existe(conn, direccion_curso):
            conn.close()
            return {'ok': False, 'invalid_direction': True}

        for fecha_actual in fechas_objetivo:
            anio_actual = str(fecha_actual.year)
            mes_actual = MESES_ES[fecha_actual.month - 1]
            dia_actual = str(fecha_actual.day)
            dia_semana_actual = DIAS_SEMANA[fecha_actual.weekday()]

            id_curso = generar_id_curso(conn, direccion_curso, modalidad)
            conn.execute(
                '''
                INSERT INTO capacitaciones
                (id, nombre, anio, trimestre, mes, dia, modalidad, cupos_maximos, enlace_virtual)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    id_curso,
                    nombre_curso,
                    anio_actual,
                    trimestre,
                    mes_actual,
                    dia_actual,
                    modalidad,
                    cupos_maximos,
                    enlace_virtual,
                ),
            )
            for franja in franjas_horarias:
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
    cupos_maximos,
    enlace_virtual,
    dia_semana,
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

        conn.execute(
            '''
            UPDATE capacitaciones
            SET nombre = ?, anio = ?, trimestre = ?, mes = ?, dia = ?, modalidad = ?, cupos_maximos = ?, enlace_virtual = ?
            WHERE id = ?
            ''',
            (nombre_curso, anio, trimestre, mes, dia, modalidad, cupos_maximos, enlace_virtual, id_curso),
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


def update_direccion_record(codigo_actual, codigo_nuevo, nombre_nuevo):
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

        conn.commit()
        conn.close()
        return {'ok': True}
    except sqlite3.Error:
        return {'ok': False}


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
