import os
import sqlite3
from werkzeug.security import generate_password_hash

def aplicar_parche():
    # Obtener ruta de BD del entorno, con fallback local/PythonAnywhere
    env_db_path = os.environ.get('DATABASE_PATH')

    if env_db_path:
        db_path = env_db_path
    else:
        project_root = os.path.dirname(os.path.dirname(__file__))
        local_db = os.path.join(project_root, 'matricula.db')
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

    try:
        cursor.execute('ALTER TABLE matriculas ADD COLUMN aprobado INTEGER')
        print("✓ Columna 'aprobado' agregada en matriculas.")
    except Exception:
        print("- La columna 'aprobado' ya estaba lista.")

    try:
        cursor.execute('ALTER TABLE matriculas ADD COLUMN fecha_aprobacion TEXT')
        # Backfill
        cursor.execute('''
            UPDATE matriculas 
            SET fecha_aprobacion = (
                SELECT SUBSTR(fecha_evento, 1, 10)
                FROM matricula_historial 
                WHERE matricula_id = matriculas.numero_empleado || '_' || matriculas.id_capacitacion
                AND estado_codigo = 'APROBADO'
                ORDER BY fecha_evento DESC 
                LIMIT 1
            )
            WHERE aprobado = 1 AND fecha_aprobacion IS NULL
        ''')
        print("✓ Columna 'fecha_aprobacion' agregada y backfill completado.")
    except Exception:
        print("- La columna 'fecha_aprobacion' ya estaba lista.")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estado_matricula_catalogo (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            orden INTEGER NOT NULL
        )
    ''')
    print("✓ Catálogo de estados de matrícula preparado.")

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
    print("✓ Historial normalizado de matrículas preparado.")

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS docentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_empleado TEXT UNIQUE NOT NULL,
            nombre_completo TEXT NOT NULL,
            correo_institucional TEXT UNIQUE NOT NULL COLLATE NOCASE,
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_sincronizacion DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_docentes_numero ON docentes (numero_empleado)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_docentes_correo ON docentes (correo_institucional)')
    print("✓ Tabla de docentes preparada.")

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

    try:
        cursor.execute("ALTER TABLE capacitaciones ADD COLUMN enlace_virtual TEXT")
        print("✓ Columna 'enlace_virtual' agregada en capacitaciones.")
    except Exception:
        print("- La columna 'enlace_virtual' ya estaba lista.")

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