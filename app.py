import os
import re
import secrets
import sqlite3
import csv
from io import StringIO
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, Response,
    session, redirect, url_for, jsonify, abort
)
from werkzeug.security import check_password_hash, generate_password_hash

# ==========================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ==========================================

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Clave secreta: se lee de variable de entorno en producción
app.secret_key = os.environ.get(
    'SECRET_KEY',
    secrets.token_hex(32)  # Fallback para desarrollo local
)

# Ruta de la base de datos configurable por variable de entorno
# Detecta automáticamente si está en PythonAnywhere o en desarrollo local
# Ruta de la base de datos configurable por variable de entorno
# Detecta automáticamente si está en PythonAnywhere o en desarrollo local
_env_db_path = os.environ.get('DATABASE_PATH')

if _env_db_path:
    DB_PATH = _env_db_path
else:
    # Si no hay variable de entorno, intenta estos fallbacks en orden:
    _local_db = os.path.join(os.path.dirname(__file__), 'matricula.db')
    _pythonanywhere_db = '/home/IPSDUNAH/mysite/matricula.db'
    
    # Usa el primero que exista, o el local como último recurso
    if os.path.exists(_local_db):
        DB_PATH = _local_db
    elif os.path.exists(_pythonanywhere_db):
        DB_PATH = _pythonanywhere_db
    else:
        DB_PATH = _local_db  # Fallback final: ruta local


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

        # Alimenta direcciones desde datos existentes para evitar listas hardcodeadas en app.py.
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
        # Si la BD no está lista todavía, el flujo normal seguirá manejando errores.
        pass


asegurar_migraciones_minimas()


# ==========================================
# HEADERS DE SEGURIDAD HTTP
# ==========================================

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# ==========================================
# HELPERS DE BASE DE DATOS Y CSRF
# ==========================================

def get_db_connection():
    # Usa la ruta del DB_PATH configurada (por variable de entorno o fallback)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generar_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']


def validar_csrf(token_recibido):
    token_session = session.get('_csrf_token')
    return token_session and secrets.compare_digest(token_session, token_recibido or '')


# Inyecta el token CSRF en todos los templates automáticamente
app.jinja_env.globals['csrf_token'] = generar_csrf_token


# ==========================================
# DECORADOR DE AUTENTICACIÓN DE ADMIN
# ==========================================

def admin_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logueado'):
            return redirect(url_for('login_admin'))
        return f(*args, **kwargs)
    return decorated


def superadmin_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logueado'):
            return redirect(url_for('login_admin'))
        if session.get('admin_rol') != 'superadmin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def validar_numero_empleado(numero):
    """Valida que el número de empleado solo tenga dígitos y tenga longitud razonable."""
    return numero and re.match(r'^\d{4,12}$', numero.strip())


def validar_id_curso(id_curso):
    """Valida que el ID de curso sea alfanumérico con guiones."""
    return id_curso and re.match(r'^[A-Z0-9\-]{2,20}$', id_curso.strip().upper())


def validar_username_admin(username):
    return username and re.match(r'^[a-zA-Z0-9_.-]{3,30}$', username.strip())


def validar_nombre_direccion(nombre):
    return nombre and 2 <= len(nombre.strip()) <= 80


def normalizar_direccion(direccion):
    direccion_normalizada = (direccion or '').strip().upper().replace(' ', '')
    if re.match(r'^[A-Z0-9]{2,12}$', direccion_normalizada):
        return direccion_normalizada
    return None


def obtener_direcciones(conn):
    return conn.execute(
        'SELECT codigo, nombre FROM direcciones ORDER BY codigo'
    ).fetchall()


def direccion_existe(conn, direccion_codigo):
    return bool(
        conn.execute(
            'SELECT 1 FROM direcciones WHERE codigo = ?',
            (direccion_codigo,)
        ).fetchone()
    )


def obtener_codigo_modalidad(modalidad):
    if modalidad == 'Virtual':
        return 'V'
    if modalidad == 'Presencial':
        return 'P'
    return None


def generar_id_curso(conn, direccion, modalidad):
    codigo_modalidad = obtener_codigo_modalidad(modalidad)
    prefijo = f'AF-{direccion}-{codigo_modalidad}-'

    existentes = conn.execute(
        'SELECT id FROM capacitaciones WHERE id LIKE ?',
        (f'{prefijo}%',)
    ).fetchall()

    ultimo = 0
    patron = re.compile(rf'^{re.escape(prefijo)}(\d{{3}})$')
    for row in existentes:
        match = patron.match((row['id'] or '').upper())
        if match:
            ultimo = max(ultimo, int(match.group(1)))

    return f'{prefijo}{ultimo + 1:03d}'


# ==========================================
# RUTAS PÚBLICAS (Portal de Profesores)
# ==========================================

@app.route('/')
def inicio():
    return render_template('index.html')


@app.route('/dashboard', methods=['POST'])
def dashboard():
    # Validar CSRF
    if not validar_csrf(request.form.get('_csrf_token')):
        return render_template('index.html', error='Token de seguridad inválido. Recarga la página.')

    numero_empleado = request.form.get('numero_empleado', '').strip()

    if not validar_numero_empleado(numero_empleado):
        return render_template('index.html', error='Número de empleado inválido. Debe contener solo dígitos (4-12 caracteres).')

    try:
        conn = get_db_connection()

        query_matriculados = '''
            SELECT c.id, c.nombre, c.mes, c.anio, m.horario_elegido, m.id as matricula_id
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            WHERE m.numero_empleado = ?
            ORDER BY c.anio DESC, c.mes
        '''
        cursos_matriculados = conn.execute(query_matriculados, (numero_empleado,)).fetchall()

        query_disponibles = '''
            SELECT id, nombre, mes, anio, trimestre FROM capacitaciones
            WHERE id NOT IN (
                SELECT id_capacitacion FROM matriculas WHERE numero_empleado = ?
            )
            ORDER BY anio DESC, mes
        '''
        cursos_raw = conn.execute(query_disponibles, (numero_empleado,)).fetchall()

        cursos_disponibles = []
        for c in cursos_raw:
            horarios = conn.execute(
                'SELECT horario FROM horarios_curso WHERE id_capacitacion = ?', (c['id'],)
            ).fetchall()
            cursos_disponibles.append({
                'id': c['id'],
                'nombre': c['nombre'],
                'mes': c['mes'],
                'anio': c['anio'],
                'trimestre': c['trimestre'],
                'horarios': [h['horario'] for h in horarios]
            })

        conn.close()
    except sqlite3.Error as e:
        return render_template('index.html', error='Error de conexión. Intente nuevamente.')

    return render_template(
        'dashboard.html',
        empleado=numero_empleado,
        cursos=cursos_disponibles,
        matriculados=cursos_matriculados
    )


@app.route('/matricular', methods=['POST'])
def matricular():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    numero_empleado = request.form.get('numero_empleado', '').strip()
    id_capacitacion = request.form.get('id_capacitacion', '').strip()
    horario_elegido = request.form.get('horario_elegido', '').strip()

    if not validar_numero_empleado(numero_empleado):
        abort(400)
    if not id_capacitacion or not horario_elegido:
        abort(400)

    try:
        conn = get_db_connection()

        # Verificar que el curso y horario existan realmente
        curso = conn.execute('SELECT id, nombre FROM capacitaciones WHERE id = ?', (id_capacitacion,)).fetchone()
        horario_valido = conn.execute(
            'SELECT 1 FROM horarios_curso WHERE id_capacitacion = ? AND horario = ?',
            (id_capacitacion, horario_elegido)
        ).fetchone()

        if not curso or not horario_valido:
            conn.close()
            return render_template('index.html', error='Curso o horario inválido.')

        # Verificar que no esté ya matriculado
        ya_matriculado = conn.execute(
            'SELECT 1 FROM matriculas WHERE numero_empleado = ? AND id_capacitacion = ?',
            (numero_empleado, id_capacitacion)
        ).fetchone()

        if ya_matriculado:
            conn.close()
            return redirect(url_for('dashboard'), code=307)

        conn.execute(
            'INSERT INTO matriculas (numero_empleado, id_capacitacion, horario_elegido) VALUES (?, ?, ?)',
            (numero_empleado, id_capacitacion, horario_elegido)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return render_template('index.html', error='Error al procesar la matrícula.')

    return render_template(
        'matricula_exitosa.html',
        empleado=numero_empleado,
        nombre_curso=curso['nombre'],
        id_curso=id_capacitacion,
        horario=horario_elegido
    )


@app.route('/cancelar_matricula', methods=['POST'])
def cancelar_matricula():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    numero_empleado = request.form.get('numero_empleado', '').strip()
    id_capacitacion = request.form.get('id_capacitacion', '').strip()

    if not validar_numero_empleado(numero_empleado) or not id_capacitacion:
        abort(400)

    try:
        conn = get_db_connection()
        curso = conn.execute('SELECT nombre FROM capacitaciones WHERE id = ?', (id_capacitacion,)).fetchone()
        nombre_curso = curso['nombre'] if curso else id_capacitacion

        conn.execute(
            'DELETE FROM matriculas WHERE numero_empleado = ? AND id_capacitacion = ?',
            (numero_empleado, id_capacitacion)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return render_template('index.html', error='Error al cancelar la matrícula.')

    return render_template(
        'matricula_cancelada.html',
        empleado=numero_empleado,
        nombre_curso=nombre_curso,
        id_curso=id_capacitacion
    )


# ==========================================
# RUTAS PRIVADAS (Panel de Administración)
# ==========================================

@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if session.get('admin_logueado'):
        return redirect(url_for('admin'))

    error = None
    if request.method == 'POST':
        if not validar_csrf(request.form.get('_csrf_token')):
            error = 'Token de seguridad inválido.'
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            try:
                conn = get_db_connection()
                try:
                    admin = conn.execute(
                        'SELECT password_hash, rol, direccion FROM admin_users WHERE username = ?',
                        (username,)
                    ).fetchone()
                except sqlite3.OperationalError:
                    # Compatibilidad con esquemas antiguos.
                    admin = conn.execute(
                        'SELECT password_hash FROM admin_users WHERE username = ?',
                        (username,)
                    ).fetchone()
                conn.close()

                if admin and check_password_hash(admin['password_hash'], password):
                    session['admin_logueado'] = True
                    session['admin_user'] = username
                    session['admin_rol'] = admin['rol'] if 'rol' in admin.keys() else ('superadmin' if username == 'admin' else 'admin')
                    session['admin_direccion'] = admin['direccion'] if 'direccion' in admin.keys() else 'IPSD'
                    return redirect(url_for('admin'))
                else:
                    error = 'Usuario o contraseña incorrectos.'
            except sqlite3.Error:
                error = 'Error de conexión con la base de datos.'

    return render_template('admin_login.html', error=error)


@app.route('/logout_admin')
def logout_admin():
    session.clear()
    return redirect(url_for('login_admin'))


@app.route('/admin')
@admin_requerido
def admin():
    anio_filtro = request.args.get('anio', '').strip()
    trimestre_filtro = request.args.get('trimestre', '').strip()
    mes_filtro = request.args.get('mes', '').strip()
    admin_rol = session.get('admin_rol', 'admin')
    admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'
    es_superadmin = admin_rol == 'superadmin'

    try:
        conn = get_db_connection()
        direcciones = obtener_direcciones(conn)

        query_matriculas = '''
            SELECT m.numero_empleado, c.id, c.nombre, c.anio, c.trimestre, c.mes, m.horario_elegido, m.fecha_matricula
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            WHERE 1=1
        '''
        params = []

        if not es_superadmin:
            query_matriculas += ' AND c.id LIKE ?'
            params.append(f'AF-{admin_direccion}-%')

        if anio_filtro:
            query_matriculas += ' AND c.anio = ?'
            params.append(anio_filtro)
        if trimestre_filtro:
            query_matriculas += ' AND c.trimestre = ?'
            params.append(trimestre_filtro)
        if mes_filtro:
            query_matriculas += ' AND c.mes = ?'
            params.append(mes_filtro)

        query_matriculas += ' ORDER BY c.anio DESC, c.mes, c.id, m.numero_empleado'
        registros = conn.execute(query_matriculas, params).fetchall()

        query_cursos = '''
            SELECT c.id, c.nombre, c.anio, c.trimestre, c.mes, c.dia, c.modalidad, c.cupos_maximos,
                   GROUP_CONCAT(h.horario, '<br>') as horarios_html,
                   COUNT(DISTINCT m.numero_empleado) as total_inscritos
            FROM capacitaciones c
            LEFT JOIN horarios_curso h ON c.id = h.id_capacitacion
            LEFT JOIN matriculas m ON c.id = m.id_capacitacion
        '''
        cursos_params = []
        if not es_superadmin:
            query_cursos += ' WHERE c.id LIKE ?'
            cursos_params.append(f'AF-{admin_direccion}-%')

        query_cursos += ' GROUP BY c.id ORDER BY c.anio DESC, c.mes'
        cursos = conn.execute(query_cursos, cursos_params).fetchall()

        # Stats para las tarjetas del dashboard
        if es_superadmin:
            total_matriculas = conn.execute('SELECT COUNT(*) FROM matriculas').fetchone()[0]
            total_cursos = conn.execute('SELECT COUNT(*) FROM capacitaciones').fetchone()[0]
            total_profesores = conn.execute('SELECT COUNT(DISTINCT numero_empleado) FROM matriculas').fetchone()[0]
        else:
            total_matriculas = conn.execute(
                '''
                SELECT COUNT(*)
                FROM matriculas m
                JOIN capacitaciones c ON c.id = m.id_capacitacion
                WHERE c.id LIKE ?
                ''',
                (f'AF-{admin_direccion}-%',)
            ).fetchone()[0]

            total_cursos = conn.execute(
                'SELECT COUNT(*) FROM capacitaciones WHERE id LIKE ?',
                (f'AF-{admin_direccion}-%',)
            ).fetchone()[0]

            total_profesores = conn.execute(
                '''
                SELECT COUNT(DISTINCT m.numero_empleado)
                FROM matriculas m
                JOIN capacitaciones c ON c.id = m.id_capacitacion
                WHERE c.id LIKE ?
                ''',
                (f'AF-{admin_direccion}-%',)
            ).fetchone()[0]

        stats = {
            'total_matriculas': total_matriculas,
            'total_cursos': total_cursos,
            'total_profesores': total_profesores,
        }

        usuarios_admin = []
        direcciones_gestion = []
        if es_superadmin:
            usuarios_admin = conn.execute(
                '''
                SELECT username, rol, direccion
                FROM admin_users
                ORDER BY CASE WHEN rol = 'superadmin' THEN 0 ELSE 1 END, username
                '''
            ).fetchall()

            direcciones_gestion = conn.execute(
                '''
                SELECT d.codigo, d.nombre,
                       (SELECT COUNT(*) FROM admin_users a WHERE a.direccion = d.codigo AND a.rol = 'admin') as total_admins,
                       (SELECT COUNT(*) FROM capacitaciones c WHERE c.id LIKE 'AF-' || d.codigo || '-%') as total_cursos
                FROM direcciones d
                ORDER BY d.codigo
                '''
            ).fetchall()

        conn.close()
    except sqlite3.Error:
        registros, cursos = [], []
        usuarios_admin = []
        direcciones = []
        direcciones_gestion = []
        stats = {'total_matriculas': 0, 'total_cursos': 0, 'total_profesores': 0}

    filtros_actuales = {
        'anio': anio_filtro,
        'trimestre': trimestre_filtro,
        'mes': mes_filtro
    }

    return render_template(
        'admin.html',
        registros=registros,
        cursos=cursos,
        usuarios_admin=usuarios_admin,
        filtros=filtros_actuales,
        stats=stats,
        admin_user=session.get('admin_user', 'Admin'),
        admin_rol=admin_rol,
        admin_direccion=admin_direccion,
        es_superadmin=es_superadmin,
        direcciones=direcciones,
        direcciones_gestion=direcciones_gestion
    )


@app.route('/admin/stats')
@admin_requerido
def admin_stats():
    """Endpoint JSON para alimentar los gráficos con Chart.js"""
    try:
        conn = get_db_connection()
        admin_rol = session.get('admin_rol', 'admin')
        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'

        where_stats = ''
        params = []
        if admin_rol != 'superadmin':
            where_stats = ' WHERE c.id LIKE ? '
            params.append(f'AF-{admin_direccion}-%')

        datos_cursos = conn.execute(f'''
            SELECT c.nombre, COUNT(m.numero_empleado) as total
            FROM capacitaciones c
            LEFT JOIN matriculas m ON c.id = m.id_capacitacion
            {where_stats}
            GROUP BY c.id
            ORDER BY total DESC
            LIMIT 10
        ''', params).fetchall()

        datos_meses = conn.execute(f'''
            SELECT c.mes || ' ' || c.anio as periodo, COUNT(m.id) as total
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            {where_stats}
            GROUP BY periodo
            ORDER BY c.anio DESC, c.mes
            LIMIT 12
        ''', params).fetchall()

        conn.close()

        return jsonify({
            'cursos': {
                'labels': [r['nombre'] for r in datos_cursos],
                'data': [r['total'] for r in datos_cursos]
            },
            'meses': {
                'labels': [r['periodo'] for r in datos_meses],
                'data': [r['total'] for r in datos_meses]
            }
        })
    except sqlite3.Error:
        return jsonify({'cursos': {'labels': [], 'data': []}, 'meses': {'labels': [], 'data': []}})


@app.route('/admin/crear_curso', methods=['POST'])
@admin_requerido
def crear_curso():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    nombre_curso = request.form.get('nombre_curso', '').strip()
    anio = request.form.get('anio', '').strip()
    trimestre = request.form.get('trimestre', '').strip()
    mes = request.form.get('mes', '').strip()
    dia = request.form.get('dia', '').strip()
    modalidad = request.form.get('modalidad', '').strip()
    cupos_maximos_raw = request.form.get('cupos_maximos', '').strip()
    horarios_seleccionados = request.form.getlist('horarios')
    es_superadmin = session.get('admin_rol') == 'superadmin'

    if es_superadmin:
        direccion_curso = normalizar_direccion(request.form.get('direccion_curso', ''))
    else:
        direccion_curso = normalizar_direccion(session.get('admin_direccion', 'IPSD'))

    try:
        cupos_maximos = int(cupos_maximos_raw)
    except (TypeError, ValueError):
        cupos_maximos = -1

    if (
        not nombre_curso
        or not anio
        or not trimestre
        or not mes
        or not dia
        or not direccion_curso
        or modalidad not in ['Virtual', 'Presencial']
        or cupos_maximos < 0
    ):
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()
        if not direccion_existe(conn, direccion_curso):
            conn.close()
            return redirect(url_for('admin'))

        id_curso = generar_id_curso(conn, direccion_curso, modalidad)
        conn.execute(
            'INSERT INTO capacitaciones (id, nombre, anio, trimestre, mes, dia, modalidad, cupos_maximos) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (id_curso, nombre_curso, anio, trimestre, mes, dia, modalidad, cupos_maximos)
        )
        for horario in horarios_seleccionados:
            conn.execute(
                'INSERT INTO horarios_curso (id_capacitacion, horario) VALUES (?, ?)',
                (id_curso, horario)
            )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        pass
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/crear_admin', methods=['POST'])
@superadmin_requerido
def crear_admin_usuario():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    direccion = normalizar_direccion(request.form.get('direccion', '').strip())

    if not validar_username_admin(username) or len(password) < 8 or not direccion:
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()

        if not direccion_existe(conn, direccion):
            conn.close()
            return redirect(url_for('admin'))

        conn.execute(
            'INSERT INTO admin_users (username, password_hash, rol, direccion) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(password), 'admin', direccion)
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        pass
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/actualizar_admin', methods=['POST'])
@superadmin_requerido
def actualizar_admin_usuario():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    username = request.form.get('username', '').strip()
    new_password = request.form.get('new_password', '').strip()
    direccion = normalizar_direccion(request.form.get('direccion', '').strip())

    if not username or not direccion:
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()
        admin_objetivo = conn.execute(
            'SELECT rol FROM admin_users WHERE username = ?',
            (username,)
        ).fetchone()

        if not admin_objetivo or admin_objetivo['rol'] == 'superadmin' or not direccion_existe(conn, direccion):
            conn.close()
            return redirect(url_for('admin'))

        if new_password:
            if len(new_password) < 8:
                conn.close()
                return redirect(url_for('admin'))
            conn.execute(
                'UPDATE admin_users SET direccion = ?, password_hash = ? WHERE username = ?',
                (direccion, generate_password_hash(new_password), username)
            )
        else:
            conn.execute(
                'UPDATE admin_users SET direccion = ? WHERE username = ?',
                (direccion, username)
            )

        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/eliminar_admin', methods=['POST'])
@superadmin_requerido
def eliminar_admin_usuario():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    username = request.form.get('username', '').strip()
    if not username:
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()
        admin_objetivo = conn.execute(
            'SELECT rol FROM admin_users WHERE username = ?',
            (username,)
        ).fetchone()

        if not admin_objetivo or admin_objetivo['rol'] == 'superadmin':
            conn.close()
            return redirect(url_for('admin'))

        conn.execute('DELETE FROM admin_users WHERE username = ?', (username,))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/crear_direccion', methods=['POST'])
@superadmin_requerido
def crear_direccion():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    codigo = normalizar_direccion(request.form.get('codigo', '').strip())
    nombre = request.form.get('nombre', '').strip()

    if not codigo or codigo == 'GLOBAL' or not validar_nombre_direccion(nombre):
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO direcciones (codigo, nombre) VALUES (?, ?)',
            (codigo, nombre)
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        pass
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/actualizar_direccion', methods=['POST'])
@superadmin_requerido
def actualizar_direccion():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    codigo_actual = normalizar_direccion(request.form.get('codigo_actual', '').strip())
    codigo_nuevo = normalizar_direccion(request.form.get('codigo_nuevo', '').strip())
    nombre_nuevo = request.form.get('nombre_nuevo', '').strip()

    if (
        not codigo_actual
        or not codigo_nuevo
        or codigo_actual == 'GLOBAL'
        or codigo_nuevo == 'GLOBAL'
        or not validar_nombre_direccion(nombre_nuevo)
    ):
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()

        if not direccion_existe(conn, codigo_actual):
            conn.close()
            return redirect(url_for('admin'))

        if codigo_actual != codigo_nuevo:
            if direccion_existe(conn, codigo_nuevo):
                conn.close()
                return redirect(url_for('admin'))

            existe_destino = conn.execute(
                'SELECT 1 FROM capacitaciones WHERE id LIKE ? LIMIT 1',
                (f'AF-{codigo_nuevo}-%',)
            ).fetchone()
            if existe_destino:
                conn.close()
                return redirect(url_for('admin'))

            cursos_a_renombrar = conn.execute(
                'SELECT id FROM capacitaciones WHERE id LIKE ?',
                (f'AF-{codigo_actual}-%',)
            ).fetchall()

            for fila in cursos_a_renombrar:
                id_anterior = fila['id']
                sufijo = id_anterior[len(f'AF-{codigo_actual}-'):]
                id_nuevo = f'AF-{codigo_nuevo}-{sufijo}'

                conn.execute(
                    'UPDATE horarios_curso SET id_capacitacion = ? WHERE id_capacitacion = ?',
                    (id_nuevo, id_anterior)
                )
                conn.execute(
                    'UPDATE matriculas SET id_capacitacion = ? WHERE id_capacitacion = ?',
                    (id_nuevo, id_anterior)
                )
                conn.execute(
                    'UPDATE capacitaciones SET id = ? WHERE id = ?',
                    (id_nuevo, id_anterior)
                )

            conn.execute(
                'UPDATE admin_users SET direccion = ? WHERE direccion = ? AND rol = ?',
                (codigo_nuevo, codigo_actual, 'admin')
            )

            conn.execute(
                'UPDATE direcciones SET codigo = ?, nombre = ? WHERE codigo = ?',
                (codigo_nuevo, nombre_nuevo, codigo_actual)
            )
        else:
            conn.execute(
                'UPDATE direcciones SET nombre = ? WHERE codigo = ?',
                (nombre_nuevo, codigo_actual)
            )

        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/eliminar_direccion', methods=['POST'])
@superadmin_requerido
def eliminar_direccion():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    codigo = normalizar_direccion(request.form.get('codigo', '').strip())
    if not codigo or codigo == 'GLOBAL':
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()

        total_direcciones = conn.execute('SELECT COUNT(*) FROM direcciones').fetchone()[0]
        total_admins = conn.execute(
            'SELECT COUNT(*) FROM admin_users WHERE direccion = ? AND rol = ?',
            (codigo, 'admin')
        ).fetchone()[0]
        total_cursos = conn.execute(
            'SELECT COUNT(*) FROM capacitaciones WHERE id LIKE ?',
            (f'AF-{codigo}-%',)
        ).fetchone()[0]

        if total_direcciones <= 1 or total_admins > 0 or total_cursos > 0:
            conn.close()
            return redirect(url_for('admin'))

        conn.execute('DELETE FROM direcciones WHERE codigo = ?', (codigo,))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/eliminar_curso', methods=['POST'])
@admin_requerido
def eliminar_curso():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    id_curso = request.form.get('id_curso', '').strip()
    if not id_curso:
        return redirect(url_for('admin'))

    admin_rol = session.get('admin_rol', 'admin')
    admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'

    if admin_rol != 'superadmin' and not id_curso.upper().startswith(f'AF-{admin_direccion}-'):
        abort(403)

    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM matriculas WHERE id_capacitacion = ?', (id_curso,))
        conn.execute('DELETE FROM horarios_curso WHERE id_capacitacion = ?', (id_curso,))
        conn.execute('DELETE FROM capacitaciones WHERE id = ?', (id_curso,))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/eliminar_matricula', methods=['POST'])
@admin_requerido
def admin_eliminar_matricula():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    numero_empleado = request.form.get('numero_empleado', '').strip()
    id_capacitacion = request.form.get('id_capacitacion', '').strip()

    if not numero_empleado or not id_capacitacion:
        return redirect(url_for('admin'))

    admin_rol = session.get('admin_rol', 'admin')
    admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'

    if admin_rol != 'superadmin' and not id_capacitacion.upper().startswith(f'AF-{admin_direccion}-'):
        abort(403)

    try:
        conn = get_db_connection()
        conn.execute(
            'DELETE FROM matriculas WHERE numero_empleado = ? AND id_capacitacion = ?',
            (numero_empleado, id_capacitacion)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/admin/vaciar_matriculas', methods=['POST'])
@superadmin_requerido
def admin_vaciar_matriculas():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    confirmacion = request.form.get('confirmacion', '')
    if confirmacion != 'ELIMINAR':
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM matriculas')
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass

    return redirect(url_for('admin'))


@app.route('/exportar')
@admin_requerido
def exportar_csv():
    anio_filtro = request.args.get('anio', '').strip()
    trimestre_filtro = request.args.get('trimestre', '').strip()
    mes_filtro = request.args.get('mes', '').strip()

    try:
        conn = get_db_connection()
        admin_rol = session.get('admin_rol', 'admin')
        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'

        query = '''
            SELECT m.numero_empleado, c.id, c.nombre, c.anio, c.trimestre, c.mes,
                   m.horario_elegido, m.fecha_matricula
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            WHERE 1=1
        '''
        params = []
        if admin_rol != 'superadmin':
            query += ' AND c.id LIKE ?'
            params.append(f'AF-{admin_direccion}-%')
        if anio_filtro:
            query += ' AND c.anio = ?'
            params.append(anio_filtro)
        if trimestre_filtro:
            query += ' AND c.trimestre = ?'
            params.append(trimestre_filtro)
        if mes_filtro:
            query += ' AND c.mes = ?'
            params.append(mes_filtro)

        query += ' ORDER BY c.anio DESC, c.mes, c.id, m.numero_empleado'
        registros = conn.execute(query, params).fetchall()
        conn.close()
    except sqlite3.Error:
        return redirect(url_for('admin'))

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow([
        'Numero de Empleado', 'ID Capacitacion', 'Nombre de la Capacitacion',
        'Anio', 'Trimestre', 'Mes', 'Horario Elegido', 'Fecha de Matricula'
    ])
    for fila in registros:
        cw.writerow([
            fila['numero_empleado'], fila['id'], fila['nombre'],
            fila['anio'], fila['trimestre'], fila['mes'],
            fila['horario_elegido'], fila['fecha_matricula'] or ''
        ])

    output = Response(si.getvalue(), mimetype='text/csv; charset=utf-8')
    nombre_archivo = "listado_matriculas_filtrado.csv" if (anio_filtro or trimestre_filtro or mes_filtro) else "listado_matriculas_general.csv"
    output.headers["Content-Disposition"] = f"attachment; filename={nombre_archivo}"
    return output


# ==========================================
# MANEJO DE ERRORES
# ==========================================

@app.errorhandler(403)
def forbidden(e):
    return render_template('index.html', error='Acceso denegado. Token de seguridad inválido.'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error='Página no encontrada.'), 404

@app.errorhandler(400)
def bad_request(e):
    return render_template('index.html', error='Solicitud inválida.'), 400


if __name__ == '__main__':
    app.run(debug=False)
