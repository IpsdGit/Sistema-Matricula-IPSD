import os
import re
import sqlite3

from werkzeug.security import generate_password_hash

from config import DB_PATH


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def asegurar_migraciones_minimas():
    """Evita fallos en despliegues donde aún no se ha corrido parche.py."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'admin',
                direccion TEXT NOT NULL DEFAULT 'IPSD'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS direcciones (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL
            )
        ''')

        cursor.execute(
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
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_docentes_numero ON docentes (numero_empleado)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_docentes_correo ON docentes (correo_institucional)'
        )

        direcciones_admin = cursor.execute(
            '''
            SELECT DISTINCT direccion
            FROM admin_users
            WHERE rol = 'admin' AND direccion IS NOT NULL AND TRIM(direccion) <> ''
            '''
        ).fetchall()
        for row in direcciones_admin:
            codigo_dir = (row[0] or '').strip().upper().replace(' ', '')
            if codigo_dir and codigo_dir != 'GLOBAL':
                if not re.match(r'^[A-Z0-9]{2,12}$', codigo_dir):
                    continue
                cursor.execute(
                    'INSERT OR IGNORE INTO direcciones (codigo, nombre) VALUES (?, ?)',
                    (codigo_dir, codigo_dir)
                )

        cursos_ids = cursor.execute(
            "SELECT id FROM capacitaciones WHERE id LIKE 'AF-%'"
        ).fetchall()
        for row in cursos_ids:
            course_id = (row[0] or '').upper()
            match = re.match(r'^AF-([A-Z0-9]{2,12})-[VP]-\d{3}$', course_id)
            if match:
                codigo_dir = match.group(1)
                cursor.execute(
                    'INSERT OR IGNORE INTO direcciones (codigo, nombre) VALUES (?, ?)',
                    (codigo_dir, codigo_dir)
                )

        columnas_admin = {
            row[1] for row in cursor.execute('PRAGMA table_info(admin_users)').fetchall()
        }
        if 'rol' not in columnas_admin:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN rol TEXT NOT NULL DEFAULT 'admin'")
        if 'direccion' not in columnas_admin:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN direccion TEXT NOT NULL DEFAULT 'IPSD'")

        columnas_capacitaciones = {
            row[1] for row in cursor.execute('PRAGMA table_info(capacitaciones)').fetchall()
        }
        if 'enlace_virtual' not in columnas_capacitaciones:
            cursor.execute('ALTER TABLE capacitaciones ADD COLUMN enlace_virtual TEXT')

        columnas_matriculas = {
            row[1] for row in cursor.execute('PRAGMA table_info(matriculas)').fetchall()
        }
        if 'fecha_matricula' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN fecha_matricula DATETIME DEFAULT CURRENT_TIMESTAMP')
        if 'aprobado' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN aprobado INTEGER')

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS estado_matricula_catalogo (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                categoria TEXT NOT NULL,
                orden INTEGER NOT NULL
            )
            '''
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS matricula_historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricula_id INTEGER,
                numero_empleado TEXT NOT NULL,
                id_capacitacion TEXT NOT NULL,
                nombre_curso TEXT NOT NULL,
                horario_elegido TEXT,
                estado_codigo TEXT NOT NULL,
                detalle TEXT,
                fecha_evento DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (estado_codigo) REFERENCES estado_matricula_catalogo (codigo)
            )
            '''
        )

        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_historial_empleado_fecha ON matricula_historial (numero_empleado, id DESC)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_historial_matricula_id ON matricula_historial (matricula_id)'
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS historial_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_tipo TEXT NOT NULL,
                usuario_id TEXT NOT NULL,
                mensaje_usuario TEXT NOT NULL,
                respuesta_modelo TEXT NOT NULL,
                fecha_evento DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_historial_chat_usuario
            ON historial_chat (usuario_tipo, usuario_id, id DESC)
            '''
        )

        estados_catalogo = [
            ('PENDIENTE', 'Pendiente', 'pendientes', 10),
            ('APROBADA', 'Aprobada', 'aprobadas', 20),
            ('NO_APROBADA', 'No aprobada', 'no_aprobadas', 30),
            ('ABANDONO', 'Abandonó', 'no_aprobadas', 40),
            ('CANCELADA', 'Cancelada', 'canceladas', 50),
        ]
        for estado in estados_catalogo:
            cursor.execute(
                '''
                INSERT OR IGNORE INTO estado_matricula_catalogo (codigo, nombre, categoria, orden)
                VALUES (?, ?, ?, ?)
                ''',
                estado,
            )

        matriculas_sin_historial = cursor.execute(
            '''
            SELECT m.id, m.numero_empleado, m.id_capacitacion, m.horario_elegido, m.aprobado, c.nombre
            FROM matriculas m
            JOIN capacitaciones c ON c.id = m.id_capacitacion
            WHERE NOT EXISTS (
                SELECT 1
                FROM matricula_historial h
                WHERE h.matricula_id = m.id
            )
            '''
        ).fetchall()
        for fila in matriculas_sin_historial:
            valor_aprobado = fila[4]
            if valor_aprobado == 1:
                estado_codigo = 'APROBADA'
            elif valor_aprobado == 0:
                estado_codigo = 'NO_APROBADA'
            elif valor_aprobado == 2:
                estado_codigo = 'ABANDONO'
            else:
                estado_codigo = 'PENDIENTE'

            cursor.execute(
                '''
                INSERT INTO matricula_historial (
                    matricula_id, numero_empleado, id_capacitacion, nombre_curso,
                    horario_elegido, estado_codigo, detalle
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    fila[0], fila[1], fila[2], fila[5], fila[3], estado_codigo,
                    'Sincronizado desde matrículas existentes'
                )
            )

        superadmin_username = os.environ.get('SUPERADMIN_USERNAME', 'admin').strip() or 'admin'
        superadmin_password = os.environ.get(
            'SUPERADMIN_PASSWORD',
            os.environ.get('ADMIN_PASSWORD', 'IPSD@admin2026')
        )

        existe_superadmin = cursor.execute(
            'SELECT id FROM admin_users WHERE username = ?',
            (superadmin_username,)
        ).fetchone()

        if existe_superadmin:
            cursor.execute(
                'UPDATE admin_users SET rol = ?, direccion = ? WHERE username = ?',
                ('superadmin', 'GLOBAL', superadmin_username)
            )
        else:
            cursor.execute(
                'INSERT INTO admin_users (username, password_hash, rol, direccion) VALUES (?, ?, ?, ?)',
                (superadmin_username, generate_password_hash(superadmin_password), 'superadmin', 'GLOBAL')
            )

        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass
