import os
import tempfile
import unittest
from unittest.mock import patch

fd, temp_db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)

os.environ['DATABASE_PATH'] = temp_db_path
os.environ['SECRET_KEY'] = 'test-secret-key'

from app import app


class ChatRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True

    def setUp(self):
        self.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except PermissionError:
                pass

    def _set_docente_session(self, csrf_token='token-docente'):
        with self.client.session_transaction() as sess:
            sess['empleado_portal'] = '13532'
            sess['_csrf_token'] = csrf_token

    def _set_admin_session(self, csrf_token='token-admin'):
        with self.client.session_transaction() as sess:
            sess['admin_logueado'] = True
            sess['admin_user'] = 'admin'
            sess['admin_rol'] = 'superadmin'
            sess['admin_direccion'] = 'GLOBAL'
            sess['_csrf_token'] = csrf_token

    def test_chat_requires_authentication(self):
        response = self.client.post('/api/chat', json={'message': 'Hola'})
        self.assertEqual(response.status_code, 401)

    def test_chat_requires_csrf(self):
        self._set_docente_session(csrf_token='seguro')
        response = self.client.post('/api/chat', json={'message': 'Hola'})
        self.assertEqual(response.status_code, 403)

    @patch('routes.chat.build_chat_reply')
    def test_chat_responds_for_admin(self, mock_build_chat_reply):
        mock_build_chat_reply.return_value = {'ok': True, 'reply': 'Respuesta de prueba'}
        self._set_admin_session(csrf_token='csrf-admin-1')

        response = self.client.post(
            '/api/chat',
            json={'message': 'Dame un resumen'},
            headers={'X-CSRF-Token': 'csrf-admin-1'},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['reply'], 'Respuesta de prueba')
        mock_build_chat_reply.assert_called_once_with('admin', 'admin', 'Dame un resumen')

    @patch('routes.chat.fetch_chat_history')
    def test_chat_history_for_docente(self, mock_fetch_chat_history):
        mock_fetch_chat_history.return_value = [
            {'sender': 'user', 'text': 'Hola', 'timestamp': '2026-01-01 10:00:00'},
            {'sender': 'assistant', 'text': 'Hola, te ayudo.', 'timestamp': '2026-01-01 10:00:01'},
        ]
        self._set_docente_session()

        response = self.client.get('/api/chat/history')
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['user_type'], 'docente')
        self.assertEqual(len(payload['messages']), 2)


if __name__ == '__main__':
    unittest.main()
