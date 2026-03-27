import os
import sqlite3
from werkzeug.security import generate_password_hash

def aplicar_parche():
    # Obtener ruta de BD del entorno, con fallback para PythonAnywhere
    db_path = os.environ.get(
        'DATABASE_PATH',
        '/home/IPSDUNAH/mysite/matricula.db'
    )
    
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
            password_hash TEXT NOT NULL
        )
    ''')
    print("✓ Tabla de seguridad creada.")

    # 3. Crear usuario administrador desde variable de entorno
    try:
        # Obtener contraseña del entorno, con valor por defecto para pruebas locales
        admin_password = os.environ.get(
            'ADMIN_PASSWORD',
            'IPSD@admin2026'  # ⚠️ CAMBIAR esta contraseña en producción
        )
        
        clave = generate_password_hash(admin_password)
        cursor.execute('INSERT INTO admin_users (username, password_hash) VALUES (?, ?)', ('admin', clave))
        print("✓ Usuario 'admin' configurado con éxito.")
    except sqlite3.IntegrityError:
        print("- El usuario 'admin' ya existía.")

    conn.commit()
    conn.close()
    print("¡PARCHE COMPLETADO EXITOSAMENTE!")

if __name__ == '__main__':
    aplicar_parche()