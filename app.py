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
from werkzeug.security import check_password_hash

# ==========================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ==========================================

app = Flask(__name__)

# Clave secreta: se lee de variable de entorno en producción
app.secret_key = os.environ.get(
    'SECRET_KEY',
    secrets.token_hex(32)  # Fallback para desarrollo local
)

# Ruta de la base de datos configurable por variable de entorno
# En PythonAnywhere: configurar en Variables de Entorno la ruta del servidor
# Por defecto usa la ruta de PythonAnywhere si no está configurada
DB_PATH = os.environ.get(
    'DATABASE_PATH',
    '/home/IPSDUNAH/mysite/matricula.db'  # Fallback para PythonAnywhere
)


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


def validar_numero_empleado(numero):
    """Valida que el número de empleado solo tenga dígitos y tenga longitud razonable."""
    return numero and re.match(r'^\d{4,12}$', numero.strip())


def validar_id_curso(id_curso):
    """Valida que el ID de curso sea alfanumérico con guiones."""
    return id_curso and re.match(r'^[A-Z0-9\-]{2,20}$', id_curso.strip().upper())


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
                admin = conn.execute(
                    'SELECT password_hash FROM admin_users WHERE username = ?', (username,)
                ).fetchone()
                conn.close()

                if admin and check_password_hash(admin['password_hash'], password):
                    session['admin_logueado'] = True
                    session['admin_user'] = username
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

    try:
        conn = get_db_connection()

        query_matriculas = '''
            SELECT m.numero_empleado, c.id, c.nombre, c.anio, c.trimestre, c.mes, m.horario_elegido, m.fecha_matricula
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            WHERE 1=1
        '''
        params = []

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
            SELECT c.id, c.nombre, c.anio, c.trimestre, c.mes,
                   GROUP_CONCAT(h.horario, '<br>') as horarios_html,
                   COUNT(DISTINCT m.numero_empleado) as total_inscritos
            FROM capacitaciones c
            LEFT JOIN horarios_curso h ON c.id = h.id_capacitacion
            LEFT JOIN matriculas m ON c.id = m.id_capacitacion
            GROUP BY c.id
            ORDER BY c.anio DESC, c.mes
        '''
        cursos = conn.execute(query_cursos).fetchall()

        # Stats para las tarjetas del dashboard
        stats = {
            'total_matriculas': conn.execute('SELECT COUNT(*) FROM matriculas').fetchone()[0],
            'total_cursos': conn.execute('SELECT COUNT(*) FROM capacitaciones').fetchone()[0],
            'total_profesores': conn.execute('SELECT COUNT(DISTINCT numero_empleado) FROM matriculas').fetchone()[0],
        }

        conn.close()
    except sqlite3.Error:
        registros, cursos, stats = [], [], {'total_matriculas': 0, 'total_cursos': 0, 'total_profesores': 0}

    filtros_actuales = {
        'anio': anio_filtro,
        'trimestre': trimestre_filtro,
        'mes': mes_filtro
    }

    return render_template(
        'admin.html',
        registros=registros,
        cursos=cursos,
        filtros=filtros_actuales,
        stats=stats,
        admin_user=session.get('admin_user', 'Admin')
    )


@app.route('/admin/stats')
@admin_requerido
def admin_stats():
    """Endpoint JSON para alimentar los gráficos con Chart.js"""
    try:
        conn = get_db_connection()
        datos_cursos = conn.execute('''
            SELECT c.nombre, COUNT(m.numero_empleado) as total
            FROM capacitaciones c
            LEFT JOIN matriculas m ON c.id = m.id_capacitacion
            GROUP BY c.id
            ORDER BY total DESC
            LIMIT 10
        ''').fetchall()

        datos_meses = conn.execute('''
            SELECT c.mes || ' ' || c.anio as periodo, COUNT(m.id) as total
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            GROUP BY periodo
            ORDER BY c.anio DESC, c.mes
            LIMIT 12
        ''').fetchall()

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

    id_curso = request.form.get('id_curso', '').strip().upper()
    nombre_curso = request.form.get('nombre_curso', '').strip()
    anio = request.form.get('anio', '').strip()
    trimestre = request.form.get('trimestre', '').strip()
    mes = request.form.get('mes', '').strip()
    horarios_seleccionados = request.form.getlist('horarios')

    if not validar_id_curso(id_curso) or not nombre_curso or not anio or not trimestre or not mes:
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO capacitaciones (id, nombre, anio, trimestre, mes) VALUES (?, ?, ?, ?, ?)',
            (id_curso, nombre_curso, anio, trimestre, mes)
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


@app.route('/admin/eliminar_curso', methods=['POST'])
@admin_requerido
def eliminar_curso():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)

    id_curso = request.form.get('id_curso', '').strip()
    if not id_curso:
        return redirect(url_for('admin'))

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
@admin_requerido
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
        query = '''
            SELECT m.numero_empleado, c.id, c.nombre, c.anio, c.trimestre, c.mes,
                   m.horario_elegido, m.fecha_matricula
            FROM matriculas m
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            WHERE 1=1
        '''
        params = []
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
