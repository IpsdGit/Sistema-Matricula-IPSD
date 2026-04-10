import csv
from datetime import datetime
from io import StringIO

from flask import Response, abort, jsonify, redirect, render_template, request, session, url_for

from config import DIAS_SEMANA, HORARIOS_BASE, MESES_ES
from services.admin_service import (
    authenticate_admin,
    create_admin_user_record,
    create_curso_records,
    create_direccion_record,
    delete_admin_user_record,
    delete_curso_record,
    delete_direccion_record,
    delete_matricula_record,
    fetch_export_records,
    get_admin_dashboard_payload,
    get_admin_stats_payload,
    update_matricula_resultado,
    update_admin_user_record,
    update_curso_record,
    update_direccion_record,
    vaciar_matriculas_records,
)
from utils import (
    admin_requerido,
    normalizar_direccion,
    redireccion_admin_vista,
    superadmin_requerido,
    validar_csrf,
    validar_enlace_virtual,
    validar_nombre_direccion,
    validar_username_admin,
)


def register_admin_routes(app):
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

                auth_result = authenticate_admin(username, password)
                if auth_result['ok']:
                    session['admin_logueado'] = True
                    session['admin_user'] = auth_result['admin_user']
                    session['admin_rol'] = auth_result['admin_rol']
                    session['admin_direccion'] = auth_result['admin_direccion']
                    return redirect(url_for('admin'))

                error = auth_result['error']

        return render_template('admin_login.html', error=error)

    @app.route('/logout_admin')
    def logout_admin():
        session.clear()
        return redirect(url_for('login_admin'))

    @app.route('/admin')
    @admin_requerido
    def admin():
        vista_solicitada = request.args.get('view', '').strip().lower()
        anio_filtro = request.args.get('anio', '').strip()
        trimestre_filtro = request.args.get('trimestre', '').strip()
        mes_filtro = request.args.get('mes', '').strip()
        resultado_filtro = request.args.get('resultado', '').strip().lower()
        admin_rol = session.get('admin_rol', 'admin')
        dashboard_payload = get_admin_dashboard_payload(
            vista_solicitada,
            anio_filtro,
            trimestre_filtro,
            mes_filtro,
            resultado_filtro,
            admin_rol,
            session.get('admin_direccion', 'IPSD'),
        )

        return render_template(
            'admin.html',
            registros=dashboard_payload['registros'],
            cursos=dashboard_payload['cursos'],
            usuarios_admin=dashboard_payload['usuarios_admin'],
            filtros=dashboard_payload['filtros'],
            stats=dashboard_payload['stats'],
            admin_user=session.get('admin_user', 'Admin'),
            admin_rol=admin_rol,
            admin_direccion=dashboard_payload['admin_direccion'],
            es_superadmin=dashboard_payload['es_superadmin'],
            direcciones=dashboard_payload['direcciones'],
            direcciones_gestion=dashboard_payload['direcciones_gestion'],
            vista_inicial=dashboard_payload['vista_inicial'],
            fecha_hoy=datetime.now().strftime('%Y-%m-%d'),
            horarios_base=HORARIOS_BASE,
        )

    @app.route('/admin/stats')
    @admin_requerido
    def admin_stats():
        stats_payload = get_admin_stats_payload(
            session.get('admin_rol', 'admin'),
            session.get('admin_direccion', 'IPSD'),
        )
        return jsonify({'cursos': stats_payload['cursos'], 'meses': stats_payload['meses']})

    @app.route('/admin/crear_curso', methods=['POST'])
    @admin_requerido
    def crear_curso():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        nombre_curso = request.form.get('nombre_curso', '').strip()
        trimestre = request.form.get('trimestre', '').strip()
        fecha_curso = request.form.get('fecha_curso', '').strip()
        fechas_adicionales_raw = request.form.getlist('fechas_adicionales')
        modalidad = request.form.get('modalidad', '').strip()
        enlace_virtual = request.form.get('enlace_virtual', '').strip()
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

        try:
            fecha_obj = datetime.strptime(fecha_curso, '%Y-%m-%d')
        except ValueError:
            return redireccion_admin_vista('cursos')

        dia_semana = DIAS_SEMANA[fecha_obj.weekday()]

        fechas_adicionales = []
        fechas_vistas = {fecha_curso}
        for fecha_extra in fechas_adicionales_raw:
            fecha_extra = (fecha_extra or '').strip()
            if not fecha_extra or fecha_extra in fechas_vistas:
                continue
            try:
                fecha_extra_obj = datetime.strptime(fecha_extra, '%Y-%m-%d')
            except ValueError:
                return redireccion_admin_vista('cursos')
            fechas_vistas.add(fecha_extra)
            fechas_adicionales.append(fecha_extra_obj)

        if (
            not nombre_curso
            or not trimestre
            or not direccion_curso
            or modalidad not in ['Virtual', 'Presencial']
            or cupos_maximos < 0
        ):
            return redireccion_admin_vista('cursos')

        if modalidad == 'Virtual':
            if not enlace_virtual or not validar_enlace_virtual(enlace_virtual):
                return redireccion_admin_vista('cursos')
        else:
            enlace_virtual = None

        if not horarios_seleccionados:
            return redireccion_admin_vista('cursos')

        prefijo_dia = f'{dia_semana} '
        horarios_validos = {f'{dia_semana} {h}' for h in HORARIOS_BASE}
        if any((not h.startswith(prefijo_dia) or h not in horarios_validos) for h in horarios_seleccionados):
            return redireccion_admin_vista('cursos')

        franjas_horarias = []
        for horario in horarios_seleccionados:
            partes = horario.split(' ', 1)
            franjas_horarias.append(partes[1] if len(partes) == 2 else horario)

        fechas_objetivo = [fecha_obj] + fechas_adicionales

        create_result = create_curso_records(
            nombre_curso=nombre_curso,
            trimestre=trimestre,
            modalidad=modalidad,
            cupos_maximos=cupos_maximos,
            enlace_virtual=enlace_virtual,
            direccion_curso=direccion_curso,
            fechas_objetivo=fechas_objetivo,
            franjas_horarias=franjas_horarias,
        )
        if not create_result['ok']:
            return redireccion_admin_vista('cursos')

        return redireccion_admin_vista('cursos')

    @app.route('/admin/actualizar_curso', methods=['POST'])
    @admin_requerido
    def actualizar_curso():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        id_curso = request.form.get('id_curso', '').strip()
        nombre_curso = request.form.get('nombre_curso', '').strip()
        fecha_curso = request.form.get('fecha_curso', '').strip()
        trimestre = request.form.get('trimestre', '').strip()
        modalidad = request.form.get('modalidad', '').strip()
        enlace_virtual = request.form.get('enlace_virtual', '').strip()
        cupos_maximos_raw = request.form.get('cupos_maximos', '').strip()

        if not id_curso or not nombre_curso or trimestre not in ['I', 'II', 'III', 'IV']:
            return redireccion_admin_vista('cursos')

        try:
            fecha_obj = datetime.strptime(fecha_curso, '%Y-%m-%d')
        except ValueError:
            return redireccion_admin_vista('cursos')

        try:
            cupos_maximos = int(cupos_maximos_raw)
        except (TypeError, ValueError):
            cupos_maximos = -1

        if modalidad not in ['Virtual', 'Presencial'] or cupos_maximos < 0:
            return redireccion_admin_vista('cursos')

        if modalidad == 'Virtual':
            if not enlace_virtual or not validar_enlace_virtual(enlace_virtual):
                return redireccion_admin_vista('cursos')
        else:
            enlace_virtual = None

        admin_rol = session.get('admin_rol', 'admin')
        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'
        if admin_rol != 'superadmin' and not id_curso.upper().startswith(f'AF-{admin_direccion}-'):
            abort(403)

        anio = str(fecha_obj.year)
        mes = MESES_ES[fecha_obj.month - 1]
        dia = str(fecha_obj.day)
        dia_semana = DIAS_SEMANA[fecha_obj.weekday()]

        update_result = update_curso_record(
            id_curso=id_curso,
            nombre_curso=nombre_curso,
            anio=anio,
            trimestre=trimestre,
            mes=mes,
            dia=dia,
            modalidad=modalidad,
            cupos_maximos=cupos_maximos,
            enlace_virtual=enlace_virtual,
            dia_semana=dia_semana,
        )
        if not update_result['ok']:
            return redireccion_admin_vista('cursos')

        return redireccion_admin_vista('cursos')

    @app.route('/admin/crear_admin', methods=['POST'])
    @superadmin_requerido
    def crear_admin_usuario():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        direccion = normalizar_direccion(request.form.get('direccion', '').strip())

        if not validar_username_admin(username) or len(password) < 8 or not direccion:
            return redireccion_admin_vista('usuarios')

        create_admin_user_record(username, password, direccion)

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/actualizar_admin', methods=['POST'])
    @superadmin_requerido
    def actualizar_admin_usuario():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        username = request.form.get('username', '').strip()
        new_password = request.form.get('new_password', '').strip()
        direccion = normalizar_direccion(request.form.get('direccion', '').strip())

        if not username or not direccion:
            return redireccion_admin_vista('usuarios')

        if new_password and len(new_password) < 8:
            return redireccion_admin_vista('usuarios')

        update_admin_user_record(username, new_password, direccion)

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/eliminar_admin', methods=['POST'])
    @superadmin_requerido
    def eliminar_admin_usuario():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        username = request.form.get('username', '').strip()
        if not username:
            return redireccion_admin_vista('usuarios')

        delete_admin_user_record(username)

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/crear_direccion', methods=['POST'])
    @superadmin_requerido
    def crear_direccion():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        codigo = normalizar_direccion(request.form.get('codigo', '').strip())
        nombre = request.form.get('nombre', '').strip()

        if not codigo or codigo == 'GLOBAL' or not validar_nombre_direccion(nombre):
            return redireccion_admin_vista('usuarios')

        create_direccion_record(codigo, nombre)

        return redireccion_admin_vista('usuarios')

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
            return redireccion_admin_vista('usuarios')

        update_direccion_record(codigo_actual, codigo_nuevo, nombre_nuevo)

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/eliminar_direccion', methods=['POST'])
    @superadmin_requerido
    def eliminar_direccion():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        codigo = normalizar_direccion(request.form.get('codigo', '').strip())
        if not codigo or codigo == 'GLOBAL':
            return redireccion_admin_vista('usuarios')

        delete_direccion_record(codigo)

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/eliminar_curso', methods=['POST'])
    @admin_requerido
    def eliminar_curso():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        id_curso = request.form.get('id_curso', '').strip()
        if not id_curso:
            return redireccion_admin_vista('cursos')

        admin_rol = session.get('admin_rol', 'admin')
        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'

        if admin_rol != 'superadmin' and not id_curso.upper().startswith(f'AF-{admin_direccion}-'):
            abort(403)

        delete_curso_record(id_curso)

        return redireccion_admin_vista('cursos')

    @app.route('/admin/eliminar_matricula', methods=['POST'])
    @admin_requerido
    def admin_eliminar_matricula():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        numero_empleado = request.form.get('numero_empleado', '').strip()
        id_capacitacion = request.form.get('id_capacitacion', '').strip()
        matricula_id_raw = request.form.get('matricula_id', '').strip()

        matricula_id = int(matricula_id_raw) if matricula_id_raw.isdigit() else None

        if not numero_empleado or not id_capacitacion:
            return redireccion_admin_vista('matriculas')

        admin_rol = session.get('admin_rol', 'admin')
        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'

        if admin_rol != 'superadmin' and not id_capacitacion.upper().startswith(f'AF-{admin_direccion}-'):
            abort(403)

        delete_matricula_record(numero_empleado, id_capacitacion, matricula_id)

        return redireccion_admin_vista('matriculas')

    @app.route('/admin/actualizar_resultado_matricula', methods=['POST'])
    @admin_requerido
    def actualizar_resultado_matricula():
        es_ajax = (
            request.form.get('ajax') == '1'
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in (request.headers.get('Accept') or '')
        )

        if not validar_csrf(request.form.get('_csrf_token')):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión expirada. Recarga la página.'}), 403
            abort(403)

        numero_empleado = request.form.get('numero_empleado', '').strip()
        id_capacitacion = request.form.get('id_capacitacion', '').strip()
        matricula_id_raw = request.form.get('matricula_id', '').strip()
        aprobado_raw = request.form.get('aprobado', '').strip()

        matricula_id = int(matricula_id_raw) if matricula_id_raw.isdigit() else None

        if not numero_empleado or not id_capacitacion or not matricula_id:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Datos incompletos'}), 400
            return redireccion_admin_vista('matriculas')

        if aprobado_raw == '1':
            aprobado = 1
            resultado_texto = 'Aprobado'
            estado_codigo = 'APROBADA'
        elif aprobado_raw == '0':
            aprobado = 0
            resultado_texto = 'No aprobado'
            estado_codigo = 'NO_APROBADA'
        elif aprobado_raw == '2':
            aprobado = 2
            resultado_texto = 'Abandonó'
            estado_codigo = 'ABANDONO'
        elif aprobado_raw == '':
            aprobado = None
            resultado_texto = 'Pendiente'
            estado_codigo = 'PENDIENTE'
        else:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Resultado inválido'}), 400
            return redireccion_admin_vista('matriculas')

        update_result = update_matricula_resultado(
            numero_empleado=numero_empleado,
            id_capacitacion=id_capacitacion,
            matricula_id=matricula_id,
            aprobado=aprobado,
            estado_codigo=estado_codigo,
            admin_rol=session.get('admin_rol', 'admin'),
            admin_direccion=session.get('admin_direccion', 'IPSD'),
        )

        if not update_result['ok']:
            if es_ajax:
                return jsonify({'ok': False, 'error': update_result['error']}), update_result['status_code']
            if update_result['status_code'] == 403:
                abort(403)
            return redireccion_admin_vista('matriculas')

        if es_ajax:
            return jsonify({'ok': True, 'resultado': resultado_texto})

        return redireccion_admin_vista('matriculas')

    @app.route('/admin/vaciar_matriculas', methods=['POST'])
    @superadmin_requerido
    def admin_vaciar_matriculas():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        confirmacion = request.form.get('confirmacion', '')
        if confirmacion != 'ELIMINAR':
            return redireccion_admin_vista('matriculas')

        vaciar_matriculas_records()

        return redireccion_admin_vista('matriculas')

    @app.route('/exportar')
    @admin_requerido
    def exportar_csv():
        anio_filtro = request.args.get('anio', '').strip()
        trimestre_filtro = request.args.get('trimestre', '').strip()
        mes_filtro = request.args.get('mes', '').strip()
        resultado_filtro = request.args.get('resultado', '').strip().lower()

        export_result = fetch_export_records(
            anio_filtro,
            trimestre_filtro,
            mes_filtro,
            resultado_filtro,
            session.get('admin_rol', 'admin'),
            session.get('admin_direccion', 'IPSD'),
        )
        if not export_result['ok']:
            return redirect(url_for('admin'))

        registros = export_result['registros']

        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(
            [
                'Numero de Empleado',
                'ID Capacitacion',
                'Nombre de la Capacitacion',
                'Anio',
                'Trimestre',
                'Mes',
                'Horario Elegido',
                'Fecha de Matricula',
                'Resultado',
            ]
        )
        for fila in registros:
            if fila['aprobado'] == 1:
                resultado = 'Aprobado'
            elif fila['aprobado'] == 0:
                resultado = 'No aprobado'
            elif fila['aprobado'] == 2:
                resultado = 'Abandonó'
            else:
                resultado = 'Pendiente'

            cw.writerow(
                [
                    fila['numero_empleado'],
                    fila['id'],
                    fila['nombre'],
                    fila['anio'],
                    fila['trimestre'],
                    fila['mes'],
                    fila['horario_elegido'],
                    fila['fecha_matricula'] or '',
                    resultado,
                ]
            )

        output = Response(si.getvalue(), mimetype='text/csv; charset=utf-8')
        nombre_archivo = (
            'listado_matriculas_filtrado.csv'
            if (anio_filtro or trimestre_filtro or mes_filtro)
            else 'listado_matriculas_general.csv'
        )
        output.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
        return output
