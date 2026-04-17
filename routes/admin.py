import csv
from datetime import datetime
from io import StringIO

from flask import Response, abort, flash, jsonify, redirect, render_template, request, session, url_for

from config import DIAS_SEMANA, HORARIOS_BASE, MESES_ES
from database import get_db_connection
from services.admin_service import (
    abrir_asistencia_sesion,
    authenticate_admin,
    cerrar_asistencia_sesion,
    create_admin_user_record,
    crear_sesion_manual,
    create_curso_records,
    create_direccion_record,
    delete_admin_user_record,
    eliminar_sesion,
    delete_curso_record,
    delete_direccion_record,
    delete_matricula_record,
    fetch_export_records,
    generar_calendario_base,
    get_admin_dashboard_payload,
    get_admin_stats_payload,
    listar_sesiones_curso,
    editar_sesion,
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
    def _es_ajax():
        return (
            request.form.get('ajax') == '1'
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in (request.headers.get('Accept') or '')
        )

    def _admin_puede_gestionar_curso(id_curso):
        admin_rol = session.get('admin_rol', 'admin')
        if admin_rol == 'superadmin':
            return True

        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'
        return (id_curso or '').strip().upper().startswith(f'AF-{admin_direccion}-')

    def _obtener_curso_de_sesion(id_sesion):
        try:
            id_sesion_int = int(id_sesion)
        except (TypeError, ValueError):
            return None

        try:
            conn = get_db_connection()
            fila = conn.execute(
                'SELECT id_curso FROM sesiones_curso WHERE id_sesion = ? LIMIT 1',
                (id_sesion_int,),
            ).fetchone()
            conn.close()
            return fila['id_curso'] if fila else None
        except Exception:
            return None

    def _obtener_detalle_curso(id_curso):
        id_curso = (id_curso or '').strip().upper()
        if not id_curso:
            return None

        try:
            conn = get_db_connection()
            fila = conn.execute(
                '''
                    SELECT id, anio, mes, dia, duracion_tipo, tipo_accion, horas_totales, semanas_duracion
                FROM capacitaciones
                WHERE id = ?
                LIMIT 1
                ''',
                (id_curso,),
            ).fetchone()
            conn.close()
            return fila
        except Exception:
            return None

    def _construir_configuracion_sesiones(sesiones_curso, fecha_default):
        fecha_fallback = (fecha_default or datetime.now().strftime('%Y-%m-%d')).strip()
        configuracion = {
            'fecha_inicio': fecha_fallback,
            'fecha_fin': fecha_fallback,
            'dias_semana': [],
            'hora_inicio': '',
            'hora_fin': '',
                'jornada': 'UNICA',
                'docente_sesion': '',
                'bloque_codigo': '',
        }

        if not sesiones_curso:
            return configuracion

        fechas = []
        dias_semana = set()
        franjas = {}
        jornadas = {}
        docentes = {}
        bloques = {}

        for sesion in sesiones_curso:
            fecha_iso = (sesion['fecha'] or '').strip()
            hora_inicio = (sesion['hora_inicio'] or '').strip()[:5]
            hora_fin = (sesion['hora_fin'] or '').strip()[:5]

            if fecha_iso:
                fechas.append(fecha_iso)
                try:
                    dia_semana = datetime.strptime(fecha_iso, '%Y-%m-%d').weekday()
                    if 0 <= dia_semana <= 6:
                        dias_semana.add(dia_semana)
                except ValueError:
                    pass

            if hora_inicio and hora_fin:
                clave_franja = (hora_inicio, hora_fin)
                franjas[clave_franja] = franjas.get(clave_franja, 0) + 1

            jornada = (sesion['jornada'] or '').strip().upper()
            if jornada:
                jornadas[jornada] = jornadas.get(jornada, 0) + 1

            docente_sesion = (sesion['docente_sesion'] or '').strip()
            if docente_sesion:
                docentes[docente_sesion] = docentes.get(docente_sesion, 0) + 1

            bloque_codigo = (sesion['bloque_codigo'] or '').strip().upper()
            if bloque_codigo:
                bloques[bloque_codigo] = bloques.get(bloque_codigo, 0) + 1

        if fechas:
            configuracion['fecha_inicio'] = min(fechas)
            configuracion['fecha_fin'] = max(fechas)

        configuracion['dias_semana'] = sorted(dias_semana)

        if franjas:
            franja_principal = sorted(
                franjas.items(),
                key=lambda item: (-item[1], item[0][0], item[0][1]),
            )[0][0]
            configuracion['hora_inicio'] = franja_principal[0]
            configuracion['hora_fin'] = franja_principal[1]

        if jornadas:
            configuracion['jornada'] = sorted(jornadas.items(), key=lambda item: (-item[1], item[0]))[0][0]

        if docentes:
            configuracion['docente_sesion'] = sorted(docentes.items(), key=lambda item: (-item[1], item[0]))[0][0]

        if bloques:
            configuracion['bloque_codigo'] = sorted(bloques.items(), key=lambda item: (-item[1], item[0]))[0][0]

        return configuracion

    def _parse_fecha_form(fecha_raw):
        fecha_limpia = (fecha_raw or '').strip()
        if not fecha_limpia:
            return None

        for formato in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                return datetime.strptime(fecha_limpia, formato)
            except ValueError:
                continue
        return None

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
            calendario_eventos=dashboard_payload['calendario_eventos'],
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

    @app.route('/admin/curso/<id_curso>/sesiones')
    @admin_requerido
    def admin_gestion_sesiones(id_curso):
        id_curso = (id_curso or '').strip().upper()
        if not id_curso:
            return redireccion_admin_vista('cursos')

        if not _admin_puede_gestionar_curso(id_curso):
            abort(403)

        vista_solicitada = request.args.get('view', 'cursos').strip().lower()
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

        sesiones_result = listar_sesiones_curso(id_curso)
        sesiones_curso = sesiones_result.get('sesiones', []) if sesiones_result.get('ok') else []
        curso_sesion_detalle = _obtener_detalle_curso(id_curso)
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        curso_sesion_config = _construir_configuracion_sesiones(sesiones_curso, fecha_hoy)

        return render_template(
            'admin.html',
            registros=dashboard_payload['registros'],
            cursos=dashboard_payload['cursos'],
            calendario_eventos=dashboard_payload['calendario_eventos'],
            usuarios_admin=dashboard_payload['usuarios_admin'],
            filtros=dashboard_payload['filtros'],
            stats=dashboard_payload['stats'],
            admin_user=session.get('admin_user', 'Admin'),
            admin_rol=admin_rol,
            admin_direccion=dashboard_payload['admin_direccion'],
            es_superadmin=dashboard_payload['es_superadmin'],
            direcciones=dashboard_payload['direcciones'],
            direcciones_gestion=dashboard_payload['direcciones_gestion'],
            vista_inicial='cursos',
            fecha_hoy=fecha_hoy,
            horarios_base=HORARIOS_BASE,
            curso_sesiones_id=id_curso,
            curso_sesion_detalle=curso_sesion_detalle,
            curso_sesion_config=curso_sesion_config,
            sesiones_curso=sesiones_curso,
        )

    @app.route('/admin/stats')
    @admin_requerido
    def admin_stats():
        stats_payload = get_admin_stats_payload(
            session.get('admin_rol', 'admin'),
            session.get('admin_direccion', 'IPSD'),
        )
        return jsonify({'cursos': stats_payload['cursos'], 'meses': stats_payload['meses']})

    @app.route('/admin/sesion/generar_calendario', methods=['POST'])
    @admin_requerido
    def admin_generar_calendario_sesiones():
        es_ajax = _es_ajax()

        if not validar_csrf(request.form.get('_csrf_token')):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        id_curso = request.form.get('id_curso', '').strip().upper()
        fecha_inicio = request.form.get('fecha_inicio', '').strip()
        fecha_fin = request.form.get('fecha_fin', '').strip()
        dias_semana = request.form.getlist('dias_semana')
        jornada = request.form.get('jornada', 'UNICA').strip().upper()
        docente_sesion = request.form.get('docente_sesion', '').strip()
        bloque_codigo = request.form.get('bloque_codigo', '').strip().upper()

        hora_inicio_list = request.form.getlist('hora_inicio')
        hora_fin_list = request.form.getlist('hora_fin')
        bloques = []
        for idx, inicio in enumerate(hora_inicio_list):
            fin = hora_fin_list[idx] if idx < len(hora_fin_list) else ''
            bloques.append({'hora_inicio': inicio, 'hora_fin': fin})

        hora_inicio_unica = request.form.get('hora_inicio', '').strip()
        hora_fin_unica = request.form.get('hora_fin', '').strip()
        if not bloques and hora_inicio_unica and hora_fin_unica:
            bloques.append({'hora_inicio': hora_inicio_unica, 'hora_fin': hora_fin_unica})

        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Curso inválido'}), 400
            return redireccion_admin_vista('cursos')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = generar_calendario_base(
            id_curso,
            fecha_inicio,
            fecha_fin,
            dias_semana,
            bloques,
            jornada=jornada,
            docente_sesion=docente_sesion,
            bloque_codigo=bloque_codigo,
        )
        if es_ajax:
            status = 200 if result.get('ok') else 400
            return jsonify(result), status

        return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))

    @app.route('/admin/sesion/crear', methods=['POST'])
    @admin_requerido
    def admin_crear_sesion():
        es_ajax = _es_ajax()

        if not validar_csrf(request.form.get('_csrf_token')):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        id_curso = request.form.get('id_curso', '').strip().upper()
        fecha = request.form.get('fecha', '').strip()
        hora_inicio = request.form.get('hora_inicio', '').strip()
        hora_fin = request.form.get('hora_fin', '').strip()
        jornada = request.form.get('jornada', 'UNICA').strip().upper()
        docente_sesion = request.form.get('docente_sesion', '').strip()
        bloque_codigo = request.form.get('bloque_codigo', '').strip().upper()

        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Curso inválido'}), 400
            return redireccion_admin_vista('cursos')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = crear_sesion_manual(
            id_curso,
            fecha,
            hora_inicio,
            hora_fin,
            jornada=jornada,
            docente_sesion=docente_sesion,
            bloque_codigo=bloque_codigo,
        )
        if es_ajax:
            status = 200 if result.get('ok') else 400
            return jsonify(result), status

        return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))

    @app.route('/admin/sesion/editar', methods=['POST'])
    @admin_requerido
    def admin_editar_sesion():
        es_ajax = _es_ajax()

        if not validar_csrf(request.form.get('_csrf_token')):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        id_sesion = request.form.get('id_sesion', '').strip()
        fecha = request.form.get('fecha', '').strip()
        hora_inicio = request.form.get('hora_inicio', '').strip()
        hora_fin = request.form.get('hora_fin', '').strip()
        jornada = request.form.get('jornada', 'UNICA').strip().upper()
        docente_sesion = request.form.get('docente_sesion', '').strip()
        bloque_codigo = request.form.get('bloque_codigo', '').strip().upper()
        id_curso_form = request.form.get('id_curso', '').strip().upper()

        id_curso = id_curso_form or _obtener_curso_de_sesion(id_sesion)
        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión inválida'}), 400
            return redireccion_admin_vista('cursos')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = editar_sesion(
            id_sesion,
            fecha,
            hora_inicio,
            hora_fin,
            jornada=jornada,
            docente_sesion=docente_sesion,
            bloque_codigo=bloque_codigo,
        )
        if es_ajax:
            status = 200 if result.get('ok') else 400
            return jsonify(result), status

        return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))

    @app.route('/admin/sesion/eliminar', methods=['POST'])
    @admin_requerido
    def admin_eliminar_sesion():
        es_ajax = _es_ajax()

        if not validar_csrf(request.form.get('_csrf_token')):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        id_sesion = request.form.get('id_sesion', '').strip()
        id_curso_form = request.form.get('id_curso', '').strip().upper()

        id_curso = id_curso_form or _obtener_curso_de_sesion(id_sesion)
        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión inválida'}), 400
            return redireccion_admin_vista('cursos')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = eliminar_sesion(id_sesion)
        if es_ajax:
            status = 200 if result.get('ok') else 400
            return jsonify(result), status

        return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))

    @app.route('/admin/sesion/abrir', methods=['POST'])
    @admin_requerido
    def admin_abrir_sesion_asistencia():
        es_ajax = _es_ajax()

        if not validar_csrf(request.form.get('_csrf_token')):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        id_sesion = request.form.get('id_sesion', '').strip()
        id_curso_form = request.form.get('id_curso', '').strip().upper()

        id_curso = id_curso_form or _obtener_curso_de_sesion(id_sesion)
        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión inválida'}), 400
            return redireccion_admin_vista('cursos')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = abrir_asistencia_sesion(id_sesion)
        if es_ajax:
            status = 200 if result.get('ok') else 400
            return jsonify(result), status

        return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))

    @app.route('/admin/sesion/cerrar', methods=['POST'])
    @admin_requerido
    def admin_cerrar_sesion_asistencia():
        es_ajax = _es_ajax()

        if not validar_csrf(request.form.get('_csrf_token')):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        id_sesion = request.form.get('id_sesion', '').strip()
        id_curso_form = request.form.get('id_curso', '').strip().upper()

        id_curso = id_curso_form or _obtener_curso_de_sesion(id_sesion)
        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión inválida'}), 400
            return redireccion_admin_vista('cursos')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = cerrar_asistencia_sesion(id_sesion)
        if es_ajax:
            status = 200 if result.get('ok') else 400
            return jsonify(result), status

        return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))

    @app.route('/admin/crear_curso', methods=['POST'])
    @admin_requerido
    def crear_curso():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        nombre_curso = request.form.get('nombre_curso', '').strip()
        trimestre = request.form.get('trimestre', '').strip()
        fecha_curso = request.form.get('fecha_curso', '').strip()
        tipo_accion = request.form.get('tipo_accion', 'CURSO').strip().upper()
        horas_totales_raw = request.form.get('horas_totales', '').strip()
        semanas_duracion_raw = request.form.get('semanas_duracion', '').strip()
        modalidad = request.form.get('modalidad', '').strip()
        enlace_virtual = request.form.get('enlace_virtual', '').strip()
        cupos_maximos_raw = request.form.get('cupos_maximos', '').strip()
        es_superadmin = session.get('admin_rol') == 'superadmin'

        if tipo_accion not in {'CONFERENCIA', 'SEMINARIO', 'CURSO'}:
            tipo_accion = 'CURSO'

        if es_superadmin:
            direccion_curso = normalizar_direccion(request.form.get('direccion_curso', ''))
        else:
            direccion_curso = normalizar_direccion(session.get('admin_direccion', 'IPSD'))

        try:
            cupos_maximos = int(cupos_maximos_raw)
        except (TypeError, ValueError):
            cupos_maximos = -1

        try:
            horas_totales = int(horas_totales_raw)
        except (TypeError, ValueError):
            horas_totales = 0

        try:
            semanas_duracion = int(semanas_duracion_raw)
        except (TypeError, ValueError):
            semanas_duracion = 1

        fecha_obj = _parse_fecha_form(fecha_curso)
        if not fecha_obj:
            flash('La fecha de inicio es inválida.', 'danger')
            return redireccion_admin_vista('cursos')

        if (
            not nombre_curso
            or not trimestre
            or not direccion_curso
            or modalidad not in ['Virtual', 'Presencial']
            or cupos_maximos < 0
            or horas_totales < 1
            or semanas_duracion < 1
        ):
            flash('Completa correctamente los campos obligatorios para crear la acción formativa.', 'danger')
            return redireccion_admin_vista('cursos')

        if modalidad == 'Virtual':
            if not enlace_virtual or not validar_enlace_virtual(enlace_virtual):
                flash('Debes ingresar un enlace válido para modalidad virtual.', 'danger')
                return redireccion_admin_vista('cursos')
        else:
            enlace_virtual = None
        fechas_objetivo = [fecha_obj]

        create_result = create_curso_records(
            nombre_curso=nombre_curso,
            trimestre=trimestre,
            modalidad=modalidad,
            tipo_accion=tipo_accion,
            horas_totales=horas_totales,
            semanas_duracion=semanas_duracion,
            cupos_maximos=cupos_maximos,
            enlace_virtual=enlace_virtual,
            direccion_curso=direccion_curso,
            fechas_objetivo=fechas_objetivo,
            franjas_horarias=[],
        )
        if not create_result['ok']:
            if create_result.get('validation_error'):
                flash(create_result['validation_error'], 'danger')
            elif create_result.get('invalid_direction'):
                flash('La dirección seleccionada no es válida.', 'danger')
            else:
                flash('No se pudo crear la acción formativa. Intenta nuevamente.', 'danger')
            return redireccion_admin_vista('cursos')

        flash('Acción formativa creada correctamente.', 'success')

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
        tipo_accion = request.form.get('tipo_accion', 'CURSO').strip().upper()
        horas_totales_raw = request.form.get('horas_totales', '').strip()
        semanas_duracion_raw = request.form.get('semanas_duracion', '').strip()
        modalidad = request.form.get('modalidad', '').strip()
        enlace_virtual = request.form.get('enlace_virtual', '').strip()
        cupos_maximos_raw = request.form.get('cupos_maximos', '').strip()

        if tipo_accion not in {'CONFERENCIA', 'SEMINARIO', 'CURSO'}:
            tipo_accion = 'CURSO'

        if not id_curso or not nombre_curso or trimestre not in ['I', 'II', 'III', 'IV']:
            return redireccion_admin_vista('cursos')

        fecha_obj = _parse_fecha_form(fecha_curso)
        if not fecha_obj:
            return redireccion_admin_vista('cursos')

        try:
            cupos_maximos = int(cupos_maximos_raw)
        except (TypeError, ValueError):
            cupos_maximos = -1

        try:
            horas_totales = int(horas_totales_raw)
        except (TypeError, ValueError):
            horas_totales = 0

        try:
            semanas_duracion = int(semanas_duracion_raw)
        except (TypeError, ValueError):
            semanas_duracion = 1

        if modalidad not in ['Virtual', 'Presencial'] or cupos_maximos < 0 or horas_totales < 1 or semanas_duracion < 1:
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
            tipo_accion=tipo_accion,
            horas_totales=horas_totales,
            semanas_duracion=semanas_duracion,
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
