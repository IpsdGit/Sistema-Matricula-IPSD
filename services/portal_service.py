import sqlite3
from datetime import datetime

from config import LIMITE_ABANDONO, LIMITE_REPROBADO, MESES_ES
from database import get_db_connection
from services.admin_service import _resolver_jornada_desde_horario
from utils import (
    construir_contexto_dashboard,
    normalizar_nombre_curso,
    obtener_horarios_disponibles_curso,
    obtener_resumen_intentos_por_curso,
    registrar_evento_matricula,
)


def _normalizar_tipo_accion(valor):
    tipo = (valor or '').strip().upper()
    if tipo not in {'CONFERENCIA', 'SEMINARIO', 'CURSO'}:
        return 'CURSO'
    return tipo


def _fecha_inicio_curso(anio, mes_nombre, dia):
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
        return datetime(anio_int, mes_int, dia_int).date()
    except ValueError:
        return None


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
            'SELECT id, nombre, anio, mes, dia FROM capacitaciones WHERE id = ?',
            (id_capacitacion,),
        ).fetchone()
        horarios_disponibles = obtener_horarios_disponibles_curso(conn, id_capacitacion)
        horario_valido = horario_elegido in horarios_disponibles

        if not curso or not horario_valido:
            conn.close()
            return {'ok': False, 'error': 'Curso o horario inválido.', 'error_view': 'index'}

        fecha_inicio = _fecha_inicio_curso(curso['anio'], curso['mes'], curso['dia'])
        hoy = datetime.now().date()
        if fecha_inicio and hoy > fecha_inicio:
            contexto = construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles')
            conn.close()
            return {
                'ok': False,
                'error': f'La fecha máxima de matrícula para este curso fue el {fecha_inicio.strftime("%d/%m/%Y")}.',
                'error_view': 'dashboard',
                'contexto': contexto,
            }

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


def _estado_sesion_texto(estado):
    if estado == 1:
        return 'Abierta'
    if estado == 2:
        return 'Finalizada'
    return 'Cerrada'


def fetch_curso_detalle_docente(numero_empleado, id_curso):
    id_curso = (id_curso or '').strip().upper()
    if not numero_empleado or not id_curso:
        return {'ok': False, 'error': 'Datos inválidos', 'status_code': 400}

    try:
        conn = get_db_connection()

        matricula_docente = conn.execute(
            '''
            SELECT 1
            FROM matriculas
            WHERE numero_empleado = ? AND id_capacitacion = ?
            LIMIT 1
            ''',
            (numero_empleado, id_curso),
        ).fetchone()

        historial_docente = conn.execute(
            '''
            SELECT 1
            FROM matricula_historial
            WHERE numero_empleado = ? AND id_capacitacion = ?
            LIMIT 1
            ''',
            (numero_empleado, id_curso),
        ).fetchone()

        if not matricula_docente and not historial_docente:
            conn.close()
            return {'ok': False, 'error': 'No tienes acceso a este curso', 'status_code': 403}

        curso = conn.execute(
            '''
            SELECT id, nombre, anio, trimestre, mes, dia, modalidad, enlace_virtual, duracion_tipo,
                   tipo_accion, horas_totales, semanas_duracion, id_plantilla_certificado
            FROM capacitaciones
            WHERE id = ?
            LIMIT 1
            ''',
            (id_curso,),
        ).fetchone()
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Curso no encontrado', 'status_code': 404}

        horarios = obtener_horarios_disponibles_curso(conn, id_curso)

        matricula_activa = conn.execute(
            '''
            SELECT id, horario_elegido, aprobado, fecha_matricula
            FROM matriculas
            WHERE numero_empleado = ? AND id_capacitacion = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (numero_empleado, id_curso),
        ).fetchone()

        historial_ultimo = conn.execute(
            '''
            SELECT h.estado_codigo, c.nombre AS estado_nombre, h.horario_elegido, h.fecha_evento
            FROM matricula_historial h
            LEFT JOIN estado_matricula_catalogo c ON c.codigo = h.estado_codigo
            WHERE h.numero_empleado = ? AND h.id_capacitacion = ?
            ORDER BY h.id DESC
            LIMIT 1
            ''',
            (numero_empleado, id_curso),
        ).fetchone()

        estados_finales = {'APROBADA', 'NO_APROBADA', 'ABANDONO', 'CANCELADA'}
        estado_historial = (historial_ultimo['estado_codigo'] or '').strip().upper() if historial_ultimo else ''
        resultado_final_matricula = bool(matricula_activa and matricula_activa['aprobado'] is not None)
        puede_marcar_asistencia = bool(matricula_activa) and not resultado_final_matricula and estado_historial not in estados_finales

        jornadas_sesiones_raw = conn.execute(
            '''
            SELECT jornada, hora_inicio, hora_fin
            FROM sesiones_curso
            WHERE id_curso = ?
            ''',
            (id_curso,),
        ).fetchall()

        jornadas_sesiones = {}
        for fila in jornadas_sesiones_raw:
            jornada = (fila['jornada'] or '').strip().upper() or 'UNICA'
            hora_inicio = (fila['hora_inicio'] or '').strip()[:5]
            hora_fin = (fila['hora_fin'] or '').strip()[:5]
            if jornada not in jornadas_sesiones:
                jornadas_sesiones[jornada] = {'rangos': set()}
            if hora_inicio and hora_fin:
                jornadas_sesiones[jornada]['rangos'].add((hora_inicio, hora_fin))

        horario_referencia = (
            matricula_activa['horario_elegido']
            if matricula_activa and matricula_activa['horario_elegido']
            else (historial_ultimo['horario_elegido'] if historial_ultimo else '')
        )
        jornada_docente_codigo = _resolver_jornada_desde_horario(horario_referencia, jornadas_sesiones)
        nombres_jornada = {
            'UNICA': 'Unica',
            'MATUTINA': 'Matutina',
            'VESPERTINA': 'Vespertina',
            'NOCTURNA': 'Nocturna',
            'POR_CONFIRMAR': 'Por confirmar',
        }
        jornada_docente = nombres_jornada.get(jornada_docente_codigo, 'Por confirmar')

        sesiones = conn.execute(
            '''
            SELECT
                s.id_sesion,
                s.id_curso,
                s.fecha,
                s.hora_inicio,
                s.hora_fin,
                s.jornada,
                s.docente_sesion,
                s.edicion,
                s.estado,
                s.token_asistencia,
                ra.id_registro AS asistencia_id,
                ra.fecha_marcado,
                ra.hora_marcado
            FROM sesiones_curso s
            LEFT JOIN registro_asistencia ra
                ON ra.id_sesion = s.id_sesion AND ra.numero_empleado = ?
            WHERE s.id_curso = ?
              AND (s.jornada = ? OR s.jornada = 'UNICA')
            ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
            ''',
            (numero_empleado, id_curso, jornada_docente_codigo),
        ).fetchall()
        conn.close()

        ahora = datetime.now()
        sesiones_pasadas = []
        sesiones_futuras = []

        for fila in sesiones:
            fecha_iso = fila['fecha']
            hora_inicio = fila['hora_inicio']
            fecha_hora_sesion = None
            try:
                fecha_hora_sesion = datetime.strptime(f'{fecha_iso} {hora_inicio}', '%Y-%m-%d %H:%M')
            except ValueError:
                fecha_hora_sesion = None

            registro = {
                'id_sesion': fila['id_sesion'],
                'id_curso': fila['id_curso'],
                'fecha': fila['fecha'],
                'hora_inicio': fila['hora_inicio'],
                'hora_fin': fila['hora_fin'],
                'jornada': fila['jornada'],
                'docente_sesion': fila['docente_sesion'],
                'edicion': fila['edicion'],
                'bloque_codigo': fila['edicion'],
                'estado': fila['estado'],
                'estado_texto': _estado_sesion_texto(fila['estado']),
                'token_asistencia': fila['token_asistencia'] if fila['estado'] == 1 and puede_marcar_asistencia else None,
                'asistencia_marcada': fila['asistencia_id'] is not None,
                'fecha_marcado': fila['fecha_marcado'],
                'hora_marcado': fila['hora_marcado'],
            }

            if fecha_hora_sesion and fecha_hora_sesion < ahora:
                sesiones_pasadas.append(registro)
            else:
                sesiones_futuras.append(registro)

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
                'duracion_tipo': curso['duracion_tipo'] if curso['duracion_tipo'] in {'un_dia', 'varios_dias'} else 'un_dia',
                'tipo_accion': _normalizar_tipo_accion(curso['tipo_accion']),
                'horas_totales': curso['horas_totales'] if curso['horas_totales'] else 0,
                'semanas_duracion': curso['semanas_duracion'] if curso['semanas_duracion'] else 1,
                'enlace_virtual': curso['enlace_virtual'],
                'horarios': horarios,
                'matricula_activa': bool(matricula_activa),
                'puede_marcar_asistencia': puede_marcar_asistencia,
                'horario_matriculado': (
                    matricula_activa['horario_elegido'] if matricula_activa and matricula_activa['horario_elegido']
                    else (historial_ultimo['horario_elegido'] if historial_ultimo else None)
                ),
                'matricula_id': matricula_activa['id'] if matricula_activa else None,
                'plantilla_disponible': bool(curso['id_plantilla_certificado']),
                'estado_matricula': historial_ultimo['estado_codigo'] if historial_ultimo else None,
                'estado_matricula_nombre': historial_ultimo['estado_nombre'] if historial_ultimo else None,
                'fecha_ultimo_estado': historial_ultimo['fecha_evento'] if historial_ultimo else None,
            },
            'sesiones_pasadas': sesiones_pasadas,
            'sesiones_futuras': sesiones_futuras,
            'jornada_docente': jornada_docente,
        }
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo cargar el detalle del curso', 'status_code': 500}


def marcar_asistencia_docente(numero_empleado, id_sesion, token_asistencia):
    try:
        id_sesion_int = int(id_sesion)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Sesión inválida', 'status_code': 400}

    token_asistencia = (token_asistencia or '').strip()
    if not numero_empleado or not token_asistencia:
        return {'ok': False, 'error': 'Token inválido', 'status_code': 400}

    try:
        conn = get_db_connection()
        sesion = conn.execute(
            '''
            SELECT id_sesion, id_curso, estado, token_asistencia
            FROM sesiones_curso
            WHERE id_sesion = ?
            LIMIT 1
            ''',
            (id_sesion_int,),
        ).fetchone()
        if not sesion:
            conn.close()
            return {'ok': False, 'error': 'Sesión no encontrada', 'status_code': 404}

        if sesion['estado'] != 1:
            conn.close()
            return {'ok': False, 'error': 'La sesión no está habilitada para asistencia', 'status_code': 409}

        if (sesion['token_asistencia'] or '') != token_asistencia:
            conn.close()
            return {'ok': False, 'error': 'Token de asistencia inválido', 'status_code': 403}

        matricula_docente = conn.execute(
            '''
            SELECT aprobado
            FROM matriculas
            WHERE numero_empleado = ? AND id_capacitacion = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (numero_empleado, sesion['id_curso']),
        ).fetchone()
        if not matricula_docente:
            conn.close()
            return {'ok': False, 'error': 'No tienes matrícula en este curso', 'status_code': 403}

        if matricula_docente['aprobado'] is not None:
            conn.close()
            return {
                'ok': False,
                'error': 'Este curso ya tiene resultado final y no permite marcar asistencia',
                'status_code': 409,
            }

        historial_ultimo = conn.execute(
            '''
            SELECT estado_codigo
            FROM matricula_historial
            WHERE numero_empleado = ? AND id_capacitacion = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (numero_empleado, sesion['id_curso']),
        ).fetchone()

        estado_historial = (historial_ultimo['estado_codigo'] or '').strip().upper() if historial_ultimo else ''
        if estado_historial in {'APROBADA', 'NO_APROBADA', 'ABANDONO', 'CANCELADA'}:
            conn.close()
            return {
                'ok': False,
                'error': 'Tu matrícula en este curso ya está cerrada y no permite asistencia',
                'status_code': 409,
            }

        existe_asistencia = conn.execute(
            '''
            SELECT 1
            FROM registro_asistencia
            WHERE id_sesion = ? AND numero_empleado = ?
            LIMIT 1
            ''',
            (id_sesion_int, numero_empleado),
        ).fetchone()
        if existe_asistencia:
            conn.close()
            return {'ok': False, 'error': 'Ya registraste asistencia para esta sesión', 'status_code': 409}

        ahora = datetime.now()
        conn.execute(
            '''
            INSERT INTO registro_asistencia (id_sesion, numero_empleado, fecha_marcado, hora_marcado)
            VALUES (?, ?, ?, ?)
            ''',
            (
                id_sesion_int,
                numero_empleado,
                ahora.strftime('%Y-%m-%d'),
                ahora.strftime('%H:%M:%S'),
            ),
        )
        conn.commit()
        conn.close()

        return {'ok': True, 'mensaje': 'Asistencia registrada correctamente'}
    except sqlite3.IntegrityError:
        return {'ok': False, 'error': 'Asistencia duplicada', 'status_code': 409}
    except sqlite3.Error:
        return {'ok': False, 'error': 'No se pudo registrar la asistencia', 'status_code': 500}
