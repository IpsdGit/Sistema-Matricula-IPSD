import sqlite3
import os
from werkzeug.security import generate_password_hash

if os.path.exists('matricula.db'):
    os.remove('matricula.db')

def inicializar_bd():
    conexion = sqlite3.connect('matricula.db')
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
            cupos_maximos INTEGER NOT NULL DEFAULT 0
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
            FOREIGN KEY (id_capacitacion) REFERENCES capacitaciones (id) ON DELETE CASCADE
        )
    ''')

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