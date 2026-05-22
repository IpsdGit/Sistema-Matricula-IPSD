import os
import sqlite3
import unittest
from unittest.mock import patch

os.environ['SECRET_KEY'] = 'test-secret-key'

from app import app
DB_PATH = 'matricula.db'


class DocenteLoginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True

    def setUp(self):
        self.client = app.test_client()
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS docentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_empleado TEXT UNIQUE NOT NULL,
                nombre_completo TEXT NOT NULL,
                correo_institucional TEXT UNIQUE NOT NULL COLLATE NOCASE,
                activo INTEGER NOT NULL DEFAULT 1,
                fecha_sincronizacion DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        conn.execute('DELETE FROM docentes')
        conn.execute(
            '''
            INSERT INTO docentes (numero_empleado, nombre_completo, correo_institucional, activo)
            VALUES (?, ?, ?, ?)
            ''',
            ('12345678', 'Docente Prueba', 'docente.prueba@unah.edu.hn', 1),
        )
        conn.commit()
        conn.close()

    def _set_csrf_session(self, csrf_token='token-docente'):
        with self.client.session_transaction() as sess:
            sess['_csrf_token'] = csrf_token

    @patch('routes.portal.load_dashboard_context')
    def test_dashboard_login_acepta_correo_y_numero_validos(self, mock_load_dashboard_context):
        mock_load_dashboard_context.return_value = {
            'ok': True,
            'contexto': {
                'empleado': '12345678',
                'cursos': [],
                'matriculados': [],
                'avisos_oportunidades': [],
                'seccion_activa': 'disponibles',
                'filtro_historial': 'todas',
                'historial_acciones': [],
                'resumen_historial': {
                    'todas': 0,
                    'aprobadas': 0,
                    'no_aprobadas': 0,
                    'canceladas': 0,
                },
            },
        }
        self._set_csrf_session('csrf-1')

        response = self.client.post(
            '/dashboard',
            data={
                '_csrf_token': 'csrf-1',
                'correo_institucional': 'docente.prueba@unah.edu.hn',
                'numero_empleado': '12345678',
            },
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('empleado_portal'), '12345678')
            self.assertEqual(sess.get('correo_docente'), 'docente.prueba@unah.edu.hn')
            self.assertEqual(sess.get('nombre_docente'), 'Docente Prueba')

    @patch('routes.portal.load_dashboard_context')
    def test_dashboard_login_rechaza_credenciales_invalidas(self, mock_load_dashboard_context):
        self._set_csrf_session('csrf-2')

        response = self.client.post(
            '/dashboard',
            data={
                '_csrf_token': 'csrf-2',
                'correo_institucional': 'otro@unah.edu.hn',
                'numero_empleado': '12345678',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Credenciales inválidas'.encode('utf-8'), response.data)
        mock_load_dashboard_context.assert_not_called()


if __name__ == '__main__':
    unittest.main()
