import sqlite3

from config import LIMITE_ABANDONO, LIMITE_REPROBADO
from database import get_db_connection
from utils import (
    construir_contexto_dashboard,
    normalizar_nombre_curso,
    obtener_resumen_intentos_por_curso,
    registrar_evento_matricula,
)


def load_dashboard_context(
    numero_empleado,
    seccion_activa,
    filtro_historial,
    filtro_notificacion='todas',
    ids_notificaciones_leidas=None,
):
    try:
        conn = get_db_connection()
        contexto = construir_contexto_dashboard(
            conn,
            numero_empleado,
            seccion_activa=seccion_activa,
            filtro_historial=filtro_historial,
            filtro_notificacion=filtro_notificacion,
            ids_notificaciones_leidas=ids_notificaciones_leidas,
        )
        conn.close()
        return {'ok': True, 'contexto': contexto}
    except sqlite3.Error:
        return {'ok': False, 'error': 'Error de conexión. Intente nuevamente.'}


def process_matricula(numero_empleado, id_capacitacion, horario_elegido):
    try:
        conn = get_db_connection()

        curso = conn.execute(
            'SELECT id, nombre FROM capacitaciones WHERE id = ?',
            (id_capacitacion,),
        ).fetchone()
        horario_valido = conn.execute(
            'SELECT 1 FROM horarios_curso WHERE id_capacitacion = ? AND horario = ?',
            (id_capacitacion, horario_elegido),
        ).fetchone()

        if not curso or not horario_valido:
            conn.close()
            return {'ok': False, 'error': 'Curso o horario inválido.', 'error_view': 'index'}

        resumen_intentos = obtener_resumen_intentos_por_curso(conn, numero_empleado)
        clave_curso = normalizar_nombre_curso(curso['nombre'])
        resumen_curso = resumen_intentos.get(
            clave_curso,
            {
                'nombre': curso['nombre'],
                'aprobados': 0,
                'reprobados': 0,
                'abandonos': 0,
                'pendientes': 0,
            },
        )

        if resumen_curso['aprobados'] > 0:
            contexto = construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles')
            conn.close()
            return {
                'ok': False,
                'error': 'Este curso ya fue aprobado y no está habilitado para una nueva matrícula.',
                'error_view': 'dashboard',
                'contexto': contexto,
            }

        if resumen_curso['abandonos'] >= LIMITE_ABANDONO:
            contexto = construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles')
            conn.close()
            return {
                'ok': False,
                'error': f'Ya alcanzaste el límite de abandonos ({LIMITE_ABANDONO}) para este curso.',
                'error_view': 'dashboard',
                'contexto': contexto,
            }

        if resumen_curso['reprobados'] >= LIMITE_REPROBADO:
            contexto = construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles')
            conn.close()
            return {
                'ok': False,
                'error': f'Ya alcanzaste el límite de no aprobación ({LIMITE_REPROBADO}) para este curso.',
                'error_view': 'dashboard',
                'contexto': contexto,
            }

        if resumen_curso['pendientes'] > 0:
            contexto = construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles')
            conn.close()
            return {
                'ok': False,
                'error': 'Ya tienes una matrícula pendiente para este curso.',
                'error_view': 'dashboard',
                'contexto': contexto,
            }

        nueva_matricula = conn.execute(
            'INSERT INTO matriculas (numero_empleado, id_capacitacion, horario_elegido) VALUES (?, ?, ?)',
            (numero_empleado, id_capacitacion, horario_elegido),
        )

        registrar_evento_matricula(
            conn,
            numero_empleado=numero_empleado,
            id_capacitacion=id_capacitacion,
            nombre_curso=curso['nombre'],
            horario_elegido=horario_elegido,
            estado_codigo='PENDIENTE',
            matricula_id=nueva_matricula.lastrowid,
            detalle='Inscripción realizada por el docente',
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return {'ok': False, 'error': 'Error al procesar la matrícula.', 'error_view': 'index'}

    return {
        'ok': True,
        'empleado': numero_empleado,
        'nombre_curso': curso['nombre'],
        'id_curso': id_capacitacion,
        'horario': horario_elegido,
    }


def process_cancelar_matricula(numero_empleado, id_capacitacion, matricula_id):
    try:
        conn = get_db_connection()
        if matricula_id:
            matricula = conn.execute(
                '''
                SELECT m.id, m.id_capacitacion, c.nombre, m.horario_elegido
                FROM matriculas m
                JOIN capacitaciones c ON c.id = m.id_capacitacion
                WHERE m.id = ? AND m.numero_empleado = ?
                ''',
                (matricula_id, numero_empleado),
            ).fetchone()
            if not matricula:
                conn.close()
                return {'ok': False, 'http_status': 404}

            id_capacitacion = matricula['id_capacitacion']
            nombre_curso = matricula['nombre']
            registrar_evento_matricula(
                conn,
                numero_empleado=numero_empleado,
                id_capacitacion=id_capacitacion,
                nombre_curso=nombre_curso,
                horario_elegido=matricula['horario_elegido'],
                estado_codigo='CANCELADA',
                matricula_id=matricula['id'],
                detalle='Matrícula cancelada por el docente',
            )
            conn.execute(
                'DELETE FROM matriculas WHERE id = ? AND numero_empleado = ? AND aprobado IS NULL',
                (matricula_id, numero_empleado),
            )
        else:
            curso = conn.execute(
                'SELECT nombre FROM capacitaciones WHERE id = ?',
                (id_capacitacion,),
            ).fetchone()
            nombre_curso = curso['nombre'] if curso else id_capacitacion

            pendientes = conn.execute(
                '''
                SELECT id, horario_elegido
                FROM matriculas
                WHERE numero_empleado = ? AND id_capacitacion = ? AND aprobado IS NULL
                ''',
                (numero_empleado, id_capacitacion),
            ).fetchall()

            for fila in pendientes:
                registrar_evento_matricula(
                    conn,
                    numero_empleado=numero_empleado,
                    id_capacitacion=id_capacitacion,
                    nombre_curso=nombre_curso,
                    horario_elegido=fila['horario_elegido'],
                    estado_codigo='CANCELADA',
                    matricula_id=fila['id'],
                    detalle='Matrícula cancelada por el docente',
                )

            conn.execute(
                'DELETE FROM matriculas WHERE numero_empleado = ? AND id_capacitacion = ? AND aprobado IS NULL',
                (numero_empleado, id_capacitacion),
            )

        conn.commit()
        conn.close()
    except sqlite3.Error:
        return {'ok': False, 'error': 'Error al cancelar la matrícula.'}

    return {
        'ok': True,
        'empleado': numero_empleado,
        'nombre_curso': nombre_curso,
        'id_curso': id_capacitacion,
    }
