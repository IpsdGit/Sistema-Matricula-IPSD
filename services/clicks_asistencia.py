"""
clicks_asistencia.py
Servicio de control de atención por clics para acciones formativas de tipo CONFERENCIA.

Flujo:
  - La sesión se activa automáticamente cuando llega la hora_inicio.
  - El admin configura hasta 5 ventanas (minutos desde inicio) en las que se habilita el botón.
  - Cada ventana dura DURACION_VENTANA_SEG segundos (3 min por defecto).
  - El admin puede forzar una ventana manual (override) en cualquier momento.
  - Al completar MINIMO_CLICKS (4) el docente es aprobado automáticamente.
"""
import json
from datetime import datetime, timedelta

import psycopg2

from utils import registrar_evento_matricula

# ── Constantes configurables ───────────────────────────────────────────────
MINIMO_CLICKS = 4            # clics mínimos para aprobar
DURACION_VENTANA_SEG = 180   # 3 minutos de ventana por clic
MAX_VENTANAS = 5             # máximo de ventanas configurables
DURACION_CONFERENCIA_MIN = 120  # duración estándar de una conferencia


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_hora(hora_str: str):
    """Convierte 'HH:MM' o 'HH:MM:SS' a (hora, minuto)."""
    partes = (hora_str or '').strip().split(':')
    if len(partes) >= 2:
        try:
            return int(partes[0]), int(partes[1])
        except ValueError:
            pass
    return 0, 0


def _sesion_inicio_dt(sesion) -> datetime | None:
    """Construye el datetime de inicio de la sesión a partir de fecha y hora_inicio."""
    fecha_str = str(sesion['fecha'])[:10]
    hora, minuto = _parse_hora(str(sesion['hora_inicio']))
    try:
        d = datetime.strptime(fecha_str, '%Y-%m-%d')
        return d.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    except (ValueError, TypeError):
        return None


def _cargar_lista(valor) -> list:
    """Deserializa un campo JSONB (puede llegar como str, list o None)."""
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    try:
        return json.loads(valor)
    except Exception:
        return []


def _fetch_sesion(conn, id_sesion: int):
    """Obtiene los datos de la sesión incluyendo tipo_accion del catálogo."""
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT
                sc.id_sesion,
                sc.edicion_id,
                sc.fecha,
                sc.hora_inicio,
                sc.hora_fin,
                sc.estado,
                sc.ventanas_atencion,
                sc.ventana_forzada_expira,
                sc.ventana_forzada_idx,
                ca.tipo_accion
            FROM sesiones_curso sc
            JOIN ediciones_formativas ef ON ef.id = sc.edicion_id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE sc.id_sesion = %s
            LIMIT 1
            ''',
            (id_sesion,)
        )
        return cur.fetchone()


def _fetch_registro(conn, id_sesion: int, numero_empleado: str):
    """Obtiene el registro de asistencia del docente para esa sesión."""
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT ventanas_completadas, aprobado_automatico
            FROM registro_asistencia
            WHERE id_sesion = %s AND numero_empleado = %s
            LIMIT 1
            ''',
            (id_sesion, numero_empleado)
        )
        return cur.fetchone()


# ── API pública del servicio ────────────────────────────────────────────────

def get_estado_ventana(conn, id_sesion: int, numero_empleado: str) -> dict:
    """
    Retorna el estado actual de las ventanas de atención para un docente.
    Llamado por el frontend (~cada 25 s) para actualizar la UI.
    """
    sesion = _fetch_sesion(conn, id_sesion)
    if not sesion:
        return {'ok': False, 'error': 'Sesión no encontrada', 'status_code': 404}

    tipo_accion = (sesion['tipo_accion'] or '').strip().upper()
    if tipo_accion != 'CONFERENCIA':
        return {'ok': False, 'error': 'Esta sesión no es de tipo CONFERENCIA', 'status_code': 400}

    inicio_dt = _sesion_inicio_dt(sesion)
    if not inicio_dt:
        return {'ok': False, 'error': 'Fecha/hora de sesión inválida', 'status_code': 500}

    now = datetime.now()
    minutos_transcurridos = int((now - inicio_dt).total_seconds() / 60)

    # Datos del docente
    registro = _fetch_registro(conn, id_sesion, numero_empleado)
    ventanas_completadas = []
    aprobado = False
    if registro:
        ventanas_completadas = _cargar_lista(registro['ventanas_completadas'])
        aprobado = bool(registro['aprobado_automatico'])

    ventanas_config = _cargar_lista(sesion['ventanas_atencion'])
    total_ventanas = len(ventanas_config) if ventanas_config else 5

    # La conferencia solo aplica el mismo día
    if inicio_dt.date() != now.date():
        return _estado_inactivo('La conferencia no es hoy', ventanas_completadas, total_ventanas, aprobado)

    # Aún no ha iniciado
    if now < inicio_dt:
        seg_para_inicio = int((inicio_dt - now).total_seconds())
        return {**_estado_inactivo('La conferencia aún no ha iniciado', ventanas_completadas, total_ventanas, aprobado),
                'segundos_para_inicio': seg_para_inicio}

    ventana_activa = None

    # 1. Ventana forzada por admin (prioridad alta)
    forzada_expira = sesion['ventana_forzada_expira']
    if forzada_expira and now <= forzada_expira:
        ventana_idx = sesion['ventana_forzada_idx'] or 0
        if ventana_idx not in ventanas_completadas:
            seg_restantes = max(0, int((forzada_expira - now).total_seconds()))
            ventana_activa = {
                'ventana_id': ventana_idx,
                'tipo': 'forzada',
                'segundos_restantes': seg_restantes,
            }

    # 2. Ventanas programadas
    if not ventana_activa:
        for idx, hora_ventana in enumerate(ventanas_config, start=1):
            if idx in ventanas_completadas:
                continue
                
            try:
                hora, minuto = map(int, str(hora_ventana).split(':'))
                ventana_dt = now.replace(hour=hora, minute=minuto, second=0, microsecond=0)
            except ValueError:
                continue
                
            delta_seg = (now - ventana_dt).total_seconds()
            if 0 <= delta_seg < DURACION_VENTANA_SEG:
                seg_restantes = max(0, int(DURACION_VENTANA_SEG - delta_seg))
                ventana_activa = {
                    'ventana_id': idx,
                    'tipo': 'programada',
                    'hora_programada': hora_ventana,
                    'segundos_restantes': seg_restantes,
                }
                break

    return {
        'ok': True,
        'conferencia_activa': True,
        'minutos_transcurridos': minutos_transcurridos,
        'ventana_activa': ventana_activa,
        'ventanas_completadas': ventanas_completadas,
        'total_completadas': len(ventanas_completadas),
        'total_ventanas': len(ventanas_config),
        'aprobado': aprobado,
    }


def registrar_clic(conn, id_sesion: int, numero_empleado: str, ventana_id: int) -> dict:
    """
    Registra el clic del docente en la ventana activa.
    Si alcanza MINIMO_CLICKS aprueba la matrícula automáticamente.
    """
    estado = get_estado_ventana(conn, id_sesion, numero_empleado)
    if not estado.get('ok'):
        return estado

    if not estado.get('conferencia_activa'):
        return {'ok': False, 'error': 'La conferencia no está activa en este momento.', 'status_code': 409}

    ventana_activa = estado.get('ventana_activa')
    if not ventana_activa:
        return {'ok': False, 'error': 'No hay ventana activa en este momento.', 'status_code': 409}

    if ventana_activa['ventana_id'] != ventana_id:
        return {'ok': False, 'error': 'ID de ventana no coincide con la ventana activa.', 'status_code': 409}

    if ventana_id in estado['ventanas_completadas']:
        return {'ok': False, 'error': 'Ya confirmaste esta ventana de atención.', 'status_code': 409}

    nuevas_completadas = estado['ventanas_completadas'] + [ventana_id]
    total = len(nuevas_completadas)
    aprobado_auto = total >= MINIMO_CLICKS

    ahora = datetime.now()
    fecha_str = ahora.strftime('%Y-%m-%d')
    hora_str = ahora.strftime('%H:%M:%S')

    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO registro_asistencia
                    (id_sesion, numero_empleado, fecha_marcado, hora_marcado,
                     tipo_registro, ventanas_completadas, aprobado_automatico)
                VALUES (%s, %s, %s, %s, 'CONFERENCIA', %s, %s)
                ON CONFLICT (id_sesion, numero_empleado)
                DO UPDATE SET
                    ventanas_completadas = EXCLUDED.ventanas_completadas,
                    aprobado_automatico  = EXCLUDED.aprobado_automatico
                ''',
                (
                    id_sesion, numero_empleado, fecha_str, hora_str,
                    json.dumps(nuevas_completadas), aprobado_auto,
                )
            )

        if aprobado_auto:
            _aprobar_matricula_automatica(conn, id_sesion, numero_empleado)

        conn.commit()
        return {
            'ok': True,
            'ventanas_completadas': nuevas_completadas,
            'total_completadas': total,
            'aprobado_automatico': aprobado_auto,
            'mensaje': (
                '¡Confirmación registrada! ¡Has aprobado la conferencia!' if aprobado_auto
                else '¡Confirmación registrada correctamente!'
            ),
        }
    except psycopg2.Error as e:
        return {'ok': False, 'error': f'Error de base de datos: {e}', 'status_code': 500}


def guardar_ventanas(conn, id_sesion: int, ventanas: list) -> dict:
    """
    Guarda la configuración de ventanas de atención (admin).
    ventanas: lista de strings representando horas específicas (HH:MM).
    """
    if not isinstance(ventanas, list) or len(ventanas) == 0 or len(ventanas) > MAX_VENTANAS:
        return {'ok': False, 'error': f'Debe configurar entre 1 y {MAX_VENTANAS} ventanas.'}

    import re
    ventanas_limpias = []
    for v in ventanas:
        v_str = str(v).strip()
        if not re.match(r'^(?:[01]\d|2[0-3]):[0-5]\d$', v_str):
            return {'ok': False, 'error': f'Valor inválido: {v}. Debe estar en formato HH:MM.'}
        ventanas_limpias.append(v_str)

    ventanas_ordenadas = sorted(set(ventanas_limpias))

    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE sesiones_curso SET ventanas_atencion = %s WHERE id_sesion = %s',
                (json.dumps(ventanas_ordenadas), id_sesion)
            )
        conn.commit()
        return {'ok': True, 'ventanas': ventanas_ordenadas}
    except psycopg2.Error as e:
        return {'ok': False, 'error': str(e)}


def forzar_ventana(conn, id_sesion: int, ventana_idx: int) -> dict:
    """
    Fuerza una ventana activa durante DURACION_VENTANA_SEG segundos (admin — override).
    """
    if not (1 <= ventana_idx <= MAX_VENTANAS):
        return {'ok': False, 'error': f'ventana_idx debe estar entre 1 y {MAX_VENTANAS}.'}

    expira = datetime.now() + timedelta(seconds=DURACION_VENTANA_SEG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE sesiones_curso
                SET ventana_forzada_expira = %s,
                    ventana_forzada_idx    = %s
                WHERE id_sesion = %s
                ''',
                (expira, ventana_idx, id_sesion)
            )
        conn.commit()
        return {
            'ok': True,
            'ventana_idx': ventana_idx,
            'expira': expira.isoformat(),
            'segundos': DURACION_VENTANA_SEG,
        }
    except psycopg2.Error as e:
        return {'ok': False, 'error': str(e)}


def get_config_ventanas(conn, id_sesion: int) -> dict:
    """Retorna la configuración actual de ventanas de una sesión (admin)."""
    sesion = _fetch_sesion(conn, id_sesion)
    if not sesion:
        return {'ok': False, 'error': 'Sesión no encontrada', 'status_code': 404}

    ventanas = _cargar_lista(sesion['ventanas_atencion'])
    now = datetime.now()
    forzada_expira = sesion['ventana_forzada_expira']
    ventana_forzada_activa = bool(forzada_expira and now <= forzada_expira)

    return {
        'ok': True,
        'tipo_accion': sesion['tipo_accion'],
        'ventanas': ventanas,
        'ventana_forzada_activa': ventana_forzada_activa,
        'ventana_forzada_idx': sesion['ventana_forzada_idx'],
        'ventana_forzada_expira': forzada_expira.isoformat() if forzada_expira else None,
    }


# ── Lógica interna ─────────────────────────────────────────────────────────

def _estado_inactivo(motivo: str, ventanas_completadas=None, total_ventanas=0, aprobado=False) -> dict:
    if ventanas_completadas is None:
        ventanas_completadas = []
    return {
        'ok': True,
        'conferencia_activa': False,
        'motivo': motivo,
        'ventana_activa': None,
        'ventanas_completadas': ventanas_completadas,
        'total_completadas': len(ventanas_completadas),
        'total_ventanas': total_ventanas,
        'aprobado': aprobado,
    }


def _aprobar_matricula_automatica(conn, id_sesion: int, numero_empleado: str):
    """Busca la matrícula pendiente y la marca como aprobada."""
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT m.id, m.edicion_id, ca.nombre
            FROM matriculas m
            JOIN sesiones_curso sc ON sc.edicion_id = m.edicion_id
            JOIN ediciones_formativas ef ON ef.id = m.edicion_id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE sc.id_sesion = %s
              AND m.numero_empleado = %s
              AND m.aprobado IS NULL
            ORDER BY m.id DESC
            LIMIT 1
            ''',
            (id_sesion, numero_empleado)
        )
        matricula = cur.fetchone()

    if not matricula:
        return  # Ya estaba aprobada o no existe

    ahora = datetime.now()
    with conn.cursor() as cur:
        cur.execute(
            '''
            UPDATE matriculas
            SET aprobado              = 1,
                fecha_aprobacion      = %s,
                comentario_validacion = %s
            WHERE id = %s
            ''',
            (
                ahora.strftime('%Y-%m-%d'),
                'Aprobado automáticamente por control de atención en conferencia '
                f'(≥{MINIMO_CLICKS}/{MAX_VENTANAS} ventanas respondidas)',
                matricula['id'],
            )
        )

    registrar_evento_matricula(
        conn,
        numero_empleado=numero_empleado,
        edicion_id=matricula['edicion_id'],
        nombre_accion=matricula['nombre'],
        estado_codigo='APROBADA',
        matricula_id=matricula['id'],
        detalle=(
            f'Aprobado automáticamente: completó ≥{MINIMO_CLICKS}/{MAX_VENTANAS} '
            'ventanas de atención en conferencia'
        ),
    )
