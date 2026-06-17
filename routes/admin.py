import csv
import os
import json
from datetime import datetime
from io import StringIO

# pyrefly: ignore [missing-import]
from flask import Response, abort, flash, jsonify, redirect, render_template, request, session, url_for
# pyrefly: ignore [missing-import]
from werkzeug.utils import secure_filename

from config import DIAS_SEMANA, HORARIOS_BASE, MESES_ES
from database import get_db_connection
from services.admin_service import (
    abrir_asistencia_sesion,
    authenticate_admin,
    cerrar_asistencia_sesion,
    create_admin_user_record,
    crear_sesion_manual,
    create_curso_records,
    crear_edicion_formativa,
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
    listar_ediciones_catalogo,
    obtener_catalogo_id_por_edicion,
    obtener_reporte_asistencia_curso,
    editar_sesion,
    update_matricula_resultado,
    update_admin_user_record,
    update_curso_record,
    update_direccion_record,
    update_edicion_metadata,
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

    def _obtener_centros_regionales_admin():
        conn = None
        try:
            from services.grupo_cerrado_service import obtener_centros_regionales
            conn = get_db_connection()
            return obtener_centros_regionales(conn)
        except Exception:
            return []
        finally:
            if conn is not None:
                conn.close()

    def _admin_puede_gestionar_curso(id_curso):
        admin_rol = session.get('admin_rol', 'admin')
        if admin_rol == 'superadmin':
            return True

        id_curso = (id_curso or '').strip().upper()
        if not id_curso:
            return False

        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'
        try:
            conn = get_db_connection()
            # Primero intentamos como edicion
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT 1
                    FROM ediciones_formativas ef
                    JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                    WHERE ef.id = %s AND ca.direccion_codigo = %s
                    LIMIT 1
                    ''',
                    (id_curso, admin_direccion),
                )
                fila = cur.fetchone()
            
            if not fila:
                # Si no es edicion, intentamos como catalogo
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT 1 FROM catalogo_acciones WHERE id = %s AND direccion_codigo = %s LIMIT 1',
                        (id_curso, admin_direccion),
                    )
                    fila = cur.fetchone()
                
            conn.close()
            return bool(fila)
        except Exception:
            return False

    def _admin_puede_gestionar_catalogo(catalogo_id):
        admin_rol = session.get('admin_rol', 'admin')
        if admin_rol == 'superadmin':
            return True

        catalogo_id = (catalogo_id or '').strip().upper()
        if not catalogo_id:
            return False

        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT 1 FROM catalogo_acciones WHERE id = %s AND direccion_codigo = %s LIMIT 1',
                    (catalogo_id, admin_direccion),
                )
                fila = cur.fetchone()
            conn.close()
            return bool(fila)
        except Exception:
            return False

    def _normalizar_estado_edicion(valor):
        texto = (valor or '').strip().lower()
        if texto in {'en edicion', 'en edición', 'en_edicion'}:
            return 'En Edicion'
        if texto in {'programado', 'programada'}:
            return 'Programado'
        if texto in {'finalizado', 'finalizada'}:
            return 'Finalizado'
        return 'En Edicion'

    def _obtener_curso_de_sesion(id_sesion):
        try:
            id_sesion_int = int(id_sesion)
        except (TypeError, ValueError):
            return None

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT edicion_id FROM sesiones_curso WHERE id_sesion = %s LIMIT 1',
                    (id_sesion_int,),
                )
                fila = cur.fetchone()
            conn.close()
            return fila['edicion_id'] if fila else None
        except Exception:
            return None

    def _obtener_detalle_curso(id_curso):
        id_curso = (id_curso or '').strip().upper()
        if not id_curso:
            return None

        try:
            conn = get_db_connection()
            # Intentar como edicion
            with conn.cursor() as cur:
                cur.execute(
                    '''
                      SELECT ef.id, ef.catalogo_id, ef.etiqueta_edicion, ef.periodo, ef.fecha_inicio,
                          ef.fecha_limite_matricula, ef.cupos_maximos, ef.enlace_acceso,
                          ef.privacidad, ef.jornada, ef.hora, ef.docente_responsable, ef.persona_apoyo,
                            ef.estado, ef.duracion_horas, ef.calendario_academico,
                          ca.id_plantilla_certificado,
                          COALESCE(NULLIF(ef.requisitos, ''), ca.requisitos) AS requisitos,
                          ca.requisitos AS requisitos_catalogo,
                          ca.tipo_accion, ca.modalidad, ca.nombre
                    FROM ediciones_formativas ef
                    JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                    WHERE ef.id = %s
                    LIMIT 1
                    ''',
                    (id_curso,),
                )
                fila = cur.fetchone()
            
            if not fila:
                # Intentar como catalogo (retornar estructura similar pero sin campos de edicion)
                with conn.cursor() as cur:
                    cur.execute(
                        '''
                              SELECT NULL as id, id as catalogo_id, '' as etiqueta_edicion, NULL as periodo, 
                                  NULL as fecha_inicio, NULL as fecha_limite_matricula, NULL as cupos_maximos, 
                                  NULL as enlace_acceso, 'Abierta' as privacidad, 'UNICA' as jornada, 
                                  '' as hora, '' as docente_responsable, '' as persona_apoyo,
                                  'En Edicion' as estado, NULL as duracion_horas, NULL as calendario_academico,
                                  id_plantilla_certificado,
                                  requisitos as requisitos, requisitos as requisitos_catalogo,
                                  tipo_accion, modalidad, nombre
                        FROM catalogo_acciones
                        WHERE id = %s
                        LIMIT 1
                        ''',
                        (id_curso,),
                    )
                    fila = cur.fetchone()
                
            conn.close()
            return dict(fila) if fila else None
        except Exception:
            return None

    def _obtener_catalogo_detalle(catalogo_id):
        catalogo_id = (catalogo_id or '').strip().upper()
        if not catalogo_id:
            return None

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id, nombre, modalidad, tipo_accion, direccion_codigo, id_plantilla_certificado
                    FROM catalogo_acciones
                    WHERE id = %s
                    LIMIT 1
                    ''',
                    (catalogo_id,),
                )
                fila = cur.fetchone()
            conn.close()
            return dict(fila) if fila else None
        except Exception:
            return None

    def _sincronizar_fechas_capacitacion_desde_sesiones(id_curso, fecha_inicio_fallback='', fecha_fin_fallback=''):
        """Mantiene fecha_inicio en ediciones_formativas según MIN(fecha) de sesiones_curso."""
        id_curso = (id_curso or '').strip().upper()
        if not id_curso:
            return

        def _parse_iso(iso_str):
            if not iso_str:
                return None
            if hasattr(iso_str, 'strftime'):
                if hasattr(iso_str, 'date'):
                    return iso_str.date()
                return iso_str
            iso_str_clean = str(iso_str).strip()
            if not iso_str_clean:
                return None
            try:
                return datetime.strptime(iso_str_clean, '%Y-%m-%d').date()
            except ValueError:
                return None

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT MIN(fecha) AS fecha_inicio, MAX(fecha) AS fecha_fin FROM sesiones_curso WHERE edicion_id = %s',
                    (id_curso,),
                )
                fila = cur.fetchone()

            fecha_inicio_val = fila['fecha_inicio'] if fila else None
            inicio_dt = _parse_iso(fecha_inicio_val) or _parse_iso(fecha_inicio_fallback)

            if not inicio_dt:
                conn.close()
                return

            with conn.cursor() as cur:
                cur.execute(
                    '''
                    UPDATE ediciones_formativas
                    SET fecha_inicio = %s
                    WHERE id = %s
                    ''',
                    (inicio_dt.strftime('%Y-%m-%d'), id_curso),
                )
            conn.commit()
            conn.close()
        except Exception:
            return

    def _construir_configuracion_sesiones(sesiones_curso, fecha_default, jornada_default=None, hora_default=None):
        fecha_fallback = (fecha_default or datetime.now().strftime('%Y-%m-%d')).strip()
        jornada_fallback = (jornada_default or 'UNICA').strip().upper() or 'UNICA'
        hora_fallback = (hora_default or '').strip()
        configuracion = {
            'fecha_inicio': fecha_fallback,
            'fecha_fin': fecha_fallback,
            'dias_semana': [],
            'dias_clase': '',
            'hora_inicio': '',
            'hora_fin': '',
            'jornada': jornada_fallback,
            'docente_sesion': '',
            'edicion': '',
            'segunda_jornada_activa': False,
            'dias_semana_2': [],
            'hora_inicio_2': '',
            'hora_fin_2': '',
            'jornada_2': 'VESPERTINA',
            'docente_sesion_2': '',
            'edicion_2': '',
        }

        if hora_fallback and '-' in hora_fallback:
            partes = hora_fallback.split('-', 1)
            configuracion['hora_inicio'] = (partes[0] or '').strip()
            configuracion['hora_fin'] = (partes[1] or '').strip()

        if not sesiones_curso:
            return configuracion

        fechas = []
        bloques_calendario = {}

        def _modo_valor(conteos):
            if not conteos:
                return ''
            return sorted(conteos.items(), key=lambda item: (-item[1], item[0]))[0][0]

        def _aplicar_bloque(config, key, data, sufijo=''):
            jornada, hora_inicio, hora_fin = key
            config[f'jornada{sufijo}'] = jornada or 'UNICA'
            config[f'hora_inicio{sufijo}'] = hora_inicio or ''
            config[f'hora_fin{sufijo}'] = hora_fin or ''
            config[f'dias_semana{sufijo}'] = sorted(data['dias_semana'])
            config[f'dias_clase{sufijo}'] = ','.join(str(dia) for dia in sorted(data['dias_semana']))
            config[f'docente_sesion{sufijo}'] = _modo_valor(data.get('docentes', {}))
            config[f'edicion{sufijo}'] = _modo_valor(data.get('ediciones', {}))

        for sesion in sesiones_curso:
            fecha_iso = (sesion['fecha'] or '').strip()
            hora_inicio = (sesion['hora_inicio'] or '').strip()[:5]
            hora_fin = (sesion['hora_fin'] or '').strip()[:5]
            jornada = jornada_fallback

            clave_bloque = (jornada, hora_inicio, hora_fin)
            if clave_bloque not in bloques_calendario:
                bloques_calendario[clave_bloque] = {
                    'conteo': 0,
                    'dias_semana': set(),
                    'docentes': {},
                    'ediciones': {},
                }
            bloque_actual = bloques_calendario[clave_bloque]
            bloque_actual['conteo'] += 1

            if fecha_iso:
                fechas.append(fecha_iso)
                try:
                    dia_semana = datetime.strptime(fecha_iso, '%Y-%m-%d').weekday()
                    if 0 <= dia_semana <= 6:
                        bloque_actual['dias_semana'].add(dia_semana)
                except ValueError:
                    pass

            # Sesiones actuales no registran docente/jornada/edicion por bloque.

        if fechas:
            configuracion['fecha_inicio'] = min(fechas)
            configuracion['fecha_fin'] = max(fechas)

        if not bloques_calendario:
            return configuracion

        bloques_ordenados = sorted(
            bloques_calendario.items(),
            key=lambda item: (-item[1]['conteo'], item[0][0], item[0][1], item[0][2]),
        )

        _aplicar_bloque(configuracion, bloques_ordenados[0][0], bloques_ordenados[0][1])

        if len(bloques_ordenados) > 1:
            configuracion['segunda_jornada_activa'] = True
            _aplicar_bloque(configuracion, bloques_ordenados[1][0], bloques_ordenados[1][1], '_2')

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

    def _formatear_datetime_local(valor):
        if not valor:
            return ''
        if hasattr(valor, 'strftime'):
            if hasattr(valor, 'hour'):
                return valor.strftime('%Y-%m-%dT%H:%M')
            return valor.strftime('%Y-%m-%d')
        texto = str(valor).strip()
        texto = texto.replace(' ', 'T')
        return texto[:16]

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
        periodo_filtro = request.args.get('periodo', '').strip()
        mes_filtro = request.args.get('mes', '').strip()
        resultado_filtro = request.args.get('resultado', '').strip().lower()
        admin_rol = session.get('admin_rol', 'admin')
        dashboard_payload = get_admin_dashboard_payload(
            vista_solicitada,
            anio_filtro,
            periodo_filtro,
            mes_filtro,
            resultado_filtro,
            admin_rol,
            session.get('admin_direccion', 'IPSD'),
        )

        from services.certificate_service import obtener_plantillas_por_direccion, obtener_todas_las_plantillas
        if admin_rol == 'superadmin':
            plantillas = obtener_todas_las_plantillas()
        else:
            plantillas = obtener_plantillas_por_direccion(session.get('admin_direccion', 'IPSD'))

        centros_regionales = _obtener_centros_regionales_admin()

        # --- Lógica para reportes (pestaña matriculas) ---
        calendario_filtro = request.args.get('calendario', '').strip()
        cur_filtro = request.args.get('cur', '').strip()
        facultad_filtro = request.args.get('facultad', '').strip()
        departamento_filtro = request.args.get('departamento', '').strip()
        jerarquia = []
        historial = []
        
        if vista_solicitada == 'matriculas':
            from services.reportes_service import obtener_reporte_jerarquico, obtener_historial_reportes
            res = obtener_reporte_jerarquico(anio_filtro, calendario_filtro, periodo_filtro, cur_filtro, facultad_filtro, departamento_filtro, admin_rol, session.get('admin_direccion', 'IPSD'))
            jerarquia = res.get('jerarquia', [])
            historial = obtener_historial_reportes()
            
            # Calcular datos para los gráficos
            top_acciones = sorted(jerarquia, key=lambda x: x['total_matriculados'], reverse=True)[:5]
            max_matriculados = max([a['total_matriculados'] for a in top_acciones]) if top_acciones else 1
            
            matriculas_por_mes = [0] * 12
            distribucion_centros = {}
            filas_planas = res.get('filas_planas', [])
            for r in filas_planas:
                # Comprobar si hay matricula_id
                matricula_id = r[7] if isinstance(r, tuple) else r['matricula_id']
                if matricula_id:
                    fecha_inicio = r[6] if isinstance(r, tuple) else r['fecha_inicio']
                    if fecha_inicio:
                        mes_index = fecha_inicio.month - 1
                        matriculas_por_mes[mes_index] += 1
                    
                    centro = (r[12] if isinstance(r, tuple) else r['centro_universitario_regional']) or 'No Asignado'
                    distribucion_centros[centro] = distribucion_centros.get(centro, 0) + 1
            
            # Ordenar de mayor a menor y tomar el top 8 para no saturar el grafico
            distribucion_centros = dict(sorted(distribucion_centros.items(), key=lambda item: item[1], reverse=True)[:8])
            
            
            # Obtener facultades para el dropdown
            try:
                conn_fac = get_db_connection()
                cur_fac = conn_fac.cursor()
                cur_fac.execute("SELECT DISTINCT TRIM(facultad) AS f FROM docentes WHERE facultad IS NOT NULL AND TRIM(facultad) <> '' ORDER BY f")
                facultades = [r['f'] for r in cur_fac.fetchall()]
                
                cur_fac.execute("SELECT DISTINCT TRIM(departamento) AS d FROM docentes WHERE departamento IS NOT NULL AND TRIM(departamento) <> '' ORDER BY d")
                departamentos = [r['d'] for r in cur_fac.fetchall()]
                conn_fac.close()
            except Exception:
                facultades = []
                departamentos = []
            
            # Guardamos los filtros adicionales
            dashboard_payload['filtros']['calendario'] = calendario_filtro
            dashboard_payload['filtros']['cur'] = cur_filtro
            dashboard_payload['filtros']['facultad'] = facultad_filtro
            dashboard_payload['filtros']['departamento'] = departamento_filtro
        else:
            facultades = []
            departamentos = []
            top_acciones = []
            max_matriculados = 1
            matriculas_por_mes = [0] * 12
            distribucion_centros = {}
        # -------------------------------------------------

        return render_template(
            'admin.html',
            registros=dashboard_payload['registros'],
            cursos=dashboard_payload['cursos'],
            catalogos=dashboard_payload['catalogos'],
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
            plantillas=plantillas,
            centros_regionales=centros_regionales,
            jerarquia=jerarquia,
            historial=historial,
            facultades=facultades,
            departamentos=departamentos,
            top_acciones=top_acciones,
            max_matriculados=max_matriculados,
            matriculas_por_mes=json.dumps(matriculas_por_mes),
            distribucion_centros=json.dumps(distribucion_centros)
        )


    @app.route('/admin/ediciones/nueva')
    @admin_requerido
    def admin_nueva_edicion():
        catalogo_id = (request.args.get('catalogo_id') or '').strip().upper()
        if not catalogo_id:
            return redireccion_admin_vista('ediciones')

        if not _admin_puede_gestionar_catalogo(catalogo_id):
            abort(403)

        vista_solicitada = request.args.get('view', 'ediciones').strip().lower()
        anio_filtro = request.args.get('anio', '').strip()
        periodo_filtro = request.args.get('periodo', '').strip()
        mes_filtro = request.args.get('mes', '').strip()
        resultado_filtro = request.args.get('resultado', '').strip().lower()
        admin_rol = session.get('admin_rol', 'admin')

        dashboard_payload = get_admin_dashboard_payload(
            vista_solicitada,
            anio_filtro,
            periodo_filtro,
            mes_filtro,
            resultado_filtro,
            admin_rol,
            session.get('admin_direccion', 'IPSD'),
        )

        catalogo_detalle = _obtener_catalogo_detalle(catalogo_id)
        if not catalogo_detalle:
            return redireccion_admin_vista('ediciones')

        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        curso_sesion_config = _construir_configuracion_sesiones([], fecha_hoy)

        from services.certificate_service import obtener_plantillas_por_direccion, obtener_todas_las_plantillas
        if dashboard_payload['es_superadmin']:
            plantillas = obtener_todas_las_plantillas()
        else:
            plantillas = obtener_plantillas_por_direccion(session.get('admin_direccion', 'IPSD'))

        centros_regionales = _obtener_centros_regionales_admin()

        return render_template(
            'admin.html',
            registros=dashboard_payload['registros'],
            cursos=dashboard_payload['cursos'],
            catalogos=dashboard_payload['catalogos'],
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
            vista_inicial=vista_solicitada,
            fecha_hoy=fecha_hoy,
            horarios_base=HORARIOS_BASE,
            plantillas=plantillas,
            curso_sesiones_id='',
            curso_sesion_detalle=catalogo_detalle,
            curso_sesion_config=curso_sesion_config,
            jornadas_config=[],
            catalogo_id=catalogo_id,
            sesiones_curso=[],
            modo_nueva_edicion=True,
            catalogo_seleccionado=catalogo_detalle,
            centros_regionales=centros_regionales,
        )

    @app.route('/admin/curso/<id_curso>/sesiones')
    @admin_requerido
    def admin_gestion_sesiones(id_curso):
        id_curso = (id_curso or '').strip().upper()
        if not id_curso:
            return redireccion_admin_vista('ediciones')

        if not _admin_puede_gestionar_curso(id_curso):
            abort(403)

        vista_solicitada = request.args.get('view', 'ediciones').strip().lower()
        anio_filtro = request.args.get('anio', '').strip()
        periodo_filtro = request.args.get('periodo', '').strip()
        mes_filtro = request.args.get('mes', '').strip()
        resultado_filtro = request.args.get('resultado', '').strip().lower()
        admin_rol = session.get('admin_rol', 'admin')

        dashboard_payload = get_admin_dashboard_payload(
            vista_solicitada,
            anio_filtro,
            periodo_filtro,
            mes_filtro,
            resultado_filtro,
            admin_rol,
            session.get('admin_direccion', 'IPSD'),
        )

        sesiones_result = listar_sesiones_curso(id_curso)
        sesiones_curso = sesiones_result.get('sesiones', []) if sesiones_result.get('ok') else []
        curso_sesion_detalle = _obtener_detalle_curso(id_curso)
        catalogo_id = (curso_sesion_detalle['catalogo_id'] if curso_sesion_detalle else None)
        if id_curso:
            ediciones_catalogo = [curso_sesion_detalle] if curso_sesion_detalle else []
        else:
            ediciones_catalogo = listar_ediciones_catalogo(catalogo_id)
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')

        jornadas_config = []
        for edicion in ediciones_catalogo:
            sesiones_edicion_result = listar_sesiones_curso(edicion['id'])
            sesiones_edicion = (
                sesiones_edicion_result.get('sesiones', [])
                if sesiones_edicion_result.get('ok')
                else []
            )
            config = _construir_configuracion_sesiones(
                sesiones_edicion,
                fecha_hoy,
                jornada_default=edicion['jornada'],
                hora_default=edicion['hora'],
            )
            config.update(
                {
                    'edicion_id': edicion['id'],
                    'etiqueta_edicion': edicion['etiqueta_edicion'] or '',
                    'docente_responsable': edicion['docente_responsable'] or '',
                    'persona_apoyo': edicion['persona_apoyo'] or '',
                    'calendario_academico': edicion['calendario_academico'] or 'Trimestral',
                    'periodo': edicion['periodo'] or '',
                    'cupos_maximos': edicion['cupos_maximos'] if edicion['cupos_maximos'] is not None else '',
                    'privacidad': (edicion['privacidad'] or 'Abierta'),
                    'estado': edicion['estado'] or 'En Edicion',
                    'fecha_limite_input': _formatear_datetime_local(edicion['fecha_limite_matricula']),
                }
            )
            jornadas_config.append(config)

        if jornadas_config:
            curso_sesion_config = jornadas_config[0]
        else:
            curso_sesion_config = _construir_configuracion_sesiones([], fecha_hoy)

        from services.certificate_service import obtener_plantillas_por_direccion, obtener_todas_las_plantillas
        if admin_rol == 'superadmin':
            plantillas = obtener_todas_las_plantillas()
        else:
            plantillas = obtener_plantillas_por_direccion(session.get('admin_direccion', 'IPSD'))

        centros_regionales = _obtener_centros_regionales_admin()

        return render_template(
            'admin.html',
            registros=dashboard_payload['registros'],
            cursos=dashboard_payload['cursos'],
            catalogos=dashboard_payload['catalogos'],
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
            vista_inicial=vista_solicitada,
            fecha_hoy=fecha_hoy,
            horarios_base=HORARIOS_BASE,
            plantillas=plantillas,
            curso_sesiones_id=id_curso,
            curso_sesion_detalle=curso_sesion_detalle,
            curso_sesion_config=curso_sesion_config,
            jornadas_config=jornadas_config,
            catalogo_id=catalogo_id,
            sesiones_curso=sesiones_curso,
            centros_regionales=centros_regionales,
        )

    @app.route('/admin/stats')
    @admin_requerido
    def admin_stats():
        stats_payload = get_admin_stats_payload(
            session.get('admin_rol', 'admin'),
            session.get('admin_direccion', 'IPSD'),
        )
        return jsonify({'cursos': stats_payload['cursos'], 'meses': stats_payload['meses']})

    @app.route('/admin/catalogo/eliminar', methods=['POST'])
    @admin_requerido
    def admin_eliminar_catalogo():
        token = request.form.get('_csrf_token') or request.form.get('csrf_token')
        if not validar_csrf(token):
            abort(403)
            
        catalogo_id = request.form.get('catalogo_id')
        if not _admin_puede_gestionar_catalogo(catalogo_id):
            flash('No tienes permisos para eliminar este catálogo o el ID es inválido.', 'danger')
            return redirect(url_for('admin', view='cursos'))
        
        from services.admin_service import eliminar_catalogo_accion
        resultado = eliminar_catalogo_accion(catalogo_id)
        if not resultado['ok']:
            flash(resultado['error'], 'danger')
        else:
            flash('Catálogo eliminado correctamente.', 'success')
            
        return redirect(url_for('admin', view='cursos'))

    @app.route('/admin/catalogo/editar', methods=['POST'])
    @admin_requerido
    def admin_editar_catalogo():
        token = request.form.get('_csrf_token') or request.form.get('csrf_token')
        if not validar_csrf(token):
            abort(403)

        catalogo_id = request.form.get('catalogo_id')
        nombre = request.form.get('nombre_curso')
        modalidad = request.form.get('modalidad')
        tipo_accion = request.form.get('tipo_accion')
        id_plantilla = request.form.get('id_plantilla_certificado')
        requisitos = request.form.get('requisitos', '')
        
        if not _admin_puede_gestionar_catalogo(catalogo_id):
            flash('No tienes permisos para editar este catálogo o el ID es inválido.', 'danger')
            return redirect(url_for('admin', view='cursos'))
            
        from services.admin_service import actualizar_catalogo_accion
        resultado = actualizar_catalogo_accion(catalogo_id, nombre, modalidad, tipo_accion, id_plantilla, requisitos)
        if not resultado['ok']:
            flash(resultado['error'], 'danger')
        else:
            flash('Catálogo actualizado correctamente.', 'success')
            
        return redirect(url_for('admin', view='cursos'))

    @app.route('/admin/sesion/generar_calendario', methods=['POST'])
    @admin_requerido
    def admin_generar_calendario_sesiones():
        es_ajax = _es_ajax()

        payload = request.get_json(silent=True) or {}
        csrf_token = payload.get('_csrf_token') or request.form.get('_csrf_token')
        if not validar_csrf(csrf_token):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        id_curso = (payload.get('id_curso') or '').strip().upper()
        catalogo_id = (payload.get('catalogo_id') or '').strip().upper()
        fecha_inicio = (payload.get('fecha_inicio') or '').strip()
        fecha_fin = (payload.get('fecha_fin') or '').strip()
        enlace_virtual = (payload.get('enlace_virtual') or '').strip()
        requisitos_cal = (payload.get('requisitos') or '').strip()
        calendario_academico_cal = (payload.get('calendario_academico') or '').strip()
        duracion_horas_cal_raw = payload.get('duracion_horas')
        try:
            duracion_horas_cal = int(duracion_horas_cal_raw) if duracion_horas_cal_raw not in (None, '') else None
        except (TypeError, ValueError):
            duracion_horas_cal = None
        bloques = payload.get('bloques') if isinstance(payload.get('bloques'), list) else []

        if not id_curso and not catalogo_id:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Edición o catálogo inválido.'}), 400
            return redireccion_admin_vista('ediciones')

        if id_curso:
            if not _admin_puede_gestionar_curso(id_curso):
                if es_ajax:
                    return jsonify({'ok': False, 'error': 'No autorizado'}), 403
                abort(403)
        else:
            if not _admin_puede_gestionar_catalogo(catalogo_id):
                if es_ajax:
                    return jsonify({'ok': False, 'error': 'No autorizado'}), 403
                abort(403)

        if not catalogo_id and id_curso:
            catalogo_id = obtener_catalogo_id_por_edicion(id_curso)
        if not catalogo_id:
            payload_error = {'ok': False, 'error': 'No se pudo identificar el catálogo.'}
            if es_ajax:
                return jsonify(payload_error), 400
            flash(payload_error['error'], 'danger')
            return redireccion_admin_vista('ediciones')

        id_plantilla_certificado = payload.get('id_plantilla_certificado')
        if id_plantilla_certificado:
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        'UPDATE catalogo_acciones SET id_plantilla_certificado = %s WHERE id = %s',
                        (id_plantilla_certificado, catalogo_id),
                    )
                conn.commit()
                conn.close()
            except Exception:
                pass

        if not fecha_inicio or not fecha_fin:
            payload_error = {'ok': False, 'error': 'Debes indicar fecha de inicio y fin.'}
            if es_ajax:
                return jsonify(payload_error), 400
            flash(payload_error['error'], 'danger')
            return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))

        detalle_curso = _obtener_detalle_curso(id_curso) if id_curso else None
        catalogo_detalle = _obtener_catalogo_detalle(catalogo_id) if not detalle_curso else None
        modalidad_curso = ''
        if detalle_curso:
            modalidad_curso = (detalle_curso['modalidad'] or '').strip()
        elif catalogo_detalle:
            modalidad_curso = (catalogo_detalle.get('modalidad') or '').strip()
        if modalidad_curso not in ('Virtual', 'B-Learning'):
            enlace_virtual = None
        elif enlace_virtual and not validar_enlace_virtual(enlace_virtual):
            payload_error = {'ok': False, 'error': 'Debes ingresar un enlace valido para modalidad virtual.'}
            if es_ajax:
                return jsonify(payload_error), 400
            flash(payload_error['error'], 'danger')
            if id_curso:
                return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))
            return redireccion_admin_vista('ediciones')

        if not bloques:
            payload_error = {'ok': False, 'error': 'Debes agregar al menos una jornada.'}
            if es_ajax:
                return jsonify(payload_error), 400
            flash(payload_error['error'], 'danger')
            if id_curso:
                return redirect(url_for('admin_gestion_sesiones', id_curso=id_curso))
            return redireccion_admin_vista('ediciones')

        sesiones_creadas_total = 0
        ediciones_creadas = 0
        ediciones_creadas_ids = []

        for bloque in bloques:
            if not isinstance(bloque, dict):
                return jsonify({'ok': False, 'error': 'Formato de jornada invalido.'}), 400
            dias_semana = bloque.get('dias_semana') or []
            modo_configuracion = (bloque.get('modo_configuracion') or 'auto').strip().lower()
            if modo_configuracion not in {'auto', 'manual'}:
                modo_configuracion = 'auto'
            fechas_manual = bloque.get('fechas_manual') if isinstance(bloque.get('fechas_manual'), list) else []
            hora_inicio = (bloque.get('hora_inicio') or '').strip()
            hora_fin = (bloque.get('hora_fin') or '').strip()
            jornada = (bloque.get('jornada') or 'UNICA').strip().upper()
            docente_responsable = (bloque.get('docente_responsable') or '').strip()
            persona_apoyo = (bloque.get('persona_apoyo') or '').strip()
            etiqueta_edicion = (bloque.get('etiqueta_edicion') or '').strip()
            privacidad = (bloque.get('privacidad') or '').strip().title()
            estado = _normalizar_estado_edicion(bloque.get('estado'))
            fecha_limite_raw = (bloque.get('fecha_limite_matricula') or '').strip()
            periodo = (bloque.get('periodo') or '').strip().upper()
            cupos_raw = (bloque.get('cupos_maximos') or '').strip()
            edicion_id = (bloque.get('edicion_id') or '').strip().upper()
            req_bloque = (bloque.get('requisitos') or requisitos_cal or '').strip()
            dur_raw = bloque.get('duracion_horas')
            try:
                dur_horas = int(dur_raw) if dur_raw not in (None, '') else duracion_horas_cal
            except (TypeError, ValueError):
                dur_horas = duracion_horas_cal

            if periodo not in {'I PAC', 'II PAC', 'III PAC', 'I SEMESTRE', 'II SEMESTRE'}:
                return jsonify({'ok': False, 'error': 'Selecciona un periodo valido.'}), 400

            try:
                cupos_maximos = int(cupos_raw)
            except (TypeError, ValueError):
                cupos_maximos = None
            if cupos_maximos is None or cupos_maximos < 0:
                return jsonify({'ok': False, 'error': 'Ingresa un cupo maximo valido.'}), 400

            if privacidad not in {'Abierta', 'Cerrada'}:
                return jsonify({'ok': False, 'error': 'Selecciona una privacidad valida.'}), 400

            if not etiqueta_edicion or not docente_responsable:
                return jsonify({'ok': False, 'error': 'Etiqueta y docente son obligatorios.'}), 400

            fecha_limite_matricula = ''
            if fecha_limite_raw:
                fecha_limite_matricula = fecha_limite_raw.replace('T', ' ')
                if len(fecha_limite_matricula) == 16:
                    fecha_limite_matricula = f"{fecha_limite_matricula}:00"
                try:
                    datetime.fromisoformat(fecha_limite_matricula)
                except ValueError:
                    return jsonify({'ok': False, 'error': 'Fecha limite invalida.'}), 400

            if not hora_inicio or not hora_fin:
                return jsonify({'ok': False, 'error': 'Completa horas para cada jornada.'}), 400

            if modo_configuracion == 'manual':
                if not fechas_manual:
                    return jsonify({'ok': False, 'error': 'Selecciona fechas manuales para la jornada.'}), 400
            else:
                if not dias_semana:
                    return jsonify({'ok': False, 'error': 'Completa dias y horas para cada jornada.'}), 400

            hora_texto = f"{hora_inicio}-{hora_fin}"

            if not edicion_id:
                nuevo_result = crear_edicion_formativa(
                    catalogo_id,
                    periodo=periodo,
                    fecha_inicio=fecha_inicio,
                    fecha_limite_matricula=fecha_limite_matricula or None,
                    jornada=jornada,
                    hora=hora_texto,
                    cupos_maximos=cupos_maximos,
                    enlace_acceso=enlace_virtual,
                    docente_responsable=docente_responsable,
                    persona_apoyo=persona_apoyo,
                    privacidad=privacidad,
                    estado=estado,
                    etiqueta_edicion=etiqueta_edicion,
                    requisitos=req_bloque,
                    duracion_horas=dur_horas,
                    calendario_academico=calendario_academico_cal,
                )
                if not nuevo_result.get('ok'):
                    return jsonify({'ok': False, 'error': 'No se pudo crear la edicion.'}), 400
                edicion_id = nuevo_result.get('edicion_id')
                ediciones_creadas += 1
                if edicion_id:
                    ediciones_creadas_ids.append(edicion_id)
            else:
                update_result = update_edicion_metadata(
                    edicion_id,
                    periodo=periodo,
                    fecha_inicio=fecha_inicio,
                    cupos_maximos=cupos_maximos,
                    jornada=jornada,
                    hora=hora_texto,
                    docente_responsable=docente_responsable,
                    persona_apoyo=persona_apoyo,
                    etiqueta_edicion=etiqueta_edicion,
                    privacidad=privacidad,
                    estado=estado,
                    fecha_limite_matricula=fecha_limite_matricula,
                    enlace_acceso=enlace_virtual,
                    requisitos=req_bloque,
                    duracion_horas=dur_horas,
                    calendario_academico=calendario_academico_cal,
                )
                if not update_result.get('ok'):
                    return jsonify({'ok': False, 'error': 'No se pudo actualizar la edicion.'}), 400

            result = generar_calendario_base(
                edicion_id,
                fecha_inicio,
                fecha_fin,
                dias_semana,
                [{'hora_inicio': hora_inicio, 'hora_fin': hora_fin}],
                jornada=jornada,
                fechas_manual=fechas_manual,
            )
            if not result.get('ok'):
                return jsonify({'ok': False, 'error': result.get('error') or 'No se pudo generar el calendario.'}), 400

            sesiones_creadas_total += int(result.get('sesiones_creadas', 0) or 0)

    

        redirect_target = id_curso or (ediciones_creadas_ids[0] if ediciones_creadas_ids else '')

        redirect_url = (
            url_for('admin_gestion_sesiones', id_curso=redirect_target)
            if redirect_target
            else url_for('admin', view='ediciones')
        )

        response_payload = {
            'ok': True,
            'sesiones_creadas': sesiones_creadas_total,
            'ediciones_creadas': ediciones_creadas,
            'ediciones_creadas_ids': ediciones_creadas_ids,
            'redirect_url': redirect_url,
        }
        if es_ajax:
            return jsonify(response_payload), 200

        flash(
            f"Calendario generado: {sesiones_creadas_total} sesion(es) en {len(bloques)} jornada(s).",
            'success',
        )
        return redirect(redirect_url)

    @app.route('/admin/ediciones/<edicion_id>/eliminar', methods=['POST'])
    @admin_requerido
    def admin_eliminar_edicion(edicion_id):
        token = request.form.get('_csrf_token') or request.json.get('_csrf_token') if request.is_json else request.form.get('_csrf_token')
        if not validar_csrf(token):
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        edicion_id = (edicion_id or '').strip().upper()
        if not edicion_id:
            return jsonify({'ok': False, 'error': 'ID de edición inválido.'}), 400

        if not _admin_puede_gestionar_curso(edicion_id):
            return jsonify({'ok': False, 'error': 'No autorizado.'}), 403

        try:
            conn = get_db_connection()
            # Cascade manually: asistencias → sesiones → matrículas → edición
            with conn.cursor() as cur:
                cur.execute('SELECT id_sesion FROM sesiones_curso WHERE edicion_id = %s', (edicion_id,))
                sesiones = cur.fetchall()
                for s in sesiones:
                    cur.execute('DELETE FROM asistencias WHERE id_sesion = %s', (s['id_sesion'],))
                cur.execute('DELETE FROM sesiones_curso WHERE edicion_id = %s', (edicion_id,))
                cur.execute('DELETE FROM matriculas WHERE edicion_id = %s', (edicion_id,))
                cur.execute('DELETE FROM ediciones_formativas WHERE id = %s', (edicion_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'ok': True})
        flash('Edición eliminada correctamente.', 'success')
        return redireccion_admin_vista('ediciones')

    @app.route('/admin/ediciones/<edicion_id>/editar', methods=['POST'])
    @admin_requerido
    def admin_editar_edicion(edicion_id):
        es_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in (request.headers.get('Accept') or '')
        )
        payload = request.get_json(silent=True) or {}
        token = payload.get('_csrf_token') or request.form.get('_csrf_token')
        if not validar_csrf(token):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        edicion_id = (edicion_id or '').strip().upper()
        if not edicion_id:
            return jsonify({'ok': False, 'error': 'ID de edición inválido.'}), 400

        if not _admin_puede_gestionar_curso(edicion_id):
            return jsonify({'ok': False, 'error': 'No autorizado.'}), 403

        def _get(key, form_fallback=None):
            return payload.get(key) if payload else request.form.get(form_fallback or key)

        etiqueta = (_get('etiqueta_edicion') or '').strip()
        docente = (_get('docente_responsable') or '').strip()
        calendario = (_get('calendario_academico') or '').strip()
        periodo = (_get('periodo') or '').strip().upper()
        jornada = (_get('jornada') or '').strip().upper()
        hora = (_get('hora') or '').strip()
        cupos_raw = _get('cupos_maximos')
        privacidad = (_get('privacidad') or '').strip().title()
        enlace = (_get('enlace_acceso') or '').strip() or None
        fecha_limite_raw = (_get('fecha_limite_matricula') or '').strip()
        requisitos = (_get('requisitos') or '').strip()
        dur_raw = _get('duracion_horas')

        try:
            cupos = int(cupos_raw) if cupos_raw not in (None, '') else None
        except (TypeError, ValueError):
            cupos = None

        try:
            dur_horas = int(dur_raw) if dur_raw not in (None, '') else None
        except (TypeError, ValueError):
            dur_horas = None

        fecha_limite = ''
        if fecha_limite_raw:
            fecha_limite = fecha_limite_raw.replace('T', ' ')
            if len(fecha_limite) == 16:
                fecha_limite = f"{fecha_limite}:00"

        result = update_edicion_metadata(
            edicion_id,
            periodo=periodo or None,
            cupos_maximos=cupos,
            jornada=jornada or None,
            hora=hora or None,
            docente_responsable=docente or None,
            etiqueta_edicion=etiqueta or None,
            privacidad=privacidad or None,
            fecha_limite_matricula=fecha_limite or None,
            enlace_acceso=enlace,
            requisitos=requisitos,
            duracion_horas=dur_horas,
            calendario_academico=calendario or None,
        )

        if not result.get('ok'):
            msg = 'Edición no encontrada.' if result.get('not_found') else 'No se pudo actualizar la edición.'
            if es_ajax:
                return jsonify({'ok': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redireccion_admin_vista('ediciones')

        if es_ajax:
            return jsonify({'ok': True})
        flash('Edición actualizada correctamente.', 'success')
        return redireccion_admin_vista('ediciones')

    @app.route('/admin/ediciones/grupo_cerrado/centros', methods=['GET'])
    @admin_requerido
    def admin_api_centros_regionales():
        """Retorna la lista de centros regionales. Si se pasa ?centro=X, devuelve el total de docentes."""
        try:
            from services.grupo_cerrado_service import obtener_centros_regionales, obtener_docentes_por_centro
            conn = get_db_connection()
            centro_filtro = request.args.get('centro', '').strip()
            if centro_filtro:
                docentes = obtener_docentes_por_centro(conn, centro_filtro)
                conn.close()
                return jsonify({'ok': True, 'total': len(docentes)})
            centros = obtener_centros_regionales(conn)
            conn.close()
            return jsonify({'ok': True, 'centros': centros})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)})


    @app.route('/admin/ediciones/<edicion_id>/grupo_cerrado/procesar', methods=['POST'])
    @admin_requerido
    def admin_procesar_grupo_cerrado(edicion_id):
        edicion_id = (edicion_id or '').strip().upper()
        if not edicion_id or not _admin_puede_gestionar_curso(edicion_id):
            return jsonify({'ok': False, 'error': 'No autorizado.'}), 403
            
        token = request.form.get('_csrf_token')
        if not validar_csrf(token):
            return jsonify({'ok': False, 'error': 'Token inválido.'}), 403

        accion = request.form.get('accion')
        metodo = request.form.get('metodo') # 'excel', 'manual', 'centro'
        
        if accion not in ['automatica', 'invitacion']:
            return jsonify({'ok': False, 'error': 'Acción inválida.'}), 400
            
        from services.grupo_cerrado_service import (
            procesar_archivo_excel, validar_docentes, obtener_docentes_por_centro, ejecutar_accion_grupo_cerrado
        )
        
        conn = get_db_connection()
        lista_numeros = []
        
        try:
            if metodo == 'excel':
                archivo = request.files.get('archivo_excel')
                if not archivo or not archivo.filename.endswith(('.xlsx', '.xls')):
                    return jsonify({'ok': False, 'error': 'Sube un archivo Excel válido.'}), 400
                lista_numeros = procesar_archivo_excel(archivo)
                
            elif metodo == 'manual':
                numeros_raw = request.form.get('numeros_empleado', '')
                lista_numeros = [n.strip() for n in numeros_raw.split(',') if n.strip()]
                
            elif metodo == 'centro':
                centro = request.form.get('centro_regional', '')
                if not centro:
                    return jsonify({'ok': False, 'error': 'Selecciona un centro.'}), 400
                docentes_centro = obtener_docentes_por_centro(conn, centro)
                lista_numeros = [d['numero_empleado'] for d in docentes_centro]
            else:
                return jsonify({'ok': False, 'error': 'Método inválido.'}), 400
                
            docentes_validos = validar_docentes(conn, lista_numeros)
            if not docentes_validos:
                return jsonify({'ok': False, 'error': 'No se encontraron docentes válidos en la lista enviada.'}), 400
                
            nums_validos = [d['numero_empleado'] for d in docentes_validos]
            insertados, ignorados = ejecutar_accion_grupo_cerrado(conn, edicion_id, accion, nums_validos)
            
            return jsonify({
                'ok': True, 
                'mensaje': f'Se procesaron {len(nums_validos)} docentes. {insertados} nuevos, {ignorados} ya estaban asignados.',
                'insertados': insertados,
                'ignorados': ignorados
            })
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            conn.close()

    @app.route('/admin/curso/<id_curso>/asistencias')
    @admin_requerido
    def admin_gestion_asistencias(id_curso):
        id_curso = (id_curso or '').strip().upper()
        if not id_curso:
            return redireccion_admin_vista('ediciones')

        if not _admin_puede_gestionar_curso(id_curso):
            abort(403)

        vista_solicitada = request.args.get('view', 'ediciones').strip().lower()
        anio_filtro = request.args.get('anio', '').strip()
        periodo_filtro = request.args.get('periodo', '').strip()
        mes_filtro = request.args.get('mes', '').strip()
        resultado_filtro = request.args.get('resultado', '').strip().lower()
        admin_rol = session.get('admin_rol', 'admin')

        dashboard_payload = get_admin_dashboard_payload(
            vista_solicitada,
            anio_filtro,
            periodo_filtro,
            mes_filtro,
            resultado_filtro,
            admin_rol,
            session.get('admin_direccion', 'IPSD'),
        )

        reporte = obtener_reporte_asistencia_curso(id_curso)
        if not reporte.get('ok'):
            return redireccion_admin_vista('ediciones')

        centros_regionales = _obtener_centros_regionales_admin()

        return render_template(
            'admin.html',
            registros=dashboard_payload['registros'],
            cursos=dashboard_payload['cursos'],
            catalogos=dashboard_payload['catalogos'],
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
            vista_inicial=vista_solicitada,
            fecha_hoy=datetime.now().strftime('%Y-%m-%d'),
            horarios_base=HORARIOS_BASE,
            curso_asistencias_id=id_curso,
            curso_asistencia_reporte=reporte,
            centros_regionales=centros_regionales,
        )

    @app.route('/admin/sesion/crear', methods=['POST'])
    @admin_requerido
    def admin_crear_sesion():
        es_ajax = _es_ajax()

        if not validar_csrf(request.form.get('_csrf_token')):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403
            abort(403)

        id_curso = (request.form.get('edicion_id') or request.form.get('id_curso') or '').strip().upper()
        fecha = request.form.get('fecha', '').strip()
        hora_inicio = request.form.get('hora_inicio', '').strip()
        hora_fin = request.form.get('hora_fin', '').strip()
        jornada = request.form.get('jornada', 'UNICA').strip().upper()
        docente_sesion = request.form.get('docente_sesion', '').strip()
        edicion = request.form.get('edicion', '').strip().upper()

        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Curso inválido'}), 400
            flash('ID de edición/curso inválido.', 'danger')
            return redireccion_admin_vista('ediciones')

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
            edicion=edicion,
        )
        if result.get('ok'):
            _sincronizar_fechas_capacitacion_desde_sesiones(id_curso, fecha, fecha)
            if not es_ajax:
                flash('Sesión creada correctamente.', 'success')
        else:
            if not es_ajax:
                flash(result.get('error', 'No se pudo crear la sesión.'), 'danger')

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
        edicion = request.form.get('edicion', '').strip().upper()
        id_curso_form = (request.form.get('edicion_id') or request.form.get('id_curso') or '').strip().upper()

        id_curso = id_curso_form or _obtener_curso_de_sesion(id_sesion)
        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión inválida'}), 400
            flash('ID de edición/curso inválido.', 'danger')
            return redireccion_admin_vista('ediciones')

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
            edicion=edicion,
        )
        if result.get('ok'):
            _sincronizar_fechas_capacitacion_desde_sesiones(id_curso)
            if not es_ajax:
                flash('Sesión actualizada correctamente.', 'success')
        else:
            if not es_ajax:
                flash(result.get('error', 'No se pudo actualizar la sesión.'), 'danger')

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
        id_curso_form = (request.form.get('edicion_id') or request.form.get('id_curso') or '').strip().upper()

        id_curso = id_curso_form or _obtener_curso_de_sesion(id_sesion)
        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión inválida'}), 400
            flash('ID de edición/curso inválido.', 'danger')
            return redireccion_admin_vista('ediciones')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = eliminar_sesion(id_sesion)
        if result.get('ok'):
            _sincronizar_fechas_capacitacion_desde_sesiones(id_curso)
            if not es_ajax:
                flash('Sesión eliminada correctamente.', 'success')
        else:
            if not es_ajax:
                flash(result.get('error', 'No se pudo eliminar la sesión.'), 'danger')

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
        id_curso_form = (request.form.get('edicion_id') or request.form.get('id_curso') or '').strip().upper()

        id_curso = id_curso_form or _obtener_curso_de_sesion(id_sesion)
        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión inválida'}), 400
            flash('ID de edición/curso inválido.', 'danger')
            return redireccion_admin_vista('ediciones')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = abrir_asistencia_sesion(id_sesion)
        if result.get('ok'):
            if not es_ajax:
                flash('Registro de asistencia abierto (Token generado).', 'success')
        else:
            if not es_ajax:
                flash(result.get('error', 'No se pudo abrir el registro de asistencia.'), 'danger')

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
        id_curso_form = (request.form.get('edicion_id') or request.form.get('id_curso') or '').strip().upper()

        id_curso = id_curso_form or _obtener_curso_de_sesion(id_sesion)
        if not id_curso:
            if es_ajax:
                return jsonify({'ok': False, 'error': 'Sesión inválida'}), 400
            flash('ID de edición/curso inválido.', 'danger')
            return redireccion_admin_vista('ediciones')

        if not _admin_puede_gestionar_curso(id_curso):
            if es_ajax:
                return jsonify({'ok': False, 'error': 'No autorizado'}), 403
            abort(403)

        result = cerrar_asistencia_sesion(id_sesion)
        if result.get('ok'):
            if not es_ajax:
                flash('Registro de asistencia cerrado.', 'success')
        else:
            if not es_ajax:
                flash(result.get('error', 'No se pudo cerrar el registro de asistencia.'), 'danger')

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
        tipo_accion = request.form.get('tipo_accion', 'CURSO').strip().upper()
        modalidad = request.form.get('modalidad', '').strip()
        id_plantilla_certificado = (request.form.get('id_plantilla_certificado') or '').strip()
        if not id_plantilla_certificado:
            id_plantilla_certificado = None
        elif not id_plantilla_certificado.isdigit():
            id_plantilla_certificado = None
        else:
            id_plantilla_certificado = int(id_plantilla_certificado)
        es_superadmin = session.get('admin_rol') == 'superadmin'

        if tipo_accion not in {'CONFERENCIA', 'SEMINARIO', 'SEMINARIO-TALLER', 'CURSO'}:
            tipo_accion = 'CURSO'

        if es_superadmin:
            direccion_curso = normalizar_direccion(request.form.get('direccion_curso', ''))
        else:
            direccion_curso = normalizar_direccion(session.get('admin_direccion', 'IPSD'))

        if (
            not nombre_curso
            or not direccion_curso
            or modalidad not in ['Virtual', 'Presencial', 'B-Learning']
        ):
            flash('Completa correctamente los campos obligatorios para crear la acción formativa.', 'danger')
            return redireccion_admin_vista('cursos')

        try:
            create_result = create_curso_records(
                nombre_curso=nombre_curso,
                modalidad=modalidad,
                tipo_accion=tipo_accion,
                direccion_curso=direccion_curso,
                id_plantilla_certificado=id_plantilla_certificado,
            )
        except Exception as e:
            print(f"Error al crear: {e}")
            flash('No se pudo crear la acción formativa. Intenta nuevamente.', 'danger')
            return redireccion_admin_vista('cursos')
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

        id_curso = (request.form.get('edicion_id') or request.form.get('id_curso') or '').strip()
        nombre_curso = request.form.get('nombre_curso', '').strip()
        fecha_curso = request.form.get('fecha_curso', '').strip()
        periodo = request.form.get('periodo', '').strip()
        tipo_accion = request.form.get('tipo_accion', 'CURSO').strip().upper()
        horas_totales_raw = request.form.get('horas_totales', '').strip()
        semanas_duracion_raw = request.form.get('semanas_duracion', '').strip()
        modalidad = request.form.get('modalidad', '').strip()
        enlace_virtual = request.form.get('enlace_virtual', '').strip()
        cupos_maximos_raw = request.form.get('cupos_maximos', '').strip()
        id_plantilla_certificado = (request.form.get('id_plantilla_certificado') or '').strip()
        if not id_plantilla_certificado:
            id_plantilla_certificado = None
        elif not id_plantilla_certificado.isdigit():
            id_plantilla_certificado = None
        else:
            id_plantilla_certificado = int(id_plantilla_certificado)

        if tipo_accion not in {'CONFERENCIA', 'SEMINARIO', 'SEMINARIO-TALLER', 'CURSO'}:
            tipo_accion = 'CURSO'

        if not id_curso or not nombre_curso or periodo not in ['I', 'II', 'III', 'IV']:
            flash('Datos de catálogo/acción formativa inválidos o incompletos.', 'danger')
            return redireccion_admin_vista('cursos')

        fecha_obj = _parse_fecha_form(fecha_curso)
        if not fecha_obj:
            flash('Fecha inválida.', 'danger')
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

        if modalidad not in ['Virtual', 'Presencial', 'B-Learning'] or cupos_maximos < 0 or horas_totales < 1 or semanas_duracion < 1:
            flash('Completa correctamente todos los campos obligatorios del catálogo/acción formativa.', 'danger')
            return redireccion_admin_vista('cursos')

        if modalidad == 'Virtual':
            if not enlace_virtual or not validar_enlace_virtual(enlace_virtual):
                flash('El enlace virtual no es válido.', 'danger')
                return redireccion_admin_vista('cursos')
        else:
            enlace_virtual = None

        admin_rol = session.get('admin_rol', 'admin')
        if admin_rol != 'superadmin' and not _admin_puede_gestionar_curso(id_curso):
            abort(403)

        anio = str(fecha_obj.year)
        mes = MESES_ES[fecha_obj.month - 1]
        dia = str(fecha_obj.day)
        dia_semana = DIAS_SEMANA[fecha_obj.weekday()]

        update_result = update_curso_record(
            id_curso=id_curso,
            nombre_curso=nombre_curso,
            anio=anio,
            periodo=periodo,
            mes=mes,
            dia=dia,
            modalidad=modalidad,
            tipo_accion=tipo_accion,
            horas_totales=horas_totales,
            semanas_duracion=semanas_duracion,
            cupos_maximos=cupos_maximos,
            enlace_virtual=enlace_virtual,
            dia_semana=dia_semana,
            id_plantilla_certificado=id_plantilla_certificado,
        )
        if not update_result['ok']:
            flash('No se pudo actualizar el catálogo/acción formativa.', 'danger')
            return redireccion_admin_vista('cursos')

        flash('Catálogo/acción formativa actualizado correctamente.', 'success')
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
            flash('Datos de usuario administrador inválidos o contraseña menor a 8 caracteres.', 'danger')
            return redireccion_admin_vista('usuarios')

        create_admin_user_record(username, password, direccion)
        flash('Usuario administrador creado correctamente.', 'success')

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
            flash('Datos de actualización incompletos.', 'danger')
            return redireccion_admin_vista('usuarios')

        if new_password and len(new_password) < 8:
            flash('La nueva contraseña debe tener al menos 8 caracteres.', 'danger')
            return redireccion_admin_vista('usuarios')

        update_admin_user_record(username, new_password, direccion)
        flash('Usuario administrador actualizado correctamente.', 'success')

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/eliminar_admin', methods=['POST'])
    @superadmin_requerido
    def eliminar_admin_usuario():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        username = request.form.get('username', '').strip()
        if not username:
            flash('Usuario inválido para eliminar.', 'danger')
            return redireccion_admin_vista('usuarios')

        delete_admin_user_record(username)
        flash('Usuario administrador eliminado correctamente.', 'success')

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/crear_direccion', methods=['POST'])
    @superadmin_requerido
    def crear_direccion():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        codigo = normalizar_direccion(request.form.get('codigo', '').strip())
        nombre = request.form.get('nombre', '').strip()

        if not codigo or codigo == 'GLOBAL' or not validar_nombre_direccion(nombre):
            flash('Completa correctamente los campos de la dirección.', 'danger')
            return redireccion_admin_vista('usuarios')

        resultado = create_direccion_record(codigo, nombre)
        if not resultado.get('ok'):
            flash('No se pudo crear la dirección. Verifica si ya existe o intenta nuevamente.', 'danger')
            return redireccion_admin_vista('usuarios')

        flash('Dirección creada correctamente.', 'success')

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
            flash('Datos de dirección inválidos o incompletos.', 'danger')
            return redireccion_admin_vista('usuarios')

        update_direccion_record(codigo_actual, codigo_nuevo, nombre_nuevo)
        flash('Dirección actualizada correctamente.', 'success')

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/eliminar_direccion', methods=['POST'])
    @superadmin_requerido
    def eliminar_direccion():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        codigo = normalizar_direccion(request.form.get('codigo', '').strip())
        if not codigo or codigo == 'GLOBAL':
            flash('Dirección inválida para eliminar.', 'danger')
            return redireccion_admin_vista('usuarios')

        delete_direccion_record(codigo)
        flash('Dirección eliminada correctamente.', 'success')

        return redireccion_admin_vista('usuarios')

    @app.route('/admin/eliminar_curso', methods=['POST'])
    @admin_requerido
    def eliminar_curso():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        id_curso = (request.form.get('edicion_id') or request.form.get('id_curso') or '').strip()
        if not id_curso:
            flash('ID de catálogo/acción formativa inválido.', 'danger')
            return redireccion_admin_vista('cursos')

        admin_rol = session.get('admin_rol', 'admin')
        if admin_rol != 'superadmin' and not _admin_puede_gestionar_curso(id_curso):
            abort(403)

        delete_curso_record(id_curso)
        flash('Catálogo/acción formativa eliminado correctamente.', 'success')

        return redireccion_admin_vista('cursos')

    @app.route('/admin/eliminar_matricula', methods=['POST'])
    @admin_requerido
    def admin_eliminar_matricula():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        vista_target = request.form.get('view', 'matriculas').strip().lower()
        numero_empleado = request.form.get('numero_empleado', '').strip()
        edicion_id = (request.form.get('edicion_id') or '').strip()
        matricula_id_raw = request.form.get('matricula_id', '').strip()

        matricula_id = int(matricula_id_raw) if matricula_id_raw.isdigit() else None

        if not numero_empleado or not edicion_id:
            flash('Datos de matrícula/inscripción inválidos.', 'danger')
            return redireccion_admin_vista(vista_target)

        admin_rol = session.get('admin_rol', 'admin')
        admin_direccion = normalizar_direccion(session.get('admin_direccion', 'IPSD')) or 'IPSD'

        if admin_rol != 'superadmin' and not _admin_puede_gestionar_curso(edicion_id):
            abort(403)

        delete_matricula_record(numero_empleado, edicion_id, matricula_id)
        flash('Matrícula/Inscripción eliminada correctamente.', 'success')

        return redireccion_admin_vista(vista_target)

    @app.route('/admin/matriculas/<int:matricula_id>/evaluar', methods=['PUT'])
    @admin_requerido
    def admin_evaluar_matricula(matricula_id):
        payload = request.get_json(silent=True)
        data = payload if isinstance(payload, dict) else {}
        if not data:
            data = request.form

        token = (
            request.headers.get('X-CSRF-Token')
            or request.headers.get('X-CSRFToken')
            or data.get('_csrf_token')
            or data.get('csrf_token')
        )
        if not validar_csrf(token):
            return jsonify({'ok': False, 'error': 'Sesión expirada. Recarga la página.'}), 403

        numero_empleado = (data.get('numero_empleado') or '').strip()
        edicion_id = (data.get('edicion_id') or '').strip()
        aprobado_raw = data.get('aprobado')
        comentario_validacion = (data.get('comentario_validacion') or '').strip()

        if not numero_empleado or not edicion_id or not matricula_id:
            return jsonify({'ok': False, 'error': 'Datos incompletos'}), 400

        if aprobado_raw is None or str(aprobado_raw).strip() == '':
            aprobado = None
            resultado_texto = 'Pendiente'
            estado_codigo = 'PENDIENTE'
        else:
            aprobado_raw = str(aprobado_raw).strip()
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
            else:
                return jsonify({'ok': False, 'error': 'Resultado inválido'}), 400

        update_result = update_matricula_resultado(
            numero_empleado=numero_empleado,
            edicion_id=edicion_id,
            matricula_id=matricula_id,
            aprobado=aprobado,
            estado_codigo=estado_codigo,
            admin_rol=session.get('admin_rol', 'admin'),
            admin_direccion=session.get('admin_direccion', 'IPSD'),
            comentario_validacion=comentario_validacion,
        )

        if not update_result['ok']:
            return jsonify({'ok': False, 'error': update_result['error']}), update_result['status_code']

        return jsonify({'ok': True, 'resultado': resultado_texto})

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
        edicion_id = (request.form.get('edicion_id') or '').strip()
        matricula_id_raw = request.form.get('matricula_id', '').strip()
        aprobado_raw = request.form.get('aprobado', '').strip()

        matricula_id = int(matricula_id_raw) if matricula_id_raw.isdigit() else None

        if not numero_empleado or not edicion_id or not matricula_id:
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
            flash('Resultado de matrícula inválido.', 'danger')
            return redireccion_admin_vista('matriculas')

        update_result = update_matricula_resultado(
            numero_empleado=numero_empleado,
            edicion_id=edicion_id,
            matricula_id=matricula_id,
            aprobado=aprobado,
            estado_codigo=estado_codigo,
            admin_rol=session.get('admin_rol', 'admin'),
            admin_direccion=session.get('admin_direccion', 'IPSD'),
            comentario_validacion=None,
        )

        if not update_result['ok']:
            if es_ajax:
                return jsonify({'ok': False, 'error': update_result['error']}), update_result['status_code']
            if update_result['status_code'] == 403:
                abort(403)
            flash(update_result.get('error', 'No se pudo actualizar el resultado.'), 'danger')
            return redireccion_admin_vista('matriculas')

        if es_ajax:
            return jsonify({'ok': True, 'resultado': resultado_texto})

        flash('Resultado de matrícula actualizado correctamente.', 'success')
        return redireccion_admin_vista('matriculas')

    @app.route('/admin/vaciar_matriculas', methods=['POST'])
    @superadmin_requerido
    def admin_vaciar_matriculas():
        if not validar_csrf(request.form.get('_csrf_token')):
            abort(403)

        confirmacion = request.form.get('confirmacion', '')
        if confirmacion != 'ELIMINAR':
            flash('Confirmación de seguridad inválida. No se eliminó nada.', 'danger')
            return redireccion_admin_vista('matriculas')

        vaciar_matriculas_records()
        flash('Todas las inscripciones y matrículas han sido eliminadas correctamente.', 'success')

        return redireccion_admin_vista('matriculas')

    @app.route('/exportar')
    @admin_requerido
    def exportar_csv():
        anio_filtro = request.args.get('anio', '').strip()
        periodo_filtro = request.args.get('periodo', '').strip()
        mes_filtro = request.args.get('mes', '').strip()
        resultado_filtro = request.args.get('resultado', '').strip().lower()

        export_result = fetch_export_records(
            anio_filtro,
            periodo_filtro,
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
                'ID Edicion',
                'Nombre de la Accion',
                'Anio',
                'Periodo',
                'Mes',
                'Horario',
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

            jornada = (fila.get('jornada') or '').strip()
            hora = (fila.get('hora') or '').strip()
            horario = f"{jornada} {hora}".strip()

            cw.writerow(
                [
                    fila['numero_empleado'],
                    fila['edicion_id'],
                    fila['nombre'],
                    fila['anio'],
                    fila['periodo'],
                    fila.get('mes') or '',
                    horario,
                    fila['fecha_matricula'] or '',
                    resultado,
                ]
            )

        output = Response(si.getvalue(), mimetype='text/csv; charset=utf-8')
        nombre_archivo = (
            'listado_matriculas_filtrado.csv'
            if (anio_filtro or periodo_filtro or mes_filtro)
            else 'listado_matriculas_general.csv'
        )
        output.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
        return output

    # ── Rutas: Sistema de Clicks de Atención (CONFERENCIA) ─────────────────

    @app.route('/admin/sesion/<int:id_sesion>/ventanas', methods=['GET'])
    @admin_requerido
    def admin_get_ventanas(id_sesion):
        """Obtiene la configuración actual de ventanas de una sesión de conferencia."""
        from services.clicks_asistencia import get_config_ventanas
        conn = get_db_connection()
        try:
            result = get_config_ventanas(conn, id_sesion)
            status = 200 if result.get('ok') else result.get('status_code', 400)
            return jsonify(result), status
        finally:
            conn.close()

    @app.route('/admin/sesion/<int:id_sesion>/ventanas', methods=['POST'])
    @admin_requerido
    def admin_guardar_ventanas(id_sesion):
        """Guarda la configuración de ventanas de atención (admin)."""
        if not validar_csrf(request.form.get('_csrf_token') or (request.get_json(silent=True) or {}).get('_csrf_token')):
            return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403

        payload = request.get_json(silent=True) or {}
        ventanas_raw = payload.get('ventanas') or request.form.getlist('ventanas[]')

        try:
            ventanas = [str(v).strip() for v in ventanas_raw if str(v).strip()]
        except Exception:
            return jsonify({'ok': False, 'error': 'Formato de ventanas inválido.'}), 400

        # Verificar que el admin puede gestionar esta sesión
        id_curso = _obtener_curso_de_sesion(id_sesion)
        if not id_curso or not _admin_puede_gestionar_curso(id_curso):
            return jsonify({'ok': False, 'error': 'Sin permiso para esta sesión.'}), 403

        from services.clicks_asistencia import guardar_ventanas
        conn = get_db_connection()
        try:
            result = guardar_ventanas(conn, id_sesion, ventanas)
            status = 200 if result.get('ok') else 400
            return jsonify(result), status
        finally:
            conn.close()

    @app.route('/admin/sesion/<int:id_sesion>/forzar_ventana', methods=['POST'])
    @admin_requerido
    def admin_forzar_ventana(id_sesion):
        """Admin fuerza una ventana activa por 3 minutos (override para casos especiales)."""
        payload = request.get_json(silent=True) or {}
        csrf = payload.get('_csrf_token') or request.form.get('_csrf_token')
        if not validar_csrf(csrf):
            return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403

        ventana_idx_raw = payload.get('ventana_idx') or request.form.get('ventana_idx', '')
        try:
            ventana_idx = int(ventana_idx_raw)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'error': 'ventana_idx inválido.'}), 400

        id_curso = _obtener_curso_de_sesion(id_sesion)
        if not id_curso or not _admin_puede_gestionar_curso(id_curso):
            return jsonify({'ok': False, 'error': 'Sin permiso para esta sesión.'}), 403

        from services.clicks_asistencia import forzar_ventana
        conn = get_db_connection()
        try:
            result = forzar_ventana(conn, id_sesion, ventana_idx)
            status = 200 if result.get('ok') else 400
            return jsonify(result), status
        finally:
            conn.close()

    @app.route('/admin/sesion/<int:id_sesion>/progreso_clicks', methods=['GET'])
    @admin_requerido
    def admin_progreso_clicks(id_sesion):
        """Resumen del progreso de clics de todos los docentes en una sesión (vista admin)."""
        id_curso = _obtener_curso_de_sesion(id_sesion)
        if not id_curso or not _admin_puede_gestionar_curso(id_curso):
            return jsonify({'ok': False, 'error': 'Sin permiso.'}), 403

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT
                        ra.numero_empleado,
                        d.nombre_completo,
                        ra.ventanas_completadas,
                        ra.aprobado_automatico,
                        ra.fecha_marcado
                    FROM registro_asistencia ra
                    JOIN docentes d ON d.numero_empleado = ra.numero_empleado
                    WHERE ra.id_sesion = %s AND ra.tipo_registro = 'CONFERENCIA'
                    ORDER BY ra.aprobado_automatico DESC, array_length(ra.ventanas_completadas::jsonb::text::text[], 1) DESC NULLS LAST
                    ''',
                    (id_sesion,)
                )
                filas = cur.fetchall()

            import json as _json
            progreso = []
            for f in filas:
                vc = f['ventanas_completadas']
                completadas = _json.loads(vc) if isinstance(vc, str) else (vc or [])
                progreso.append({
                    'numero_empleado': f['numero_empleado'],
                    'nombre_completo': f['nombre_completo'],
                    'ventanas_completadas': completadas,
                    'total_completadas': len(completadas),
                    'aprobado_automatico': bool(f['aprobado_automatico']),
                    'fecha': str(f['fecha_marcado']),
                })

            return jsonify({'ok': True, 'progreso': progreso, 'total_docentes': len(progreso)})
        finally:
            conn.close()

    @app.route('/admin/enviar_mensaje', methods=['POST'])
    @admin_requerido
    def admin_enviar_mensaje():
        token = request.form.get('_csrf_token') or request.form.get('csrf_token')
        if not validar_csrf(token):
            return jsonify({'ok': False, 'error': 'Token de seguridad inválido.'}), 403

        numero_empleado = request.form.get('numero_empleado', '').strip()
        edicion_id = request.form.get('edicion_id', '').strip()
        asunto = request.form.get('asunto', '').strip()
        mensaje = request.form.get('mensaje', '').strip()
        es_bienvenida = str(request.form.get('es_bienvenida', '')).lower() in ('true', '1', 'on', 'yes')

        if not asunto or not mensaje:
            return jsonify({'ok': False, 'error': 'El asunto y el mensaje son obligatorios.'}), 400
        
        if not numero_empleado and not edicion_id:
            return jsonify({'ok': False, 'error': 'Debe especificar un empleado o una edición.'}), 400

        try:
            conn = get_db_connection()
            from services.email_service import enviar_mensaje_docente

            # Obtener datos de la edición para resolver tags
            contexto_edicion_base = {
                '{{nombre_accion}}': '[Nombre de la Acción]',
                '{{modalidad}}': '[Modalidad]',
                '{{duracion_horas}}': '[Horas]',
                '{{fecha_inicio}}': '[Fecha Inicio]',
                '{{fecha_fin}}': '[Fecha Fin]',
                '{{periodo}}': '[Periodo]',
                '{{enlace_acceso}}': '[Enlace]',
                '{{direccion}}': 'IPSD – UNAH',
            }
            if edicion_id:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT ef.fecha_inicio, ef.enlace_acceso, ef.periodo, ef.mensaje_bienvenida, ef.duracion_horas,
                               ca.nombre, ca.modalidad
                        FROM ediciones_formativas ef
                        JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                        WHERE ef.id = %s LIMIT 1
                    """, (edicion_id,))
                    ed_data = cur.fetchone()
                    if ed_data:
                        fi = ed_data['fecha_inicio']
                        fecha_str = fi.strftime('%d/%m/%Y') if hasattr(fi, 'strftime') else str(fi)[:10] if fi else 'N/D'
                        
                        # Get fecha_fin from sesiones
                        cur.execute('SELECT MAX(fecha) as fecha_fin FROM sesiones_curso WHERE edicion_id = %s', (edicion_id,))
                        ses = cur.fetchone()
                        fecha_fin_str = ''
                        if ses and ses['fecha_fin']:
                            ff = ses['fecha_fin']
                            fecha_fin_str = ff.strftime('%d/%m/%Y') if hasattr(ff, 'strftime') else str(ff)[:10]

                        contexto_edicion_base = {
                            '{{nombre_accion}}': ed_data['nombre'] or '',
                            '{{modalidad}}': ed_data['modalidad'] or '',
                            '{{duracion_horas}}': str(ed_data['duracion_horas']) if ed_data['duracion_horas'] else 'N/D',
                            '{{fecha_inicio}}': fecha_str,
                            '{{fecha_fin}}': fecha_fin_str or 'N/D',
                            '{{periodo}}': ed_data['periodo'] or '',
                            '{{enlace_acceso}}': ed_data['enlace_acceso'] or 'N/D',
                            '{{direccion}}': 'IPSD – UNAH',
                        }
            
            with conn.cursor() as cur:
                destinatarios = []
                if edicion_id:
                    cur.execute('''
                        SELECT d.numero_empleado, d.correo_institucional, d.nombre_completo 
                        FROM matriculas m
                        JOIN docentes d ON m.numero_empleado = d.numero_empleado
                        WHERE m.edicion_id = %s
                    ''', (edicion_id,))
                    destinatarios = cur.fetchall()
                    if not destinatarios and not es_bienvenida:
                        return jsonify({'ok': False, 'error': 'No hay docentes matriculados en esta edición.'}), 404
                    if es_bienvenida:
                        cur.execute('UPDATE ediciones_formativas SET mensaje_bienvenida = %s WHERE id = %s', (mensaje, edicion_id))
                else:
                    numeros = [n.strip() for n in numero_empleado.replace(',', ' ').split() if n.strip()]
                    if not numeros:
                        return jsonify({'ok': False, 'error': 'No se proporcionaron números de empleado válidos.'}), 400
                    
                    # Para evitar "docente no encontrado" y bloquear a todos, filtramos los que sí existen
                    placeholders = ','.join(['%s'] * len(numeros))
                    cur.execute(f'SELECT numero_empleado, correo_institucional, nombre_completo FROM docentes WHERE numero_empleado IN ({placeholders}) AND activo = 1', tuple(numeros))
                    destinatarios = cur.fetchall()
                    if not destinatarios:
                        return jsonify({'ok': False, 'error': 'Ningún docente encontrado con los números proporcionados.'}), 404

                enviados_correctamente = 0
                for dest in destinatarios:
                    correo_docente = dest['correo_institucional']
                    nombre_docente = dest['nombre_completo']
                    num_emp = dest['numero_empleado']
                    
                    contexto_tags = {**contexto_edicion_base, '{{nombre_docente}}': nombre_docente}

                    cur.execute(
                        '''
                        INSERT INTO mensajes_personalizados (numero_empleado, asunto, mensaje) 
                        VALUES (%s, %s, %s)
                        ''', (num_emp, asunto, mensaje)
                    )
                    
                    if enviar_mensaje_docente(correo_docente, nombre_docente, asunto, mensaje, contexto_tags):
                        enviados_correctamente += 1
            
            conn.commit()
            
            if edicion_id:
                if es_bienvenida and not destinatarios:
                    return jsonify({'ok': True, 'mensaje': 'Mensaje de confirmación programado. Se enviará a los docentes cuando se matriculen.'})
                return jsonify({'ok': True, 'mensaje': f'Mensaje enviado a {len(destinatarios)} participante(s).'})
            else:
                if enviados_correctamente > 0:
                    return jsonify({'ok': True, 'mensaje': 'Mensaje enviado y notificado correctamente.'})
                else:
                    return jsonify({'ok': True, 'mensaje': 'Notificación guardada, pero el correo no pudo ser enviado (revisar configuración o logs).'})
        except Exception as e:
            if 'conn' in locals() and conn:
                conn.rollback()
            return jsonify({'ok': False, 'error': f'Error interno: {e}'}), 500
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    @app.route('/admin/api/ediciones_activas', methods=['GET'])
    @admin_requerido
    def api_ediciones_activas():
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        e.id, 
                        c.nombre as curso_nombre,
                        c.modalidad,
                        e.fecha_inicio,
                        e.jornada,
                        e.enlace_acceso,
                        (SELECT COUNT(*) FROM matriculas m WHERE m.edicion_id = e.id AND m.aprobado IS NULL) as total_matriculados
                    FROM ediciones_formativas e
                    JOIN catalogo_acciones c ON e.catalogo_id = c.id
                    WHERE e.estado != 'Cerrado'
                    ORDER BY e.fecha_inicio DESC
                """)
                ediciones = cur.fetchall()
            return jsonify({'ok': True, 'ediciones': [dict(ed) for ed in ediciones]})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    @app.route('/admin/api/buscar_docente', methods=['GET'])
    @admin_requerido
    def api_buscar_docente():
        numero = request.args.get('numero', '').strip()
        if not numero:
            return jsonify({'ok': False, 'error': 'Número requerido'}), 400
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT numero_empleado, nombre_completo, correo_institucional, centro_universitario_regional FROM docentes WHERE numero_empleado = %s AND activo = 1 LIMIT 1',
                    (numero,)
                )
                docente = cur.fetchone()
            if docente:
                return jsonify({'ok': True, 'docente': dict(docente)})
            return jsonify({'ok': False, 'error': 'Docente no encontrado'}), 404
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    @app.route('/admin/api/msg_tags', methods=['GET'])
    @admin_requerido
    def api_msg_tags():
        from services.email_service import TAGS_DISPONIBLES
        return jsonify({'ok': True, 'tags': [{'tag': k, 'desc': v} for k, v in TAGS_DISPONIBLES.items()]})

    @app.route('/admin/api/msg_preview', methods=['POST'])
    @admin_requerido
    def api_msg_preview():
        """Resuelve tags en el texto del mensaje usando datos reales de la edición."""
        data = request.get_json(silent=True) or {}
        mensaje = data.get('mensaje', '')
        edicion_id = data.get('edicion_id', '').strip()
        numero_empleado = data.get('numero_empleado', '').strip()

        contexto = {
            '{{nombre_docente}}': 'Docente de Ejemplo',
            '{{nombre_accion}}': 'Acción Formativa',
            '{{modalidad}}': 'Virtual',
            '{{duracion_horas}}': '40',
            '{{fecha_inicio}}': '01/07/2025',
            '{{fecha_fin}}': '31/07/2025',
            '{{periodo}}': '2025-1',
            '{{enlace_acceso}}': 'https://campus.unah.edu.hn',
            '{{direccion}}': 'IPSD – UNAH',
        }

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                if edicion_id:
                    cur.execute("""
                        SELECT ef.fecha_inicio, ef.enlace_acceso, ef.periodo, ef.duracion_horas,
                               ca.nombre, ca.modalidad
                        FROM ediciones_formativas ef
                        JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
                        WHERE ef.id = %s LIMIT 1
                    """, (edicion_id,))
                    ed = cur.fetchone()
                    if ed:
                        from datetime import date as _date
                        fi = ed['fecha_inicio']
                        fecha_str = fi.strftime('%d/%m/%Y') if hasattr(fi, 'strftime') else str(fi)[:10]

                        # Get fecha_fin from sesiones
                        cur.execute('SELECT MAX(fecha) as fecha_fin FROM sesiones_curso WHERE edicion_id = %s', (edicion_id,))
                        ses = cur.fetchone()
                        fecha_fin_str = ''
                        if ses and ses['fecha_fin']:
                            ff = ses['fecha_fin']
                            fecha_fin_str = ff.strftime('%d/%m/%Y') if hasattr(ff, 'strftime') else str(ff)[:10]

                        contexto.update({
                            '{{nombre_accion}}': ed['nombre'] or '',
                            '{{modalidad}}': ed['modalidad'] or '',
                            '{{duracion_horas}}': str(ed['duracion_horas']) if ed['duracion_horas'] else 'N/D',
                            '{{fecha_inicio}}': fecha_str,
                            '{{fecha_fin}}': fecha_fin_str or 'N/D',
                            '{{periodo}}': ed['periodo'] or '',
                            '{{enlace_acceso}}': ed['enlace_acceso'] or 'N/D',
                        })
                if numero_empleado:
                    cur.execute('SELECT nombre_completo FROM docentes WHERE numero_empleado = %s LIMIT 1', (numero_empleado,))
                    doc = cur.fetchone()
                    if doc:
                        contexto['{{nombre_docente}}'] = doc['nombre_completo']
        except Exception:
            pass
        finally:
            if 'conn' in locals() and conn:
                conn.close()

        from services.email_service import resolver_tags
        preview = resolver_tags(mensaje, contexto)
        return jsonify({'ok': True, 'preview': preview})

