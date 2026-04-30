import os
import re
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash

from config import DB_PATH, MESES_ES


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
            CREATE TABLE IF NOT EXISTS plantillas_certificados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direccion_codigo TEXT NOT NULL,
                nombre_plantilla TEXT NOT NULL,
                tipo_documento TEXT NOT NULL CHECK(tipo_documento IN ('DIPLOMA', 'CONSTANCIA')),
                ruta_firma_img TEXT NOT NULL,
                texto_certificado TEXT NOT NULL,
                firmante_nombre TEXT NOT NULL,
                firmante_cargo TEXT NOT NULL,
                activo INTEGER DEFAULT 1,
                FOREIGN KEY(direccion_codigo) REFERENCES direcciones(codigo)
            )
            '''
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
        if 'id_plantilla_certificado' not in columnas_capacitaciones:
            cursor.execute(
                'ALTER TABLE capacitaciones ADD COLUMN id_plantilla_certificado INTEGER REFERENCES plantillas_certificados(id)'
            )
        if 'enlace_virtual' not in columnas_capacitaciones:
            cursor.execute('ALTER TABLE capacitaciones ADD COLUMN enlace_virtual TEXT')
        if 'duracion_tipo' not in columnas_capacitaciones:
            cursor.execute("ALTER TABLE capacitaciones ADD COLUMN duracion_tipo TEXT NOT NULL DEFAULT 'un_dia'")
        if 'tipo_accion' not in columnas_capacitaciones:
            cursor.execute("ALTER TABLE capacitaciones ADD COLUMN tipo_accion TEXT NOT NULL DEFAULT 'CURSO'")
        if 'horas_totales' not in columnas_capacitaciones:
            cursor.execute('ALTER TABLE capacitaciones ADD COLUMN horas_totales INTEGER NOT NULL DEFAULT 20')
        if 'semanas_duracion' not in columnas_capacitaciones:
            cursor.execute('ALTER TABLE capacitaciones ADD COLUMN semanas_duracion INTEGER NOT NULL DEFAULT 1')

        columnas_capacitaciones = {
            row[1] for row in cursor.execute('PRAGMA table_info(capacitaciones)').fetchall()
        }
        if 'anio_fin' not in columnas_capacitaciones:
            cursor.execute("ALTER TABLE capacitaciones ADD COLUMN anio_fin TEXT NOT NULL DEFAULT ''")
        if 'mes_fin' not in columnas_capacitaciones:
            cursor.execute("ALTER TABLE capacitaciones ADD COLUMN mes_fin TEXT NOT NULL DEFAULT ''")
        if 'dia_fin' not in columnas_capacitaciones:
            cursor.execute("ALTER TABLE capacitaciones ADD COLUMN dia_fin TEXT NOT NULL DEFAULT ''")

        cursor.execute(
            '''
            UPDATE capacitaciones
            SET
                anio_fin = CASE WHEN TRIM(COALESCE(anio_fin, '')) = '' THEN COALESCE(anio, '') ELSE anio_fin END,
                mes_fin = CASE WHEN TRIM(COALESCE(mes_fin, '')) = '' THEN COALESCE(mes, '') ELSE mes_fin END,
                dia_fin = CASE WHEN TRIM(COALESCE(dia_fin, '')) = '' THEN COALESCE(dia, '') ELSE dia_fin END
            '''
        )

        # Backfill de fechas desde sesiones_curso cuando existan calendarios configurados.
        try:
            filas_fechas = cursor.execute(
                '''
                SELECT id_curso, MIN(fecha) AS fecha_inicio, MAX(fecha) AS fecha_fin
                FROM sesiones_curso
                GROUP BY id_curso
                '''
            ).fetchall()
        except sqlite3.Error:
            filas_fechas = []

        for fila in filas_fechas:
            id_curso = (fila[0] or '').strip().upper()
            fecha_inicio_iso = (fila[1] or '').strip()
            fecha_fin_iso = (fila[2] or '').strip()
            if not id_curso or not fecha_inicio_iso or not fecha_fin_iso:
                continue
            try:
                inicio_dt = datetime.strptime(fecha_inicio_iso, '%Y-%m-%d').date()
                fin_dt = datetime.strptime(fecha_fin_iso, '%Y-%m-%d').date()
            except ValueError:
                continue

            anio_inicio = str(inicio_dt.year)
            mes_inicio = MESES_ES[inicio_dt.month - 1]
            dia_inicio = str(inicio_dt.day)
            anio_fin = str(fin_dt.year)
            mes_fin = MESES_ES[fin_dt.month - 1]
            dia_fin = str(fin_dt.day)

            cursor.execute(
                '''
                UPDATE capacitaciones
                SET anio = ?, mes = ?, dia = ?, anio_fin = ?, mes_fin = ?, dia_fin = ?
                WHERE id = ?
                ''',
                (anio_inicio, mes_inicio, dia_inicio, anio_fin, mes_fin, dia_fin, id_curso)
            )

        cursor.execute(
            '''
            UPDATE capacitaciones
            SET tipo_accion = CASE
                WHEN UPPER(TRIM(COALESCE(tipo_accion, ''))) IN ('CONFERENCIA', 'SEMINARIO', 'CURSO')
                    THEN UPPER(TRIM(tipo_accion))
                WHEN TRIM(COALESCE(duracion_tipo, 'un_dia')) = 'un_dia'
                    THEN 'CONFERENCIA'
                WHEN TRIM(COALESCE(duracion_tipo, 'un_dia')) = 'varios_dias'
                    THEN 'SEMINARIO'
                ELSE 'CURSO'
            END
            '''
        )
        cursor.execute(
            '''
            UPDATE capacitaciones
            SET horas_totales = CASE
                WHEN COALESCE(horas_totales, 0) < 1 THEN
                    CASE
                        WHEN UPPER(TRIM(COALESCE(tipo_accion, 'CURSO'))) = 'CONFERENCIA' THEN 4
                        WHEN UPPER(TRIM(COALESCE(tipo_accion, 'CURSO'))) = 'SEMINARIO' THEN 16
                        ELSE 20
                    END
                ELSE horas_totales
            END
            '''
        )
        cursor.execute(
            '''
            UPDATE capacitaciones
            SET semanas_duracion = CASE
                WHEN COALESCE(semanas_duracion, 0) < 1 THEN
                    CASE
                        WHEN UPPER(TRIM(COALESCE(tipo_accion, 'CURSO'))) = 'CONFERENCIA' THEN 1
                        WHEN TRIM(COALESCE(duracion_tipo, 'un_dia')) = 'varios_dias' THEN 2
                        ELSE 1
                    END
                ELSE semanas_duracion
            END
            '''
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

        columnas_matriculas = {
            row[1] for row in cursor.execute('PRAGMA table_info(matriculas)').fetchall()
        }
        if 'fecha_matricula' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN fecha_matricula DATETIME DEFAULT CURRENT_TIMESTAMP')
        if 'aprobado' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN aprobado INTEGER')
        if 'fecha_aprobacion' not in columnas_matriculas:
            cursor.execute('ALTER TABLE matriculas ADD COLUMN fecha_aprobacion TEXT')
            # Intentar backfill desde el historial si existe algún registro de 'APROBADO'
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
            '''
        )
        columnas_sesiones = {
            row[1] for row in cursor.execute('PRAGMA table_info(sesiones_curso)').fetchall()
        }
        if 'jornada' not in columnas_sesiones:
            cursor.execute("ALTER TABLE sesiones_curso ADD COLUMN jornada TEXT NOT NULL DEFAULT 'UNICA'")
        if 'docente_sesion' not in columnas_sesiones:
            cursor.execute('ALTER TABLE sesiones_curso ADD COLUMN docente_sesion TEXT')
        if 'edicion' not in columnas_sesiones:
            cursor.execute('ALTER TABLE sesiones_curso ADD COLUMN edicion TEXT')
        if 'bloque_codigo' in columnas_sesiones:
            cursor.execute(
                '''
                UPDATE sesiones_curso
                SET edicion = UPPER(TRIM(bloque_codigo))
                WHERE (edicion IS NULL OR TRIM(edicion) = '')
                  AND bloque_codigo IS NOT NULL
                  AND TRIM(bloque_codigo) <> ''
                '''
            )

            cursor.execute('ALTER TABLE sesiones_curso RENAME TO sesiones_curso_legacy')
            cursor.execute(
                '''
                CREATE TABLE sesiones_curso (
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
                '''
            )
            cursor.execute(
                '''
                INSERT INTO sesiones_curso (
                    id_sesion, id_curso, fecha, hora_inicio, hora_fin,
                    jornada, docente_sesion, edicion, estado, token_asistencia
                )
                SELECT
                    id_sesion, id_curso, fecha, hora_inicio, hora_fin,
                    jornada, docente_sesion, edicion, estado, token_asistencia
                FROM sesiones_curso_legacy
                '''
            )
            cursor.execute('DROP TABLE sesiones_curso_legacy')

        cursor.execute(
            '''
            UPDATE sesiones_curso
            SET jornada = CASE
                WHEN UPPER(TRIM(COALESCE(jornada, ''))) IN ('MATUTINA', 'VESPERTINA', 'NOCTURNA')
                    THEN UPPER(TRIM(jornada))
                ELSE 'UNICA'
            END
            '''
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_sesiones_curso_fecha ON sesiones_curso (id_curso, fecha, hora_inicio)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_sesiones_curso_edicion ON sesiones_curso (id_curso, edicion)'
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
