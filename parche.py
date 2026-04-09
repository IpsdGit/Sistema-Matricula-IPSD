import os
import sqlite3
from werkzeug.security import generate_password_hash

def aplicar_parche():
    # Obtener ruta de BD del entorno, con fallback local/PythonAnywhere
    env_db_path = os.environ.get('DATABASE_PATH')

    if env_db_path:
        db_path = env_db_path
    else:
        base_dir = os.path.dirname(__file__)
        local_db = os.path.join(base_dir, 'matricula.db')
        pythonanywhere_db = '/home/IPSDUNAH/mysite/matricula.db'

        if os.path.exists(local_db):
            db_path = local_db
        elif os.path.exists(pythonanywhere_db):
            db_path = pythonanywhere_db
        else:
            db_path = local_db
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Iniciando actualización silenciosa...")

    # 1. Agregar fecha a las matrículas
    try:
        cursor.execute('ALTER TABLE matriculas ADD COLUMN fecha_matricula DATETIME DEFAULT CURRENT_TIMESTAMP')
        print("✓ Columna de fecha agregada.")
    except Exception as e:
        print("- La columna de fecha ya estaba lista.")

    # 2. Crear tabla de administradores segura
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'admin',
            direccion TEXT NOT NULL DEFAULT 'IPSD'
        )
    ''')
    print("✓ Tabla de seguridad creada.")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS direcciones (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL
        )
    ''')
    print("✓ Catálogo de direcciones preparado.")

    # 2.1 Agregar columnas de control de acceso en administradores (si no existen)
    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN rol TEXT NOT NULL DEFAULT 'admin'")
        print("✓ Columna 'rol' agregada en admin_users.")
    except Exception:
        print("- La columna 'rol' ya estaba lista.")

    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN direccion TEXT NOT NULL DEFAULT 'IPSD'")
        print("✓ Columna 'direccion' agregada en admin_users.")
    except Exception:
        print("- La columna 'direccion' ya estaba lista.")

    # 2.1 Agregar nuevas columnas en capacitaciones (si no existen)
    try:
        cursor.execute("ALTER TABLE capacitaciones ADD COLUMN dia TEXT NOT NULL DEFAULT '1'")
        print("✓ Columna 'dia' agregada en capacitaciones.")
    except Exception:
        print("- La columna 'dia' ya estaba lista.")

    try:
        cursor.execute("ALTER TABLE capacitaciones ADD COLUMN modalidad TEXT NOT NULL DEFAULT 'Virtual'")
        print("✓ Columna 'modalidad' agregada en capacitaciones.")
    except Exception:
        print("- La columna 'modalidad' ya estaba lista.")

    try:
        cursor.execute("ALTER TABLE capacitaciones ADD COLUMN cupos_maximos INTEGER NOT NULL DEFAULT 0")
        print("✓ Columna 'cupos_maximos' agregada en capacitaciones.")
    except Exception:
        print("- La columna 'cupos_maximos' ya estaba lista.")

    # 3. Crear/asegurar superadmin desde variable de entorno
    try:
        superadmin_username = os.environ.get('SUPERADMIN_USERNAME', 'admin').strip() or 'admin'
        superadmin_password = os.environ.get(
            'SUPERADMIN_PASSWORD',
            os.environ.get('ADMIN_PASSWORD', 'IPSD@admin2026')
        )

        superadmin = cursor.execute(
            'SELECT id FROM admin_users WHERE username = ?',
            (superadmin_username,)
        ).fetchone()

        if superadmin:
            cursor.execute(
                'UPDATE admin_users SET rol = ?, direccion = ? WHERE username = ?',
                ('superadmin', 'GLOBAL', superadmin_username)
            )
            print(f"✓ Usuario '{superadmin_username}' actualizado como superadmin.")
        else:
            clave = generate_password_hash(superadmin_password)
            cursor.execute(
                'INSERT INTO admin_users (username, password_hash, rol, direccion) VALUES (?, ?, ?, ?)',
                (superadmin_username, clave, 'superadmin', 'GLOBAL')
            )
            print(f"✓ Superadmin '{superadmin_username}' configurado con éxito.")
    except sqlite3.IntegrityError:
        print("- El superadmin ya existía.")

    # 4. Asegurar que no existan roles vacíos
    cursor.execute("UPDATE admin_users SET rol = 'admin' WHERE rol IS NULL OR TRIM(rol) = ''")
    cursor.execute("UPDATE admin_users SET direccion = 'IPSD' WHERE direccion IS NULL OR TRIM(direccion) = ''")

    conn.commit()
    conn.close()
    print("¡PARCHE COMPLETADO EXITOSAMENTE!")

if __name__ == '__main__':
    aplicar_parche()