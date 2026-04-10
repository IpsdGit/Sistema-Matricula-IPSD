import sqlite3
import os
from werkzeug.security import generate_password_hash


def resolver_db_path():
    env_db_path = os.environ.get('DATABASE_PATH')
    if env_db_path:
        return env_db_path

    project_root = os.path.dirname(os.path.dirname(__file__))
    local_db = os.path.join(project_root, 'matricula.db')
    pythonanywhere_db = '/home/IPSDUNAH/mysite/matricula.db'

    if os.path.exists(local_db):
        return local_db
    if os.path.exists(pythonanywhere_db):
        return pythonanywhere_db
    return local_db


DB_PATH = resolver_db_path()

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

def inicializar_bd():
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    # Agregamos las 3 columnas nuevas: anio, trimestre, mes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS capacitaciones (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            anio TEXT NOT NULL,
            trimestre TEXT NOT NULL,
            mes TEXT NOT NULL,
            dia TEXT NOT NULL DEFAULT '1',
            modalidad TEXT NOT NULL DEFAULT 'Virtual',
            cupos_maximos INTEGER NOT NULL DEFAULT 0,
            enlace_virtual TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS horarios_curso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_capacitacion TEXT NOT NULL,
            horario TEXT NOT NULL,
            FOREIGN KEY (id_capacitacion) REFERENCES capacitaciones (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matriculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_empleado TEXT NOT NULL,
            id_capacitacion TEXT NOT NULL,
            horario_elegido TEXT NOT NULL,
            fecha_matricula DATETIME DEFAULT CURRENT_TIMESTAMP,
            aprobado INTEGER,
            FOREIGN KEY (id_capacitacion) REFERENCES capacitaciones (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estado_matricula_catalogo (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            orden INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
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
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_historial_empleado_fecha ON matricula_historial (numero_empleado, id DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_historial_matricula_id ON matricula_historial (matricula_id)')

    estados_catalogo = [
        ('PENDIENTE', 'Pendiente', 'pendientes', 10),
        ('APROBADA', 'Aprobada', 'aprobadas', 20),
        ('NO_APROBADA', 'No aprobada', 'no_aprobadas', 30),
        ('ABANDONO', 'Abandonó', 'no_aprobadas', 40),
        ('CANCELADA', 'Cancelada', 'canceladas', 50),
    ]
    cursor.executemany(
        '''
        INSERT OR IGNORE INTO estado_matricula_catalogo (codigo, nombre, categoria, orden)
        VALUES (?, ?, ?, ?)
        ''',
        estados_catalogo
    )

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

    superadmin_username = os.environ.get('SUPERADMIN_USERNAME', 'admin').strip() or 'admin'
    superadmin_password = os.environ.get(
        'SUPERADMIN_PASSWORD',
        os.environ.get('ADMIN_PASSWORD', 'IPSD@admin2026')
    )

    existe_superadmin = cursor.execute(
        'SELECT 1 FROM admin_users WHERE username = ?',
        (superadmin_username,)
    ).fetchone()

    if not existe_superadmin:
        cursor.execute(
            'INSERT INTO admin_users (username, password_hash, rol, direccion) VALUES (?, ?, ?, ?)',
            (superadmin_username, generate_password_hash(superadmin_password), 'superadmin', 'GLOBAL')
        )

    conexion.commit()
    conexion.close()
    print("¡Base de datos lista con soporte de roles de administración!")

if __name__ == '__main__':
    inicializar_bd()