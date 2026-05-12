import sqlite3
from datetime import datetime

from config import LIMITE_ABANDONO, LIMITE_REPROBADO, MESES_ES
from database import get_db_connection
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


def _parse_fecha_limite(valor):
    texto = (valor or '').strip()
    if not texto:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None


def _partes_fecha_iso(fecha_iso):
    try:
        fecha_dt = datetime.strptime((fecha_iso or '').strip()[:10], '%Y-%m-%d')
    except ValueError:
        return None, None, None
    anio = str(fecha_dt.year)
    mes = MESES_ES[fecha_dt.month - 1]
    dia = str(fecha_dt.day)
    return anio, mes, dia


def _calcular_duracion_sesiones(sesiones):
    if not sesiones:
        return 0, 1

    total_horas = 0.0
    fechas = []
    for fila in sesiones:
        fecha_iso = (fila['fecha'] or '').strip()
        try:
            fecha_dt = datetime.strptime(fecha_iso[:10], '%Y-%m-%d')
            fechas.append(fecha_dt)
        except ValueError:
            pass

        hora_inicio = (fila['hora_inicio'] or '').strip()[:5]
        hora_fin = (fila['hora_fin'] or '').strip()[:5]
        try:
            hi = datetime.strptime(hora_inicio, '%H:%M')
            hf = datetime.strptime(hora_fin, '%H:%M')
            delta = (hf - hi).seconds / 3600
            if delta > 0:
                total_horas += delta
        except Exception:
            continue

    if not fechas:
        return int(round(total_horas)), 1

    fecha_inicio = min(fechas)
    fecha_fin = max(fechas)
    semanas = (max(0, (fecha_fin.date() - fecha_inicio.date()).days) // 7) + 1
    return int(round(total_horas)), semanas


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


def process_matricula(numero_empleado, edicion_id, horario_elegido=None):
    try:
        conn = get_db_connection()
        edicion = conn.execute(
            '''
            SELECT
                ef.id,
                ef.fecha_inicio,
                ef.fecha_limite_matricula,
                ef.cupos_maximos,
                ef.jornada,
                ef.hora,
                ef.privacidad,
                ef.estado,
                ca.nombre,
                ca.tipo_accion,
                ca.modalidad
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE ef.id = ?
            ''',
            (edicion_id,),
        ).fetchone()

        if not edicion:
            conn.close()
            return {'ok': False, 'error': 'Acción formativa inválida.', 'error_view': 'index'}

        if (edicion['privacidad'] or '').strip() != 'Abierta' or (edicion['estado'] or '').strip() != 'Programada':
            conn.close()
            return {'ok': False, 'error': 'Esta acción formativa no está disponible.', 'error_view': 'index'}

        fecha_limite = _parse_fecha_limite(edicion['fecha_limite_matricula'])
        if fecha_limite and datetime.now() > fecha_limite:
            contexto = construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles')
            conn.close()
            return {
                'ok': False,
                'error': f'La fecha límite de matrícula fue el {fecha_limite.strftime("%d/%m/%Y")}.',
                'error_view': 'dashboard',
                'contexto': contexto,
            }

        resumen_intentos = obtener_resumen_intentos_por_curso(conn, numero_empleado)
        clave_curso = normalizar_nombre_curso(edicion['nombre'])
        resumen_curso = resumen_intentos.get(
            clave_curso,
            {
                'nombre': edicion['nombre'],
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

        if edicion['cupos_maximos']:
            total_matriculas = conn.execute(
                'SELECT COUNT(*) AS total FROM matriculas WHERE edicion_id = ?',
                (edicion_id,),
            ).fetchone()
            if total_matriculas and total_matriculas['total'] >= int(edicion['cupos_maximos']):
                contexto = construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles')
                conn.close()
                return {
                    'ok': False,
                    'error': 'No hay cupos disponibles para esta acción formativa.',
                    'error_view': 'dashboard',
                    'contexto': contexto,
                }

        nueva_matricula = conn.execute(
            'INSERT INTO matriculas (numero_empleado, edicion_id) VALUES (?, ?)',
            (numero_empleado, edicion_id),
        )

        registrar_evento_matricula(
            conn,
            numero_empleado=numero_empleado,
            edicion_id=edicion_id,
            nombre_accion=edicion['nombre'],
            estado_codigo='PENDIENTE',
            matricula_id=nueva_matricula.lastrowid,
            detalle='Inscripción realizada por el docente',
        )
        horario_resumen = (obtener_horarios_disponibles_curso(conn, edicion_id) or [None])[0]
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return {'ok': False, 'error': 'Error al procesar la matrícula.', 'error_view': 'index'}

    return {
        'ok': True,
        'empleado': numero_empleado,
        'nombre_accion': edicion['nombre'],
        'edicion_id': edicion_id,
        'horario': horario_resumen,
    }


def process_cancelar_matricula(numero_empleado, edicion_id, matricula_id):
    try:
        conn = get_db_connection()
        if matricula_id:
            matricula = conn.execute(
                '''
                SELECT m.id, m.edicion_id, ca.nombre
                FROM matriculas m
                JOIN ediciones_formativas ef ON ef.id = m.edicion_id
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                WHERE m.id = ? AND m.numero_empleado = ?
                ''',
                (matricula_id, numero_empleado),
            ).fetchone()
            if not matricula:
                conn.close()
                return {'ok': False, 'http_status': 404}

            edicion_id = matricula['edicion_id']
            nombre_accion = matricula['nombre']
            registrar_evento_matricula(
                conn,
                numero_empleado=numero_empleado,
                edicion_id=edicion_id,
                nombre_accion=nombre_accion,
                estado_codigo='CANCELADA',
                matricula_id=matricula['id'],
                detalle='Matrícula cancelada por el docente',
            )
            conn.execute(
                'DELETE FROM matriculas WHERE id = ? AND numero_empleado = ? AND aprobado IS NULL',
                (matricula_id, numero_empleado),
            )
        else:
            accion = conn.execute(
                '''
                SELECT ca.nombre
                FROM ediciones_formativas ef
                JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                WHERE ef.id = ?
                ''',
                (edicion_id,),
            ).fetchone()
            nombre_accion = accion['nombre'] if accion else edicion_id

            pendientes = conn.execute(
                '''
                SELECT id
                FROM matriculas
                WHERE numero_empleado = ? AND edicion_id = ? AND aprobado IS NULL
                ''',
                (numero_empleado, edicion_id),
            ).fetchall()

            for fila in pendientes:
                registrar_evento_matricula(
                    conn,
                    numero_empleado=numero_empleado,
                    edicion_id=edicion_id,
                    nombre_accion=nombre_accion,
                    estado_codigo='CANCELADA',
                    matricula_id=fila['id'],
                    detalle='Matrícula cancelada por el docente',
                )

            conn.execute(
                'DELETE FROM matriculas WHERE numero_empleado = ? AND edicion_id = ? AND aprobado IS NULL',
                (numero_empleado, edicion_id),
            )

        conn.commit()
        conn.close()
    except sqlite3.Error:
        return {'ok': False, 'error': 'Error al cancelar la matrícula.'}

    return {
        'ok': True,
        'empleado': numero_empleado,
        'nombre_accion': nombre_accion,
        'edicion_id': edicion_id,
    }


def _estado_sesion_texto(estado):
    if estado == 1:
        return 'Abierta'
    if estado == 2:
        return 'Finalizada'
    return 'Cerrada'


def fetch_curso_detalle_docente(numero_empleado, edicion_id):
    edicion_id = (edicion_id or '').strip().upper()
    if not numero_empleado or not edicion_id:
        return {'ok': False, 'error': 'Datos inválidos', 'status_code': 400}

    try:
        conn = get_db_connection()

        matricula_docente = conn.execute(
            '''
            SELECT 1
            FROM matriculas
            WHERE numero_empleado = ? AND edicion_id = ?
            LIMIT 1
            ''',
            (numero_empleado, edicion_id),
        ).fetchone()

        historial_docente = conn.execute(
            '''
            SELECT 1
            FROM matricula_historial
            WHERE numero_empleado = ? AND edicion_id = ?
            LIMIT 1
            ''',
            (numero_empleado, edicion_id),
        ).fetchone()

        if not matricula_docente and not historial_docente:
            conn.close()
            return {'ok': False, 'error': 'No tienes acceso a este curso', 'status_code': 403}

        curso = conn.execute(
            '''
            SELECT
                ef.id,
                ef.trimestre,
                ef.fecha_inicio,
                ef.jornada,
                ef.hora,
                ef.enlace_acceso,
                ef.docente_responsable,
                ef.privacidad,
                ef.estado,
                ef.requisitos,
                ca.nombre,
                ca.modalidad,
                ca.tipo_accion,
                ca.id_plantilla_certificado,
                p.activo AS plantilla_activa,
                ddir.ruta_firma_img,
                p.texto_certificado
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca
                ON ca.id = ef.catalogo_id
            LEFT JOIN plantillas_certificados p
                ON p.id = ca.id_plantilla_certificado
            LEFT JOIN direcciones ddir
                ON ddir.codigo = p.direccion_codigo
            WHERE ef.id = ?
            LIMIT 1
            ''',
            (edicion_id,),
        ).fetchone()
        if not curso:
            conn.close()
            return {'ok': False, 'error': 'Curso no encontrado', 'status_code': 404}

        horarios = obtener_horarios_disponibles_curso(conn, edicion_id)

        matricula_activa = conn.execute(
            '''
            SELECT id, aprobado, fecha_matricula
            FROM matriculas
            WHERE numero_empleado = ? AND edicion_id = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (numero_empleado, edicion_id),
        ).fetchone()

        historial_ultimo = conn.execute(
            '''
            SELECT h.estado_codigo, c.nombre AS estado_nombre, h.fecha_evento
            FROM matricula_historial h
            LEFT JOIN estado_matricula_catalogo c ON c.codigo = h.estado_codigo
            WHERE h.numero_empleado = ? AND h.edicion_id = ?
            ORDER BY h.id DESC
            LIMIT 1
            ''',
            (numero_empleado, edicion_id),
        ).fetchone()

        estados_finales = {'APROBADA', 'NO_APROBADA', 'ABANDONO', 'CANCELADA'}
        estado_historial = (historial_ultimo['estado_codigo'] or '').strip().upper() if historial_ultimo else ''
        resultado_final_matricula = bool(matricula_activa and matricula_activa['aprobado'] is not None)
        puede_marcar_asistencia = bool(matricula_activa) and not resultado_final_matricula and estado_historial not in estados_finales

        jornada_docente_codigo = (curso['jornada'] or '').strip().upper() or 'UNICA'
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
                s.edicion_id,
                s.fecha,
                s.hora_inicio,
                s.hora_fin,
                s.estado,
                s.token_asistencia,
                ra.id_registro AS asistencia_id,
                ra.fecha_marcado,
                ra.hora_marcado
            FROM sesiones_curso s
            LEFT JOIN registro_asistencia ra
                ON ra.id_sesion = s.id_sesion AND ra.numero_empleado = ?
            WHERE s.edicion_id = ?
            ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
            ''',
            (numero_empleado, edicion_id),
        ).fetchall()
        conn.close()

        ahora = datetime.now()
        sesiones_pasadas = []
        sesiones_futuras = []

        horas_totales, semanas_duracion = _calcular_duracion_sesiones(sesiones)
        anio, mes, dia = _partes_fecha_iso(curso['fecha_inicio'])

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
                'edicion_id': fila['edicion_id'],
                'fecha': fila['fecha'],
                'hora_inicio': fila['hora_inicio'],
                'hora_fin': fila['hora_fin'],
                'jornada': jornada_docente,
                'docente_sesion': None,
                'edicion': None,
                'bloque_codigo': None,
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

        plantilla_disponible = bool(
            curso['id_plantilla_certificado']
            and int(curso['plantilla_activa'] or 0) == 1
            and (curso['ruta_firma_img'] or '').strip()
            and (curso['texto_certificado'] or '').strip()
        )

        return {
            'ok': True,
            'curso': {
                'id': curso['id'],
                'nombre': curso['nombre'],
                'anio': anio,
                'trimestre': curso['trimestre'],
                'mes': mes,
                'dia': dia,
                'fecha_inicio': curso['fecha_inicio'],
                'modalidad': curso['modalidad'],
                'duracion_tipo': 'un_dia',
                'tipo_accion': _normalizar_tipo_accion(curso['tipo_accion']),
                'requisitos': curso['requisitos'] or '',
                'horas_totales': horas_totales,
                'semanas_duracion': semanas_duracion,
                'enlace_virtual': curso['enlace_acceso'],
                'horarios': horarios,
                'matricula_activa': bool(matricula_activa),
                'puede_marcar_asistencia': puede_marcar_asistencia,
                'horario_matriculado': (
                    horarios[0] if horarios else None
                ),
                'matricula_id': matricula_activa['id'] if matricula_activa else None,
                'plantilla_disponible': plantilla_disponible,
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
            SELECT id_sesion, edicion_id, estado, token_asistencia
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
            WHERE numero_empleado = ? AND edicion_id = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (numero_empleado, sesion['edicion_id']),
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
            WHERE numero_empleado = ? AND edicion_id = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (numero_empleado, sesion['edicion_id']),
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
