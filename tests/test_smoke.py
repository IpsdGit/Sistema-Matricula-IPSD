import os
import tempfile
import unittest

fd, temp_db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)

os.environ['DATABASE_PATH'] = temp_db_path
os.environ['SECRET_KEY'] = 'test-secret-key'

from app import app


class SmokeRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True

    def setUp(self):
        self.client = app.test_client()

    def _set_admin_session(self, superadmin=False, csrf_token=None):
        with self.client.session_transaction() as sess:
            sess['admin_logueado'] = True
            sess['admin_user'] = 'admin' if superadmin else 'admin_test'
            sess['admin_rol'] = 'superadmin' if superadmin else 'admin'
            sess['admin_direccion'] = 'GLOBAL' if superadmin else 'IPSD'
            if csrf_token is not None:
                sess['_csrf_token'] = csrf_token

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except PermissionError:
                pass

    def test_home_returns_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_login_admin_returns_200(self):
        response = self.client.get('/login_admin')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_without_session_returns_200(self):
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_logout_docente_redirects(self):
        response = self.client.get('/logout_docente')
        self.assertEqual(response.status_code, 302)

    def test_admin_without_session_redirects_login(self):
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)

    def test_admin_with_session_returns_200(self):
        self._set_admin_session(superadmin=True)
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 200)

    def test_admin_post_requires_csrf_when_authenticated(self):
        self._set_admin_session(superadmin=False)
        response = self.client.post('/admin/eliminar_matricula', data={
            'numero_empleado': '1234',
            'id_capacitacion': 'AF-IPSD-V-001',
        })
        self.assertEqual(response.status_code, 403)

    def test_superadmin_post_with_valid_csrf_redirects(self):
        csrf_token = 'token-prueba-123'
        self._set_admin_session(superadmin=True, csrf_token=csrf_token)

        response = self.client.post('/admin/vaciar_matriculas', data={
            '_csrf_token': csrf_token,
            'confirmacion': 'ELIMINAR',
        })
        self.assertEqual(response.status_code, 302)


if __name__ == '__main__':
    unittest.main()
