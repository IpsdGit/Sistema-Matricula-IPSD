from flask import abort, jsonify, redirect, render_template, request, session, url_for

from database import get_db_connection
from services.portal_service import (
    fetch_curso_detalle_docente,
    load_dashboard_context,
    marcar_asistencia_docente,
    process_cancelar_matricula,
    process_matricula,
)
from utils import (
    normalizar_correo,
    normalizar_filtro_historial,
    normalizar_filtro_notificacion,
    normalizar_seccion_dashboard,
    validar_correo,
    validar_csrf,
    validar_numero_empleado,
)


def register_portal_routes(app):
    def autenticar_docente(correo_institucional, numero_empleado):
        conn = get_db_connection()
        docente = conn.execute(
            '''
            SELECT id, numero_empleado, nombre_completo, correo_institucional, activo
            FROM docentes
            WHERE numero_empleado = ? AND correo_institucional = ?
            LIMIT 1
            ''',
            (numero_empleado, correo_institucional),
        ).fetchone()
        conn.close()
        return docente

    def docente_activo_desde_sesion():
        numero_empleado = (session.get('empleado_portal') or '').strip()
        correo_institucional = normalizar_correo(session.get('correo_docente'))

        if not validar_numero_empleado(numero_empleado) or not validar_correo(correo_institucional):
            return None

        docente = autenticar_docente(correo_institucional, numero_empleado)
        if not docente or not bool(docente['activo']):
            return None
        return docente

    @app.route('/')
    def inicio():
        return render_template('index.html')

    @app.route('/logout_docente')
    def logout_docente():
        session.pop('empleado_portal', None)
        session.pop('correo_docente', None)
        session.pop('nombre_docente', None)
        session.pop('docente_notificaciones_leidas', None)
        session.pop('_csrf_token', None)
        return redirect(url_for('inicio'))

    @app.route('/dashboard', methods=['GET', 'POST'])
    def dashboard():
        if request.method == 'POST':
            if not validar_csrf(request.form.get('_csrf_token')):
                return render_template('index.html', error='Token de seguridad inválido. Recarga la página.')

            correo_institucional = normalizar_correo(request.form.get('correo_institucional', ''))
            numero_empleado = request.form.get('numero_empleado', '').strip()

            if not validar_correo(correo_institucional):
                return render_template(
                    'index.html',
                    error='Correo institucional inválido. Verifica el formato e inténtalo de nuevo.',
                )

            if not validar_numero_empleado(numero_empleado):
                return render_template(
                    'index.html',
                    error='Número de empleado inválido. Debe contener solo dígitos (4-12 caracteres).',
                )

            docente = autenticar_docente(correo_institucional, numero_empleado)
            if not docente:
                return render_template(
                    'index.html',
                    error='Credenciales inválidas. Verifica tu correo institucional y número de empleado.',
                )

            if not bool(docente['activo']):
                return render_template(
                    'index.html',
                    error='Tu cuenta docente está inactiva. Solicita una sincronización de datos.',
                )

            session['empleado_portal'] = numero_empleado
            session['correo_docente'] = docente['correo_institucional']
            session['nombre_docente'] = docente['nombre_completo']
        else:
            numero_empleado = (session.get('empleado_portal') or '').strip()
            correo_institucional = normalizar_correo(session.get('correo_docente'))
            if not validar_numero_empleado(numero_empleado) or not validar_correo(correo_institucional):
                return render_template('index.html', error='Inicia sesión para acceder al portal docente.')

            docente = autenticar_docente(correo_institucional, numero_empleado)
            if not docente or not bool(docente['activo']):
                session.pop('empleado_portal', None)
                session.pop('correo_docente', None)
                session.pop('nombre_docente', None)
                return render_template(
                    'index.html',
                    error='Tu sesión expiró o tu usuario ya no está activo. Inicia sesión nuevamente.',
                )

            session['nombre_docente'] = docente['nombre_completo']

        seccion_activa = normalizar_seccion_dashboard(request.values.get('seccion', 'disponibles'))
        filtro_historial = normalizar_filtro_historial(request.values.get('filtro_historial', 'todas'))
        filtro_notificacion = normalizar_filtro_notificacion(request.values.get('filtro_notificacion', 'todas'))
        ids_notificaciones_leidas = session.get('docente_notificaciones_leidas', [])

        resultado = load_dashboard_context(
            numero_empleado,
            seccion_activa,
            filtro_historial,
            filtro_notificacion=filtro_notificacion,
            ids_notificaciones_leidas=ids_notificaciones_leidas,
        )
        if not resultado['ok']:
            return render_template('index.html', error=resultado['error'])

        if request.method == 'GET' and seccion_activa == 'notificaciones':
            notifs_todas = resultado['contexto'].get('notificaciones_todas', [])
            if notifs_todas:
                ids_actuales = [n['id'] for n in notifs_todas]
                leidas = set(session.get('docente_notificaciones_leidas', []))
                
                # Check if there are new unread notifications
                if not leidas.issuperset(ids_actuales):
                    leidas.update(ids_actuales)
                    session['docente_notificaciones_leidas'] = sorted(leidas)
                    session.modified = True
                    
            # Always update the context in-place so it reflects immediately
            for n in notifs_todas:
                n['leida'] = True
            for n in resultado['contexto'].get('notificaciones', []):
                n['leida'] = True
            resultado['contexto']['notificaciones_total'] = 0

        resultado['contexto']['nombre_docente'] = session.get('nombre_docente')
        resultado['contexto']['correo_docente'] = session.get('correo_docente')
        resultado['contexto']['matricula_feedback'] = session.pop('matricula_feedback', None)

        return render_template('dashboard.html', **resultado['contexto'])

    @app.route('/matricular', methods=['POST'])
    def matricular():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        numero_empleado = request.form.get('numero_empleado', '').strip()
        edicion_id = (request.form.get('edicion_id') or '').strip()
        horario_elegido = request.form.get('horario_elegido', '').strip()

        if not validar_numero_empleado(numero_empleado):
            abort(400)
        if not edicion_id:
            abort(400)

        resultado = process_matricula(numero_empleado, edicion_id, horario_elegido)
        if not resultado['ok']:
            if resultado.get('error_view') == 'dashboard':
                return render_template('dashboard.html', **resultado['contexto'], error=resultado['error'])
            return render_template('index.html', error=resultado['error'])

        session['matricula_feedback'] = {
            'tipo': 'success',
            'titulo': 'Matricula exitosa',
            'mensaje': f"Te inscribiste en {resultado['nombre_accion']} ({resultado['edicion_id']}).",
            'curso': resultado['nombre_accion'],
            'codigo': resultado['edicion_id'],
            'horario': resultado['horario'],
        }
        return redirect(
            url_for(
                'dashboard',
                seccion='disponibles',
            )
        )

    @app.route('/cancelar_matricula', methods=['POST'])
    def cancelar_matricula():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        numero_empleado = request.form.get('numero_empleado', '').strip()
        edicion_id = (request.form.get('edicion_id') or '').strip()
        matricula_id_raw = request.form.get('matricula_id', '').strip()

        if not validar_numero_empleado(numero_empleado):
            abort(400)

        matricula_id = None
        if matricula_id_raw.isdigit():
            matricula_id = int(matricula_id_raw)

        if not matricula_id and not edicion_id:
            abort(400)

        resultado = process_cancelar_matricula(numero_empleado, edicion_id, matricula_id)
        if not resultado['ok']:
            if resultado.get('http_status') == 404:
                abort(404)
            return render_template('index.html', error=resultado['error'])

        return render_template(
            'matricula_cancelada.html',
            empleado=resultado['empleado'],
            nombre_curso=resultado['nombre_accion'],
            id_curso=resultado['edicion_id'],
            edicion_id=resultado['edicion_id'],
        )

    @app.route('/api/curso_detalle/<id_curso>', methods=['GET'])
    def api_curso_detalle(id_curso):
        docente = docente_activo_desde_sesion()
        if not docente:
            return jsonify({'ok': False, 'error': 'Sesión expirada. Inicia sesión nuevamente.'}), 401

        resultado = fetch_curso_detalle_docente(docente['numero_empleado'], id_curso)
        if not resultado.get('ok'):
            return jsonify(resultado), resultado.get('status_code', 400)

        return jsonify(resultado)

    @app.route('/api/sesion/<int:id_sesion>/marcar_asistencia', methods=['POST'])
    def api_marcar_asistencia(id_sesion):
        docente = docente_activo_desde_sesion()
        if not docente:
            return jsonify({'ok': False, 'error': 'Sesión expirada. Inicia sesión nuevamente.'}), 401

        token_form = request.form.get('token_asistencia', '').strip()
        token_json = ''
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            token_json = (payload.get('token_asistencia') or '').strip()

        token_asistencia = token_form or token_json
        resultado = marcar_asistencia_docente(
            numero_empleado=docente['numero_empleado'],
            id_sesion=id_sesion,
            token_asistencia=token_asistencia,
        )
        if not resultado.get('ok'):
            return jsonify(resultado), resultado.get('status_code', 400)

        return jsonify(resultado), 200
