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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plantillas_certificados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direccion_codigo TEXT NOT NULL,
            nombre_plantilla TEXT NOT NULL, 
            tipo_documento TEXT NOT NULL CHECK(tipo_documento IN ('DIPLOMA', 'CONSTANCIA')),
            ruta_fondo_img TEXT NOT NULL, 
            firmante_nombre TEXT NOT NULL, 
            firmante_cargo TEXT NOT NULL, 
            activo INTEGER DEFAULT 1,
            FOREIGN KEY(direccion_codigo) REFERENCES direcciones(codigo)
        )
    ''')

    # Agregamos las 3 columnas nuevas: anio, trimestre, mes, y el id_plantilla_certificado
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
            enlace_virtual TEXT,
            duracion_tipo TEXT NOT NULL DEFAULT 'un_dia',
            tipo_accion TEXT NOT NULL DEFAULT 'CURSO',
            horas_totales INTEGER NOT NULL DEFAULT 20,
            semanas_duracion INTEGER NOT NULL DEFAULT 1,
            id_plantilla_certificado INTEGER REFERENCES plantillas_certificados(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipo_accion_formativa (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            horas_minimas INTEGER NOT NULL,
            horas_maximas INTEGER,
            semanas_minimas INTEGER NOT NULL,
            semanas_maximas INTEGER
        )
    ''')
    cursor.executemany(
        '''
        INSERT OR IGNORE INTO tipo_accion_formativa
        (codigo, nombre, horas_minimas, horas_maximas, semanas_minimas, semanas_maximas)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        [
            ('CONFERENCIA', 'Conferencia', 1, 16, 1, 4),
            ('SEMINARIO', 'Seminario', 16, 120, 1, 16),
            ('CURSO', 'Curso', 20, 240, 1, 52),
        ]
    )

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
        CREATE TABLE IF NOT EXISTS sesiones_curso (
            id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
            id_curso TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            jornada TEXT NOT NULL DEFAULT 'UNICA',
            docente_sesion TEXT,
            edicion TEXT,
            estado INTEGER NOT NULL DEFAULT 0,
            token_asistencia TEXT,
            FOREIGN KEY (id_curso) REFERENCES capacitaciones (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sesiones_curso_fecha ON sesiones_curso (id_curso, fecha, hora_inicio)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sesiones_curso_edicion ON sesiones_curso (id_curso, edicion)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registro_asistencia (
            id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
            id_sesion INTEGER NOT NULL,
            numero_empleado TEXT NOT NULL,
            fecha_marcado TEXT NOT NULL,
            hora_marcado TEXT NOT NULL,
            FOREIGN KEY (id_sesion) REFERENCES sesiones_curso (id_sesion) ON DELETE CASCADE,
            FOREIGN KEY (numero_empleado) REFERENCES docentes (numero_empleado),
            UNIQUE (id_sesion, numero_empleado)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_registro_asistencia_sesion ON registro_asistencia (id_sesion)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_registro_asistencia_empleado ON registro_asistencia (numero_empleado)')

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