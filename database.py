import os
import re
import psycopg2
import psycopg2.extras
import psycopg2.pool
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

_pool = None

class PooledConnectionWrapper:
    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn

    def close(self):
        if self._pool is not None and self._conn is not None:
            try:
                self._conn.rollback()
            except Exception:
                pass
            self._pool.putconn(self._conn)
            self._conn = None

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._conn.__exit__(exc_type, exc_val, exc_tb)

def get_db_connection():
    global _pool
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:Postgre202625@localhost:5434/sistema_unah')
    #database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:PGS2025.@localhost:5435/sistema_unah')
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=database_url,
            cursor_factory=psycopg2.extras.DictCursor
        )
    conn = _pool.getconn()
    return PooledConnectionWrapper(_pool, conn)

def asegurar_migraciones_minimas():
    """Evita fallos en despliegues donde aún no se ha corrido setup_bd.py."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Bloqueo consultivo a nivel de transacción para evitar deadlocks con gunicorn (múltiples workers)
        cursor.execute("SELECT pg_advisory_xact_lock(1001)")

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
            CREATE TABLE IF NOT EXISTS direcciones (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                ruta_firma_img TEXT NOT NULL DEFAULT '',
                ruta_logo_img TEXT NOT NULL DEFAULT ''
            )
        ''')

        cursor.execute(
            '''
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
            '''
        )

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'direcciones'")
        columnas_direcciones = {row['column_name'] for row in cursor.fetchall()}
        if 'ruta_firma_img' not in columnas_direcciones:
            cursor.execute("ALTER TABLE direcciones ADD COLUMN ruta_firma_img TEXT NOT NULL DEFAULT ''")
        if 'ruta_logo_img' not in columnas_direcciones:
            cursor.execute("ALTER TABLE direcciones ADD COLUMN ruta_logo_img TEXT NOT NULL DEFAULT ''")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'plantillas_certificados'")
        columnas_plantillas = {row['column_name'] for row in cursor.fetchall()}
        if 'ruta_firma_img' not in columnas_plantillas:
            cursor.execute("ALTER TABLE plantillas_certificados ADD COLUMN ruta_firma_img TEXT NOT NULL DEFAULT ''")
        if 'texto_certificado' not in columnas_plantillas:
            cursor.execute("ALTER TABLE plantillas_certificados ADD COLUMN texto_certificado TEXT NOT NULL DEFAULT ''")

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS docentes (
                id SERIAL PRIMARY KEY,
                numero_empleado TEXT UNIQUE NOT NULL,
                nombre_completo TEXT NOT NULL,
                correo_institucional TEXT UNIQUE NOT NULL,
                centro_universitario_regional TEXT NOT NULL DEFAULT '',
                activo INTEGER NOT NULL DEFAULT 1,
                fecha_sincronizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_docentes_numero ON docentes (numero_empleado)')
        # En Postgres no hay COLLATE NOCASE fácil así, preferimos índice o lower()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_docentes_correo ON docentes (correo_institucional)')

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'docentes'")
        columnas_docentes = {row['column_name'] for row in cursor.fetchall()}
        if 'centro_universitario_regional' not in columnas_docentes:
            cursor.execute("ALTER TABLE docentes ADD COLUMN centro_universitario_regional TEXT NOT NULL DEFAULT ''")
        if 'notificaciones_leidas' not in columnas_docentes:
            cursor.execute("ALTER TABLE docentes ADD COLUMN notificaciones_leidas TEXT NOT NULL DEFAULT '[]'")
        if 'facultad' not in columnas_docentes:
            cursor.execute("ALTER TABLE docentes ADD COLUMN facultad TEXT NOT NULL DEFAULT ''")

        cursor.execute('''
            SELECT DISTINCT direccion
            FROM admin_users
            WHERE rol = 'admin' AND direccion IS NOT NULL AND TRIM(direccion) <> ''
        ''')
        direcciones_admin = cursor.fetchall()
        for row in direcciones_admin:
            codigo_dir = (row['direccion'] or '').strip().upper().replace(' ', '')
            if codigo_dir and codigo_dir != 'GLOBAL':
                if not re.match(r'^[A-Z0-9]{2,12}$', codigo_dir):
                    continue
                cursor.execute(
                    'INSERT INTO direcciones (codigo, nombre) VALUES (%s, %s) ON CONFLICT (codigo) DO NOTHING',
                    (codigo_dir, codigo_dir)
                )

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'admin_users'")
        columnas_admin = {row['column_name'] for row in cursor.fetchall()}
        if 'rol' not in columnas_admin:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN rol TEXT NOT NULL DEFAULT 'admin'")
        if 'direccion' not in columnas_admin:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN direccion TEXT NOT NULL DEFAULT 'IPSD'")

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS tipo_accion_formativa (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                horas_minimas INTEGER NOT NULL,
                horas_maximas INTEGER,
                semanas_minimas INTEGER NOT NULL,
                semanas_maximas INTEGER
            )
            '''
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS catalogo_acciones (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                modalidad TEXT,
                tipo_accion TEXT,
                id_plantilla_certificado INTEGER,
                direccion_codigo TEXT,
                requisitos TEXT DEFAULT '',
                FOREIGN KEY (id_plantilla_certificado) REFERENCES plantillas_certificados (id),
                FOREIGN KEY (direccion_codigo) REFERENCES direcciones (codigo),
                FOREIGN KEY (tipo_accion) REFERENCES tipo_accion_formativa (codigo)
            )
            '''
        )

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'catalogo_acciones'")
        columnas_catalogo = {row['column_name'] for row in cursor.fetchall()}
        if 'requisitos' not in columnas_catalogo:
            cursor.execute("ALTER TABLE catalogo_acciones ADD COLUMN requisitos TEXT DEFAULT ''")

        cursor.execute(
            '''
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
                privacidad TEXT DEFAULT 'Abierta',
                estado TEXT DEFAULT 'En Edicion',
                FOREIGN KEY (catalogo_id) REFERENCES catalogo_acciones (id) ON DELETE CASCADE
            )
            '''
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ediciones_catalogo ON ediciones_formativas (catalogo_id)')

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'ediciones_formativas'")
        columnas_ediciones = {row['column_name'] for row in cursor.fetchall()}
        if 'etiqueta_edicion' not in columnas_ediciones:
            cursor.execute("ALTER TABLE ediciones_formativas ADD COLUMN etiqueta_edicion TEXT DEFAULT ''")
        if 'requisitos' not in columnas_ediciones:
            cursor.execute("ALTER TABLE ediciones_formativas ADD COLUMN requisitos TEXT DEFAULT ''")
        if 'duracion_horas' not in columnas_ediciones:
            cursor.execute('ALTER TABLE ediciones_formativas ADD COLUMN duracion_horas INTEGER')
        if 'persona_apoyo' not in columnas_ediciones:
            cursor.execute('ALTER TABLE ediciones_formativas ADD COLUMN persona_apoyo TEXT')
        if 'calendario_academico' not in columnas_ediciones:
            cursor.execute('ALTER TABLE ediciones_formativas ADD COLUMN calendario_academico TEXT')
        if 'periodo' not in columnas_ediciones:
            cursor.execute('ALTER TABLE ediciones_formativas ADD COLUMN periodo TEXT')
        if 'trimestre' in columnas_ediciones:
            cursor.execute('ALTER TABLE ediciones_formativas DROP COLUMN trimestre')

        cursor.execute("UPDATE ediciones_formativas SET estado = 'Programado' WHERE estado = 'Programada'")

        extras = [
            ('CONFERENCIA', 'Conferencia', 1, 16, 1, 4),
            ('SEMINARIO', 'Seminario', 16, 120, 1, 16),
            ('CURSO', 'Curso', 20, 240, 1, 52),
        ]
        for extra in extras:
            cursor.execute(
                '''
                INSERT INTO tipo_accion_formativa
                (codigo, nombre, horas_minimas, horas_maximas, semanas_minimas, semanas_maximas)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (codigo) DO NOTHING
                ''',
                extra
            )

        cursor.execute(
            '''
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
            '''
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_matriculas_numero_empleado ON matriculas (numero_empleado)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_matriculas_edicion_id ON matriculas (edicion_id)')

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'matriculas'")
        columnas_matriculas = {row['column_name'] for row in cursor.fetchall()}
        if 'edicion_id' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN edicion_id TEXT')
        if 'fecha_matricula' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN fecha_matricula TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        if 'aprobado' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN aprobado INTEGER')
        if 'fecha_aprobacion' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN fecha_aprobacion TEXT')
        if 'comentario_validacion' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN comentario_validacion TEXT')

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
            '''
        )

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historial_empleado_fecha ON matricula_historial (numero_empleado, id DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historial_matricula_id ON matricula_historial (matricula_id)')

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS historial_chat (
                id SERIAL PRIMARY KEY,
                usuario_tipo TEXT NOT NULL,
                usuario_id TEXT NOT NULL,
                mensaje_usuario TEXT NOT NULL,
                respuesta_modelo TEXT NOT NULL,
                fecha_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )

        cursor.execute(
            '''
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
            '''
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sesiones_curso_fecha ON sesiones_curso (edicion_id, fecha, hora_inicio)')

        cursor.execute(
            '''
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
            '''
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_registro_asistencia_sesion ON registro_asistencia (id_sesion)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_registro_asistencia_empleado ON registro_asistencia (numero_empleado)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historial_chat_usuario ON historial_chat (usuario_tipo, usuario_id, id DESC)')

        # ── Migraciones: clicks_asistencia (CONFERENCIA) ────────────────────────
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'sesiones_curso'")
        columnas_sesiones = {row['column_name'] for row in cursor.fetchall()}
        if 'ventanas_atencion' not in columnas_sesiones:
            cursor.execute("ALTER TABLE sesiones_curso ADD COLUMN ventanas_atencion JSONB")
        if 'ventana_forzada_expira' not in columnas_sesiones:
            cursor.execute("ALTER TABLE sesiones_curso ADD COLUMN ventana_forzada_expira TIMESTAMP")
        if 'ventana_forzada_idx' not in columnas_sesiones:
            cursor.execute("ALTER TABLE sesiones_curso ADD COLUMN ventana_forzada_idx INTEGER")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'registro_asistencia'")
        columnas_registro = {row['column_name'] for row in cursor.fetchall()}
        if 'tipo_registro' not in columnas_registro:
            cursor.execute("ALTER TABLE registro_asistencia ADD COLUMN tipo_registro TEXT NOT NULL DEFAULT 'QR'")
        if 'ventanas_completadas' not in columnas_registro:
            cursor.execute("ALTER TABLE registro_asistencia ADD COLUMN ventanas_completadas JSONB NOT NULL DEFAULT '[]'")
        if 'aprobado_automatico' not in columnas_registro:
            cursor.execute("ALTER TABLE registro_asistencia ADD COLUMN aprobado_automatico BOOLEAN NOT NULL DEFAULT FALSE")


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
                INSERT INTO estado_matricula_catalogo (codigo, nombre, categoria, orden)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo) DO NOTHING
                ''',
                estado,
            )

        cursor.execute(
            '''
            SELECT m.id, m.numero_empleado, m.edicion_id, m.aprobado, ca.nombre
            FROM matriculas m
            JOIN ediciones_formativas e ON e.id = m.edicion_id
            JOIN catalogo_acciones ca ON ca.id = e.catalogo_id
            WHERE NOT EXISTS (
                SELECT 1 FROM matricula_historial h WHERE h.matricula_id = m.id
            )
            '''
        )
        matriculas_sin_historial = cursor.fetchall()
        for fila in matriculas_sin_historial:
            valor_aprobado = fila['aprobado']
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
                    matricula_id, numero_empleado, edicion_id, nombre_accion,
                    estado_codigo, detalle
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    fila['id'], fila['numero_empleado'], fila['edicion_id'], fila['nombre'], estado_codigo,
                    'Sincronizado desde matrículas existentes'
                )
            )

        superadmin_username = os.environ.get('SUPERADMIN_USERNAME', 'admin').strip() or 'admin'
        superadmin_password = os.environ.get('SUPERADMIN_PASSWORD', os.environ.get('ADMIN_PASSWORD', 'IPSD@admin2026'))

        cursor.execute('SELECT id FROM admin_users WHERE username = %s', (superadmin_username,))
        existe_superadmin = cursor.fetchone()

        if existe_superadmin:
            cursor.execute(
                'UPDATE admin_users SET rol = %s, direccion = %s WHERE username = %s',
                ('superadmin', 'GLOBAL', superadmin_username)
            )
        else:
            cursor.execute(
                'INSERT INTO admin_users (username, password_hash, rol, direccion) VALUES (%s, %s, %s, %s)',
                (superadmin_username, generate_password_hash(superadmin_password), 'superadmin', 'GLOBAL')
            )

        cursor.execute(
            '''
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
            '''
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cert_token ON certificados_emitidos (token_validacion)')

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS ediciones_invitaciones (
                id SERIAL PRIMARY KEY,
                edicion_id TEXT NOT NULL,
                numero_empleado TEXT NOT NULL,
                fecha_invitacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(edicion_id) REFERENCES ediciones_formativas(id) ON DELETE CASCADE,
                FOREIGN KEY(numero_empleado) REFERENCES docentes(numero_empleado) ON DELETE CASCADE,
                UNIQUE (edicion_id, numero_empleado)
            )
            '''
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_invitaciones_empleado ON ediciones_invitaciones (numero_empleado)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_invitaciones_edicion ON ediciones_invitaciones (edicion_id)')

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

        conn.commit()
    except Exception as e:
        print(f"Error asegurando migraciones: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
        pass
