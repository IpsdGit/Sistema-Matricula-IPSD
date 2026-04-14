from flask import jsonify, request, session

from services.ia_service import build_chat_reply, fetch_chat_history
from utils import validar_csrf


def _resolve_chat_user():
    if session.get('admin_logueado'):
        return 'admin', (session.get('admin_user') or 'admin').strip() or 'admin'

    empleado = (session.get('empleado_portal') or '').strip()
    if empleado:
        return 'docente', empleado

    return None, None


def register_chat_routes(app):
    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        user_type, user_id = _resolve_chat_user()
        if not user_type:
            return jsonify({'ok': False, 'error': 'Debes iniciar sesion para usar el chat.'}), 401

        payload = request.get_json(silent=True) or {}
        csrf_token = request.headers.get('X-CSRF-Token') or payload.get('_csrf_token')
        if not validar_csrf(csrf_token):
            return jsonify({'ok': False, 'error': 'Token de seguridad invalido.'}), 403

        result = build_chat_reply(user_type, user_id, payload.get('message'))
        if not result['ok']:
            return jsonify({'ok': False, 'error': result['error']}), result.get('http_status', 400)

        return jsonify({'ok': True, 'reply': result['reply']})

    @app.route('/api/chat/history', methods=['GET'])
    def api_chat_history():
        user_type, user_id = _resolve_chat_user()
        if not user_type:
            return jsonify({'ok': False, 'error': 'Debes iniciar sesion para usar el chat.'}), 401

        history = fetch_chat_history(user_type, user_id, limit=10)
        return jsonify({'ok': True, 'messages': history, 'user_type': user_type})
