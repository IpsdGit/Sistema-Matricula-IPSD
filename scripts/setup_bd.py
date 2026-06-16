import os
import psycopg2
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def get_db_connection():
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:Postgre202625@localhost:5434/sistema_unah')
    #database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:PGS2025.@localhost:5435/sistema_unah')
    return psycopg2.connect(database_url)

def inicializar_bd():
    conexion = get_db_connection()
    cursor = conexion.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS direcciones (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            ruta_firma_img TEXT NOT NULL DEFAULT '',
            ruta_logo_img TEXT NOT NULL DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS docentes (
            id SERIAL PRIMARY KEY,
            numero_empleado TEXT UNIQUE NOT NULL,
            nombre_completo TEXT NOT NULL,
            correo_institucional TEXT UNIQUE NOT NULL,
            facultad TEXT NOT NULL DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_sincronizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            centro_universitario_regional TEXT NOT NULL DEFAULT ''
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_docentes_numero ON docentes (numero_empleado)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_docentes_correo ON docentes (correo_institucional)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plantillas_certificados (
            id SERIAL PRIMARY KEY,
            direccion_codigo TEXT NOT NULL,
            nombre_plantilla TEXT NOT NULL, 
            tipo_documento TEXT NOT NULL CHECK(tipo_documento IN ('DIPLOMA', 'CONSTANCIA')),
            ruta_firma_img TEXT NOT NULL DEFAULT '',
            texto_certificado TEXT NOT NULL,
            firmante_nombre TEXT NOT NULL, 
            firmante_cargo TEXT NOT NULL, 
            activo INTEGER DEFAULT 1,
            FOREIGN KEY(direccion_codigo) REFERENCES direcciones(codigo)
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

    # Catalogo de acciones formativas (molde)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS catalogo_acciones (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            modalidad TEXT,
            tipo_accion TEXT,
            id_plantilla_certificado INTEGER,
            direccion_codigo TEXT,
            FOREIGN KEY (id_plantilla_certificado) REFERENCES plantillas_certificados (id),
            FOREIGN KEY (direccion_codigo) REFERENCES direcciones (codigo),
            FOREIGN KEY (tipo_accion) REFERENCES tipo_accion_formativa (codigo)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_catalogo_acciones_direccion ON catalogo_acciones (direccion_codigo)')

    # Ediciones formativas (ejecucion/jornada)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ediciones_formativas (
            id TEXT PRIMARY KEY,
            catalogo_id TEXT,
            etiqueta_edicion TEXT DEFAULT '',
            calendario_academico TEXT,
            periodo TEXT,
            fecha_inicio DATE,
            fecha_limite_matricula TIMESTAMP,
            jornada TEXT,
            hora TEXT,
            cupos_maximos INTEGER,
            enlace_acceso TEXT,
            docente_responsable TEXT,
            persona_apoyo TEXT,
            requisitos TEXT,
            duracion_horas INTEGER,       
            privacidad TEXT DEFAULT 'Abierta',
            estado TEXT DEFAULT 'En Edicion',
            mensaje_bienvenida TEXT DEFAULT '',
            FOREIGN KEY (catalogo_id) REFERENCES catalogo_acciones (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ediciones_catalogo ON ediciones_formativas (catalogo_id)')

    cursor.executemany(
        '''
        INSERT INTO tipo_accion_formativa
        (codigo, nombre, horas_minimas, horas_maximas, semanas_minimas, semanas_maximas)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (codigo) DO NOTHING
        ''',
        [
            ('CONFERENCIA', 'Conferencia', 1, 16, 1, 4),
            ('SEMINARIO', 'Seminario', 16, 120, 1, 16),
            ('SEMINARIO-TALLER', 'Seminario-Taller', 16, 100, 1, 8),
            ('CURSO', 'Curso', 20, 240, 1, 52),
            
        ]
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matriculas (
            id SERIAL PRIMARY KEY,
            numero_empleado TEXT NOT NULL,
            edicion_id TEXT NOT NULL,
            fecha_matricula TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aprobado INTEGER,
            fecha_aprobacion TEXT,
            comentario_validacion TEXT,
            FOREIGN KEY (edicion_id) REFERENCES ediciones_formativas (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matriculas_edicion ON matriculas (edicion_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matriculas_numero ON matriculas (numero_empleado)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matriculas_edicion_empleado ON matriculas (edicion_id, numero_empleado)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensajes_personalizados (
            id SERIAL PRIMARY KEY,
            numero_empleado TEXT NOT NULL,
            asunto TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            leido BOOLEAN DEFAULT FALSE,
            FOREIGN KEY(numero_empleado) REFERENCES docentes(numero_empleado) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mensajes_docente ON mensajes_personalizados (numero_empleado)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sesiones_curso (
            id_sesion SERIAL PRIMARY KEY,
            edicion_id TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            estado INTEGER NOT NULL DEFAULT 0,
            token_asistencia TEXT,
            FOREIGN KEY (edicion_id) REFERENCES ediciones_formativas (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sesiones_curso_edicion ON sesiones_curso (edicion_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sesiones_curso_fecha ON sesiones_curso (edicion_id, fecha, hora_inicio)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registro_asistencia (
            id_registro SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            matricula_id INTEGER,
            numero_empleado TEXT NOT NULL,
            edicion_id TEXT NOT NULL,
            nombre_accion TEXT NOT NULL,
            estado_codigo TEXT NOT NULL,
            detalle TEXT,
            fecha_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estado_codigo) REFERENCES estado_matricula_catalogo (codigo),
            FOREIGN KEY (edicion_id) REFERENCES ediciones_formativas (id)
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
        INSERT INTO estado_matricula_catalogo (codigo, nombre, categoria, orden)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (codigo) DO NOTHING
        ''',
        estados_catalogo
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificados_emitidos (
            id SERIAL PRIMARY KEY,
            token_validacion TEXT UNIQUE NOT NULL,
            matricula_id INTEGER NOT NULL,
            numero_empleado TEXT NOT NULL,
            edicion_id TEXT NOT NULL,
            fecha_emision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo_documento TEXT NOT NULL,
            veces_validado INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(matricula_id) REFERENCES matriculas(id),
            FOREIGN KEY(numero_empleado) REFERENCES docentes(numero_empleado),
            FOREIGN KEY(edicion_id) REFERENCES ediciones_formativas(id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cert_token ON certificados_emitidos (token_validacion)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_chat (
            id SERIAL PRIMARY KEY,
            usuario_tipo TEXT NOT NULL,
            usuario_id TEXT NOT NULL,
            mensaje_usuario TEXT NOT NULL,
            respuesta_modelo TEXT NOT NULL,
            fecha_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'admin',
            direccion TEXT NOT NULL DEFAULT 'IPSD'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reportes_generados (
            id SERIAL PRIMARY KEY,
            titulo_reporte TEXT NOT NULL,
            admin_id INTEGER,
            fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            parametros_extraccion JSONB,
            formato TEXT NOT NULL,
            total_registros_extraidos INTEGER NOT NULL,
            ruta_archivo TEXT NOT NULL,
            FOREIGN KEY (admin_id) REFERENCES admin_users (id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ediciones_invitaciones (
            id SERIAL PRIMARY KEY,
            edicion_id TEXT NOT NULL,
            numero_empleado TEXT NOT NULL,
            fecha_invitacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(edicion_id) REFERENCES ediciones_formativas(id) ON DELETE CASCADE,
            FOREIGN KEY(numero_empleado) REFERENCES docentes(numero_empleado) ON DELETE CASCADE,
            UNIQUE (edicion_id, numero_empleado)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invitaciones_empleado ON ediciones_invitaciones (numero_empleado)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invitaciones_edicion ON ediciones_invitaciones (edicion_id)')

    superadmin_username = os.environ.get('SUPERADMIN_USERNAME', 'admin').strip() or 'admin'
    superadmin_password = os.environ.get(
        'SUPERADMIN_PASSWORD',
        os.environ.get('ADMIN_PASSWORD', 'IPSD@admin2026')
    )

    cursor.execute(
        'SELECT 1 FROM admin_users WHERE username = %s',
        (superadmin_username,)
    )
    existe_superadmin = cursor.fetchone()

    if not existe_superadmin:
        cursor.execute(
            'INSERT INTO admin_users (username, password_hash, rol, direccion) VALUES (%s, %s, %s, %s)',
            (superadmin_username, generate_password_hash(superadmin_password), 'superadmin', 'GLOBAL')
        )

    # === MIGRACIONES AUTOMÁTICAS (Para actualizar tablas existentes) ===
    # Si las tablas ya existían antes, estas líneas inyectarán los nuevos campos sin borrar tus datos.
    cursor.execute("ALTER TABLE docentes ADD COLUMN IF NOT EXISTS facultad TEXT NOT NULL DEFAULT '';")
    cursor.execute("ALTER TABLE ediciones_formativas ADD COLUMN IF NOT EXISTS calendario_academico TEXT;")
    cursor.execute("ALTER TABLE ediciones_formativas ADD COLUMN IF NOT EXISTS periodo TEXT;")
    cursor.execute("ALTER TABLE ediciones_formativas DROP COLUMN IF EXISTS trimestre;")
 
    conexion.commit()
    conexion.close()
    print("¡Base de datos lista y actualizada con las nuevas estructuras de Reportes!")

if __name__ == '__main__':
    inicializar_bd()