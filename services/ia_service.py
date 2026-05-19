import os
import logging
import unicodedata

from dotenv import load_dotenv
from google import genai
from google.genai import types

from database import get_db_connection

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
MAX_USER_MESSAGE_LEN = 1200
FALLBACK_MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash']


def _get_system_prompt(user_type):
    base_prompt = (
        'Eres el asistente virtual del Sistema de Matricula IPSD. '
        'Responde en espanol, de forma breve, profesional y accionable. '
        'No inventes datos sensibles ni afirmes acciones del sistema que no puedas verificar. '
        'Si una solicitud requiere cambios administrativos, indica el flujo correcto dentro del portal. '
        'No des recomendaciones legales o medicas.'
    )

    if user_type == 'admin':
        return (
            f'{base_prompt} '
            'Estas atendiendo a un Administrador. '
            'Enfocate en soporte operativo: reportes, gestion de cursos, matriculas y usuarios admin. '
            'Usa solo nombres reales del sistema: Dashboard, Gestion de Cursos, Matriculas y Usuarios Admin. '
            'No inventes modulos o secciones que no existan.'
        )

    return (
        f'{base_prompt} '
        'Estas atendiendo a un Docente. '
        'Enfocate en orientacion para matricula, historial y uso del portal docente. '
        'Usa solo nombres reales del sistema: Historial Formativo y Disponibles para matricula. '
        'No menciones secciones inexistentes como Catalogo de Cursos.'
    )


def _normalize_text(value):
    raw = (value or '').strip().lower()
    normalized = unicodedata.normalize('NFKD', raw)
    return ''.join(ch for ch in normalized if not unicodedata.combining(ch))


def _try_domain_answer(user_type, user_message):
    txt = _normalize_text(user_message)

    if user_type == 'docente':
        if 'cancel' in txt or 'baja' in txt:
            return (
                'Si deseas cancelar una matricula, hazlo asi: '\
                '1) Entra a Disponibles para matricula. '\
                '2) En Mis Acciones Formativas ubica el curso. '\
                '3) Pulsa el boton X para cancelar. '\
                'Nota: si la matricula ya tiene resultado (aprobado/no aprobado/abandono), aparece bloqueada y no se puede cancelar.'
            )

        if 'matricul' in txt or 'inscrib' in txt:
            return (
                'Para matricularte en un curso: '\
                '1) Abre Disponibles para matricula. '\
                '2) Elige el curso y la Jornada preferida. '\
                '3) Pulsa Matricularme. '\
                '4) Verifica que aparezca en Mis Acciones Formativas. '\
                'Si no ves oferta, no hay cursos habilitados en este periodo.'
            )

        if 'historial' in txt or 'aprobad' in txt or 'reprobad' in txt or 'abandono' in txt:
            return (
                'Para revisar resultados usa Historial Formativo. Ahí puedes filtrar por: '\
                'Todas, Aprobadas, No Aprobadas y Canceladas. '\
                'Cada registro muestra curso, horario, estado final y fecha de evento.'
            )

        if 'disponible' in txt or 'curso' in txt or 'horario' in txt:
            return (
                'Las ofertas activas estan en Disponibles para matricula. '\
                'Ahi veras: codigo de curso, periodo, horarios y mensaje de oportunidades. '\
                'Selecciona horario y confirma para completar la inscripcion.'
            )

    if user_type == 'admin':
        if 'reporte' in txt or 'estadist' in txt or 'dashboard' in txt:
            return (
                'Para reportes rapidos, usa Dashboard. Encontraras metricas de matriculas, cursos y profesores, '\
                'ademas de graficas por curso y periodo.'
            )

        if 'curso' in txt or 'crear' in txt or 'editar' in txt:
            return (
                'La administracion de cursos se realiza en Gestion de Cursos: crear, editar y eliminar cursos, '\
                'definir modalidad, cupos y horarios.'
            )

        if 'matricul' in txt:
            return (
                'En Matriculas puedes consultar registros, actualizar resultado academico y aplicar filtros por periodo '
                'o estado para seguimiento operativo.'
            )

        if 'usuario' in txt or 'admin' in txt or 'direccion' in txt:
            return (
                'La gestion de administradores y direcciones esta en Usuarios Admin (solo superadmin). '\
                'Desde ahi se crean cuentas, se actualizan roles/direcciones y se administran catalogos.'
            )

    return None


def _normalize_reply_text(reply):
    text = (reply or '').strip()
    replacements = {
        'Catalogo de Cursos': 'Disponibles para matricula',
        'Catálogo de Cursos': 'Disponibles para matricula',
        'Catalogo de cursos': 'Disponibles para matricula',
        'catálogo de cursos': 'Disponibles para matricula',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _fetch_recent_history(user_type, user_id, limit=6):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT mensaje_usuario, respuesta_modelo, fecha_evento
                FROM historial_chat
                WHERE usuario_tipo = %s AND usuario_id = %s
                ORDER BY id DESC
                LIMIT %s
                ''',
                (user_type, user_id, limit),
            )
            rows = cur.fetchall()
        return list(reversed(rows))
    finally:
        conn.close()


def _build_prompt_with_history(rows, user_message):
    if not rows:
        return user_message

    bloques = []
    for row in rows:
        bloques.append(f"Usuario: {row['mensaje_usuario']}")
        bloques.append(f"Asistente: {row['respuesta_modelo']}")

    bloques.append(f'Usuario: {user_message}')
    bloques.append('Asistente:')
    return '\n'.join(bloques)


def _save_chat_exchange(user_type, user_id, user_message, model_reply):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO historial_chat (usuario_tipo, usuario_id, mensaje_usuario, respuesta_modelo)
                VALUES (%s, %s, %s, %s)
                ''',
                (user_type, user_id, user_message, model_reply),
            )
        conn.commit()
    finally:
        conn.close()


def _extract_response_text(response):
    text = (getattr(response, 'text', '') or '').strip()
    if text:
        return text

    candidates = getattr(response, 'candidates', None) or []
    for candidate in candidates:
        content = getattr(candidate, 'content', None)
        if not content:
            continue
        parts = getattr(content, 'parts', None) or []
        for part in parts:
            part_text = (getattr(part, 'text', '') or '').strip()
            if part_text:
                return part_text

    return ''


def _build_fallback_reply(user_type, user_message):
    domain = _try_domain_answer(user_type, user_message)
    if domain:
        return domain

    consulta = (user_message or '').lower()

    if 'matricul' in consulta:
        return (
            'Puedo ayudarte con matrícula. Ruta rápida: entra a "Disponibles para matrícula", '
            'elige el curso, selecciona horario y confirma. Si no ves cursos, revisa después porque '
            'la oferta depende del período habilitado por administración.'
        )

    if 'cancel' in consulta:
        return (
            'Para cancelar una matrícula activa, entra al panel de cursos matriculados y usa el botón de cancelación '
            '(✕) del curso. Si el curso ya tiene cierre de resultado, la matrícula aparece bloqueada y no se puede cancelar.'
        )

    if user_type == 'admin':
        return (
            'Estoy en modo de contingencia. Puedo orientarte en rutas del panel admin: '
            'Dashboard (estadísticas), Gestión de Cursos, Matrículas y Usuarios Admin.'
        )

    return (
        'Estoy en modo de contingencia. Puedo orientarte en el uso del portal docente: '
        'historial, cursos disponibles, matrícula y cancelación.'
    )


def build_chat_reply(user_type, user_id, message):
    user_message = (message or '').strip()
    if not user_message:
        return {'ok': False, 'error': 'Escribe un mensaje antes de enviar.', 'http_status': 400}

    if len(user_message) > MAX_USER_MESSAGE_LEN:
        return {
            'ok': False,
            'error': f'El mensaje es demasiado largo (maximo {MAX_USER_MESSAGE_LEN} caracteres).',
            'http_status': 400,
        }

    domain_answer = _try_domain_answer(user_type, user_message)
    if domain_answer:
        _save_chat_exchange(user_type, user_id, user_message, domain_answer)
        return {'ok': True, 'reply': domain_answer}

    api_key = os.environ.get('GOOGLE_GEMINI_API_KEY', '').strip()
    if not api_key:
        fallback = _build_fallback_reply(user_type, user_message)
        _save_chat_exchange(user_type, user_id, user_message, fallback)
        return {'ok': True, 'reply': fallback}

    recent_rows = _fetch_recent_history(user_type, user_id)
    prompt_con_contexto = _build_prompt_with_history(recent_rows, user_message)

    modelos_a_probar = [GEMINI_MODEL]
    for fallback in FALLBACK_MODELS:
        if fallback not in modelos_a_probar:
            modelos_a_probar.append(fallback)

    ultimo_error = None
    client = genai.Client(api_key=api_key)
    for model_name in modelos_a_probar:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_con_contexto,
                config=types.GenerateContentConfig(
                    system_instruction=_get_system_prompt(user_type),
                    temperature=0.35,
                    max_output_tokens=450,
                ),
            )
            reply_text = _extract_response_text(response)
            reply_text = _normalize_reply_text(reply_text)

            if not reply_text:
                reply_text = 'No pude generar una respuesta en este momento. Intenta nuevamente.'

            _save_chat_exchange(user_type, user_id, user_message, reply_text)
            return {'ok': True, 'reply': reply_text}
        except Exception as exc:
            ultimo_error = exc
            logger.warning('Fallo usando modelo %s: %s', model_name, exc)
            continue

    logger.error('No se pudo obtener respuesta de Gemini. Se usa fallback. Error final: %s', ultimo_error)
    fallback = _build_fallback_reply(user_type, user_message)
    _save_chat_exchange(user_type, user_id, user_message, fallback)
    return {'ok': True, 'reply': fallback}


def fetch_chat_history(user_type, user_id, limit=10):
    rows = _fetch_recent_history(user_type, user_id, limit=limit)
    history = []

    for row in rows:
        history.append(
            {
                'sender': 'user',
                'text': row['mensaje_usuario'],
                'timestamp': row['fecha_evento'],
            }
        )
        history.append(
            {
                'sender': 'assistant',
                'text': row['respuesta_modelo'],
                'timestamp': row['fecha_evento'],
            }
        )

    return history
