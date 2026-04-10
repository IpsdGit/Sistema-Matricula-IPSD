from flask import abort, redirect, render_template, request, session, url_for

from services.portal_service import (
    load_dashboard_context,
    process_cancelar_matricula,
    process_matricula,
)
from utils import (
    normalizar_filtro_historial,
    normalizar_seccion_dashboard,
    validar_csrf,
    validar_numero_empleado,
)


def register_portal_routes(app):
    @app.route('/')
    def inicio():
        return render_template('index.html')

    @app.route('/logout_docente')
    def logout_docente():
        session.pop('empleado_portal', None)
        session.pop('_csrf_token', None)
        return redirect(url_for('inicio'))

    @app.route('/dashboard', methods=['GET', 'POST'])
    def dashboard():
        if request.method == 'POST':
            if not validar_csrf(request.form.get('_csrf_token')):
                return render_template('index.html', error='Token de seguridad inválido. Recarga la página.')

            numero_empleado = request.form.get('numero_empleado', '').strip()
            if not validar_numero_empleado(numero_empleado):
                return render_template(
                    'index.html',
                    error='Número de empleado inválido. Debe contener solo dígitos (4-12 caracteres).',
                )

            session['empleado_portal'] = numero_empleado
        else:
            numero_empleado = (session.get('empleado_portal') or '').strip()
            if not validar_numero_empleado(numero_empleado):
                return render_template('index.html', error='Inicia sesión para acceder al portal docente.')

        seccion_activa = normalizar_seccion_dashboard(request.values.get('seccion', 'disponibles'))
        filtro_historial = normalizar_filtro_historial(request.values.get('filtro_historial', 'todas'))

        resultado = load_dashboard_context(numero_empleado, seccion_activa, filtro_historial)
        if not resultado['ok']:
            return render_template('index.html', error=resultado['error'])

        return render_template('dashboard.html', **resultado['contexto'])

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

        resultado = process_matricula(numero_empleado, id_capacitacion, horario_elegido)
        if not resultado['ok']:
            if resultado.get('error_view') == 'dashboard':
                return render_template('dashboard.html', **resultado['contexto'], error=resultado['error'])
            return render_template('index.html', error=resultado['error'])

        return render_template(
            'matricula_exitosa.html',
            empleado=resultado['empleado'],
            nombre_curso=resultado['nombre_curso'],
            id_curso=resultado['id_curso'],
            horario=resultado['horario'],
        )

    @app.route('/cancelar_matricula', methods=['POST'])
    def cancelar_matricula():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        numero_empleado = request.form.get('numero_empleado', '').strip()
        id_capacitacion = request.form.get('id_capacitacion', '').strip()
        matricula_id_raw = request.form.get('matricula_id', '').strip()

        if not validar_numero_empleado(numero_empleado):
            abort(400)

        matricula_id = None
        if matricula_id_raw.isdigit():
            matricula_id = int(matricula_id_raw)

        if not matricula_id and not id_capacitacion:
            abort(400)

        resultado = process_cancelar_matricula(numero_empleado, id_capacitacion, matricula_id)
        if not resultado['ok']:
            if resultado.get('http_status') == 404:
                abort(404)
            return render_template('index.html', error=resultado['error'])

        return render_template(
            'matricula_cancelada.html',
            empleado=resultado['empleado'],
            nombre_curso=resultado['nombre_curso'],
            id_curso=resultado['id_curso'],
        )
