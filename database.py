import os
import re
import sqlite3

from werkzeug.security import generate_password_hash

from config import DB_PATH


def get_db_connection():
    # Se aumenta el timeout a 20 segundos y se activa el modo WAL para mejorar la concurrencia
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.row_factory = sqlite3.Row
    return conn


def asegurar_migraciones_minimas():
    """Evita fallos en despliegues donde aún no se ha corrido parche.py."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA foreign_keys = ON')
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
                nombre TEXT NOT NULL,
                ruta_firma_img TEXT NOT NULL DEFAULT '',
                ruta_logo_img TEXT NOT NULL DEFAULT ''
            )
        ''')

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS plantillas_certificados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        columnas_direcciones = {
            row[1] for row in cursor.execute('PRAGMA table_info(direcciones)').fetchall()
        }
        if 'ruta_firma_img' not in columnas_direcciones:
            cursor.execute(
                "ALTER TABLE direcciones ADD COLUMN ruta_firma_img TEXT NOT NULL DEFAULT ''"
            )
        if 'ruta_logo_img' not in columnas_direcciones:
            cursor.execute(
                "ALTER TABLE direcciones ADD COLUMN ruta_logo_img TEXT NOT NULL DEFAULT ''"
            )

        columnas_plantillas = {
            row[1] for row in cursor.execute('PRAGMA table_info(plantillas_certificados)').fetchall()
        }
        if 'ruta_firma_img' not in columnas_plantillas:
            cursor.execute(
                "ALTER TABLE plantillas_certificados ADD COLUMN ruta_firma_img TEXT NOT NULL DEFAULT ''"
            )
        if 'texto_certificado' not in columnas_plantillas:
            cursor.execute(
                "ALTER TABLE plantillas_certificados ADD COLUMN texto_certificado TEXT NOT NULL DEFAULT ''"
            )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS docentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_empleado TEXT UNIQUE NOT NULL,
                nombre_completo TEXT NOT NULL,
                correo_institucional TEXT UNIQUE NOT NULL COLLATE NOCASE,
                centro_universitario_regional TEXT NOT NULL DEFAULT '',
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

        columnas_docentes = {
            row[1] for row in cursor.execute('PRAGMA table_info(docentes)').fetchall()
        }
        if 'centro_universitario_regional' not in columnas_docentes:
            cursor.execute(
                "ALTER TABLE docentes ADD COLUMN centro_universitario_regional TEXT NOT NULL DEFAULT ''"
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

        columnas_admin = {
            row[1] for row in cursor.execute('PRAGMA table_info(admin_users)').fetchall()
        }
        if 'rol' not in columnas_admin:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN rol TEXT NOT NULL DEFAULT 'admin'")
        if 'direccion' not in columnas_admin:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN direccion TEXT NOT NULL DEFAULT 'IPSD'")

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

        columnas_catalogo = {
            row[1] for row in cursor.execute('PRAGMA table_info(catalogo_acciones)').fetchall()
        }
        if 'requisitos' not in columnas_catalogo:
            cursor.execute(
                "ALTER TABLE catalogo_acciones ADD COLUMN requisitos TEXT DEFAULT ''"
            )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS ediciones_formativas (
                id TEXT PRIMARY KEY,
                catalogo_id TEXT,
                etiqueta_edicion TEXT DEFAULT '',
                trimestre TEXT,
                fecha_inicio DATE,
                fecha_limite_matricula DATETIME,
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
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_ediciones_catalogo ON ediciones_formativas (catalogo_id)'
        )

        columnas_ediciones = {
            row[1] for row in cursor.execute('PRAGMA table_info(ediciones_formativas)').fetchall()
        }
        if 'etiqueta_edicion' not in columnas_ediciones:
            cursor.execute(
                "ALTER TABLE ediciones_formativas ADD COLUMN etiqueta_edicion TEXT DEFAULT ''"
            )
        if 'requisitos' not in columnas_ediciones:
            cursor.execute(
                "ALTER TABLE ediciones_formativas ADD COLUMN requisitos TEXT DEFAULT ''"
            )
        if 'duracion_horas' not in columnas_ediciones:
            cursor.execute(
                'ALTER TABLE ediciones_formativas ADD COLUMN duracion_horas INTEGER'
            )
        if 'persona_apoyo' not in columnas_ediciones:
            cursor.execute(
                'ALTER TABLE ediciones_formativas ADD COLUMN persona_apoyo TEXT'
            )

        cursor.execute(
            "UPDATE ediciones_formativas SET estado = 'Programado' WHERE estado = 'Programada'"
        )

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
            ],
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS matriculas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_empleado TEXT NOT NULL,
                edicion_id TEXT NOT NULL,
                fecha_matricula DATETIME DEFAULT CURRENT_TIMESTAMP,
                aprobado INTEGER,
                fecha_aprobacion TEXT,
                comentario_validacion TEXT,
                FOREIGN KEY (edicion_id) REFERENCES ediciones_formativas (id) ON DELETE CASCADE
            )
            '''
        )

        columnas_matriculas = {
            row[1] for row in cursor.execute('PRAGMA table_info(matriculas)').fetchall()
        }
        if 'edicion_id' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN edicion_id TEXT')
        if 'fecha_matricula' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN fecha_matricula DATETIME DEFAULT CURRENT_TIMESTAMP')
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricula_id INTEGER,
                numero_empleado TEXT NOT NULL,
                edicion_id TEXT NOT NULL,
                nombre_accion TEXT NOT NULL,
                estado_codigo TEXT NOT NULL,
                detalle TEXT,
                fecha_evento DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (estado_codigo) REFERENCES estado_matricula_catalogo (codigo),
                FOREIGN KEY (edicion_id) REFERENCES ediciones_formativas (id)
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
            CREATE TABLE IF NOT EXISTS sesiones_curso (
                id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
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
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_sesiones_curso_fecha ON sesiones_curso (edicion_id, fecha, hora_inicio)'
        )

        cursor.execute(
            '''
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
            '''
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_registro_asistencia_sesion ON registro_asistencia (id_sesion)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_registro_asistencia_empleado ON registro_asistencia (numero_empleado)'
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
            SELECT m.id, m.numero_empleado, m.edicion_id, m.aprobado, ca.nombre
            FROM matriculas m
            JOIN ediciones_formativas e ON e.id = m.edicion_id
            JOIN catalogo_acciones ca ON ca.id = e.catalogo_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM matricula_historial h
                WHERE h.matricula_id = m.id
            )
            '''
        ).fetchall()
        for fila in matriculas_sin_historial:
            valor_aprobado = fila[3]
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
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    fila[0], fila[1], fila[2], fila[4], estado_codigo,
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

        # ── Tabla de certificados emitidos (sistema QR) ──────────────────────
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS certificados_emitidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_validacion TEXT UNIQUE NOT NULL,
                matricula_id INTEGER NOT NULL,
                numero_empleado TEXT NOT NULL,
                edicion_id TEXT NOT NULL,
                fecha_emision DATETIME DEFAULT CURRENT_TIMESTAMP,
                tipo_documento TEXT NOT NULL,
                veces_validado INTEGER NOT NULL DEFAULT 0,
                activo INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(matricula_id) REFERENCES matriculas(id),
                FOREIGN KEY(numero_empleado) REFERENCES docentes(numero_empleado),
                FOREIGN KEY(edicion_id) REFERENCES ediciones_formativas(id)
            )
            '''
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_cert_token ON certificados_emitidos (token_validacion)'
        )

        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass
