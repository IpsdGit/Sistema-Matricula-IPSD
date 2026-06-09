import re
import secrets
from datetime import datetime
from functools import wraps

# pyrefly: ignore [missing-import]
from flask import abort, redirect, request, session, url_for

from config import (
    DIAS_SEMANA,
    FILTROS_HISTORIAL_PERMITIDOS,
    FILTROS_NOTIFICACION_PERMITIDOS,
    LIMITE_ABANDONO,
    LIMITE_REPROBADO,
    MESES_ES,
    SECCIONES_DASHBOARD_PERMITIDAS,
    VISTAS_ADMIN_PERMITIDAS,
)


def generar_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']


def validar_csrf(token_recibido):
    token_session = session.get('_csrf_token')
    return token_session and secrets.compare_digest(token_session, token_recibido or '')


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
    return numero and re.match(r'^\d{3,12}$', numero.strip())


def normalizar_correo(correo):
    return (correo or '').strip().lower()


def validar_correo(correo):
    correo_normalizado = normalizar_correo(correo)
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', correo_normalizado))


def validar_id_curso(id_curso):
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
    with conn.cursor() as cur:
        cur.execute('SELECT codigo, nombre, ruta_firma_img, ruta_logo_img FROM direcciones ORDER BY codigo')
        return cur.fetchall()


def direccion_existe(conn, direccion_codigo):
    with conn.cursor() as cur:
        cur.execute(
            'SELECT 1 FROM direcciones WHERE codigo = %s',
            (direccion_codigo,),
        )
        return bool(cur.fetchone())


def obtener_codigo_modalidad(modalidad):
    if modalidad == 'Virtual':
        return 'V'
    if modalidad == 'Presencial':
        return 'P'
    if modalidad == 'B-Learning':
        return 'B'
    return 'X'


def validar_enlace_virtual(url):
    if not url:
        return True
    return bool(re.match(r'^https?://\S+$', url.strip(), re.IGNORECASE))


def _nombre_jornada_horario(jornada):
    jornada_norm = (jornada or '').strip().upper()
    nombres = {
        'UNICA': 'Unica',
        'MATUTINA': 'Matutina',
        'VESPERTINA': 'Vespertina',
        'NOCTURNA': 'Nocturna',
    }
    return nombres.get(jornada_norm, 'Unica')


def _es_horario_por_definir(horario):
    texto = (horario or '').strip().lower()
    return not texto or 'por definir' in texto


def _etiqueta_horario_desde_sesion(jornada, hora_inicio, hora_fin):
    inicio = hora_inicio.strftime('%H:%M:%S')[:5] if hasattr(hora_inicio, 'strftime') else (hora_inicio or '').strip()[:5]
    fin = hora_fin.strftime('%H:%M:%S')[:5] if hasattr(hora_fin, 'strftime') else (hora_fin or '').strip()[:5]
    if not inicio or not fin:
        return None
    return f"{_nombre_jornada_horario(jornada)} {inicio}-{fin}"


def _etiqueta_horario_desde_edicion(jornada, hora):
    etiqueta_jornada = _nombre_jornada_horario(jornada)
    hora_texto = (hora or '').strip()
    if not hora_texto:
        return etiqueta_jornada
    if etiqueta_jornada.lower() in hora_texto.lower():
        return hora_texto
    return f"{etiqueta_jornada} {hora_texto}".strip()


def obtener_horarios_disponibles_curso(conn, edicion_id):
    with conn.cursor() as cur:
        cur.execute(
            'SELECT jornada, hora FROM ediciones_formativas WHERE id = %s LIMIT 1',
            (edicion_id,),
        )
        edicion = cur.fetchone()

    horarios = []
    if edicion:
        etiqueta = _etiqueta_horario_desde_edicion(edicion['jornada'], edicion['hora'])
        if etiqueta and not _es_horario_por_definir(etiqueta):
            horarios.append(etiqueta)

    if horarios:
        return horarios

    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT hora_inicio, hora_fin, MIN(fecha) AS primera_fecha
            FROM sesiones_curso
            WHERE edicion_id = %s
            GROUP BY hora_inicio, hora_fin
            ORDER BY primera_fecha ASC, hora_inicio ASC, hora_fin ASC
            ''',
            (edicion_id,),
        )
        sesiones = cur.fetchall()

    jornada = edicion['jornada'] if edicion else None
    horarios_sesiones = []
    vistos_sesiones = set()
    for fila in sesiones:
        etiqueta = _etiqueta_horario_desde_sesion(jornada, fila['hora_inicio'], fila['hora_fin'])
        if not etiqueta or etiqueta in vistos_sesiones:
            continue
        vistos_sesiones.add(etiqueta)
        horarios_sesiones.append(etiqueta)

    return horarios_sesiones


def normalizar_nombre_curso(nombre):
    return re.sub(r'\s+', ' ', (nombre or '').strip().lower())


def obtener_resumen_intentos_por_curso(conn, numero_empleado):
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT ca.nombre, m.aprobado
            FROM matriculas m
            JOIN ediciones_formativas ef ON ef.id = m.edicion_id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            WHERE m.numero_empleado = %s
            ''',
            (numero_empleado,),
        )
        filas = cur.fetchall()

    resumen = {}
    for fila in filas:
        nombre = (fila['nombre'] or '').strip()
        clave = normalizar_nombre_curso(nombre)
        if not clave:
            continue

        if clave not in resumen:
            resumen[clave] = {
                'nombre': nombre,
                'aprobados': 0,
                'reprobados': 0,
                'abandonos': 0,
                'pendientes': 0,
            }

        valor = fila['aprobado']
        if valor == 1:
            resumen[clave]['aprobados'] += 1
        elif valor == 0:
            resumen[clave]['reprobados'] += 1
        elif valor == 2:
            resumen[clave]['abandonos'] += 1
        else:
            resumen[clave]['pendientes'] += 1

    return resumen


def construir_mensaje_oportunidades(resumen):
    restantes_reprobado = max(0, LIMITE_REPROBADO - resumen['reprobados'])
    restantes_abandono = max(0, LIMITE_ABANDONO - resumen['abandonos'])

    if resumen['aprobados'] > 0:
        return 'Curso completado: ya fue aprobado.'
    if resumen['abandonos'] >= LIMITE_ABANDONO:
        return f'Sin oportunidades por abandono (límite {LIMITE_ABANDONO}).'
    if resumen['reprobados'] >= LIMITE_REPROBADO:
        return f'Sin oportunidades por no aprobación (límite {LIMITE_REPROBADO}).'

    partes = []
    if resumen['reprobados'] > 0:
        partes.append(f'{restantes_reprobado} oportunidad(es) por no aprobación')
    if resumen['abandonos'] > 0:
        partes.append(f'{restantes_abandono} oportunidad(es) por abandono')

    return ' | '.join(partes)


def estado_codigo_desde_aprobado(aprobado):
    if aprobado == 1:
        return 'APROBADA'
    if aprobado == 0:
        return 'NO_APROBADA'
    if aprobado == 2:
        return 'ABANDONO'
    return 'PENDIENTE'


def normalizar_seccion_dashboard(seccion):
    seccion_final = (seccion or 'disponibles').strip().lower()
    if seccion_final not in SECCIONES_DASHBOARD_PERMITIDAS:
        return 'disponibles'
    return seccion_final


def normalizar_filtro_historial(filtro):
    filtro_final = (filtro or 'todas').strip().lower()
    if filtro_final not in FILTROS_HISTORIAL_PERMITIDOS:
        return 'todas'
    return filtro_final


def normalizar_filtro_notificacion(filtro):
    filtro_final = (filtro or 'todas').strip().lower()
    if filtro_final not in FILTROS_NOTIFICACION_PERMITIDOS:
        return 'todas'
    return filtro_final


def normalizar_vista_admin(vista, es_superadmin=False):
    vista_final = (vista or 'dashboard').strip().lower()
    if vista_final == 'calendario':
        vista_final = 'ediciones'
    if vista_final not in VISTAS_ADMIN_PERMITIDAS:
        vista_final = 'dashboard'
    if vista_final == 'usuarios' and not es_superadmin:
        vista_final = 'dashboard'
    return vista_final


def redireccion_admin_vista(default_view='dashboard'):
    es_superadmin = session.get('admin_rol') == 'superadmin'
    vista_form = request.form.get('view', '')
    vista_args = request.args.get('view', '')
    vista = normalizar_vista_admin(vista_form or vista_args or default_view, es_superadmin)
    return redirect(url_for('admin', view=vista))


def generar_id_curso(conn, direccion, modalidad):
    codigo_modalidad = obtener_codigo_modalidad(modalidad)
    prefijo = f'{direccion}-{codigo_modalidad}-'

    with conn.cursor() as cur:
        cur.execute(
            'SELECT id FROM catalogo_acciones WHERE id LIKE %s',
            (f'{prefijo}%',),
        )
        existentes = cur.fetchall()

    ultimo = 0
    patron = re.compile(rf'^{re.escape(prefijo)}(\d{{3}})$')
    for row in existentes:
        match = patron.match((row['id'] or '').upper())
        if match:
            ultimo = max(ultimo, int(match.group(1)))

    return f'{prefijo}{ultimo + 1:03d}'


def cargar_contexto_dashboard_docente(conn, numero_empleado):
    query_matriculados = '''
     SELECT ef.id AS edicion_id,
         ca.id AS catalogo_id,
         ca.nombre,
         ca.modalidad,
         ef.periodo,
         ef.fecha_inicio,
         ef.jornada,
         ef.hora,
         m.id as matricula_id,
         m.aprobado,
         (SELECT COUNT(*) FROM sesiones_curso s WHERE s.edicion_id = ef.id AND s.estado = 1) as sesiones_habilitadas
        FROM matriculas m
     JOIN ediciones_formativas ef ON m.edicion_id = ef.id
     JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
        WHERE m.numero_empleado = %s
        ORDER BY m.id DESC
    '''
    with conn.cursor() as cur:
        cur.execute(query_matriculados, (numero_empleado,))
        cursos_matriculados = cur.fetchall()
    
    # Convertir a dict para poder mutarlo o acceder más fácil
    cursos_matriculados_list = []
    for fila in cursos_matriculados:
        if fila['aprobado'] is not None:
            continue
            
        modalidad = (fila['modalidad'] or '').strip()
        if modalidad not in {'Virtual', 'Presencial', 'B-Learning'}:
            modalidad = 'Virtual'

        fecha_dt = _fecha_desde_iso(fila['fecha_inicio'])
        anio = str(fecha_dt.year) if fecha_dt else None
        mes = MESES_ES[fecha_dt.month - 1] if fecha_dt else None
        dia = str(fecha_dt.day) if fecha_dt else None

        cursos_matriculados_list.append(
            {
                'id': fila['edicion_id'],
                'edicion_id': fila['edicion_id'],
                'catalogo_id': fila['catalogo_id'],
                'nombre': fila['nombre'],
                'periodo': fila['periodo'],
                'fecha_inicio': fila['fecha_inicio'],
                'anio': anio,
                'mes': mes,
                'dia': dia,
                'horario_elegido': _etiqueta_horario_desde_edicion(fila['jornada'], fila['hora']),
                'matricula_id': fila['matricula_id'],
                'aprobado': fila['aprobado'],
                'sesiones_habilitadas': fila['sesiones_habilitadas'],
                'modalidad': modalidad,
                'modalidad_icono': 'B' if modalidad == 'B-Learning' else ('V' if modalidad == 'Virtual' else 'P'),
            }
        )

    resumen_intentos = obtener_resumen_intentos_por_curso(conn, numero_empleado)

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query_disponibles = f'''
        SELECT ef.id AS edicion_id,
               ca.id AS catalogo_id,
               ca.nombre,
               ca.modalidad,
               ef.periodo,
               ef.fecha_inicio,
               ef.jornada,
               ef.hora,
               ef.fecha_limite_matricula,
               EXISTS (
                   SELECT 1 FROM ediciones_invitaciones ei 
                   WHERE ei.edicion_id = ef.id AND ei.numero_empleado = %s
               ) AS es_invitacion
        FROM ediciones_formativas ef
        JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
        WHERE (ef.privacidad = 'Abierta' 
               OR EXISTS (
                   SELECT 1 FROM ediciones_invitaciones ei 
                   WHERE ei.edicion_id = ef.id AND ei.numero_empleado = %s
               ))
          AND (ef.fecha_limite_matricula IS NULL OR ef.fecha_limite_matricula >= %s)
          AND ef.estado = 'Programado'
        ORDER BY ef.fecha_inicio DESC, ef.id DESC
    '''
    with conn.cursor() as cur:
        cur.execute(query_disponibles, (numero_empleado, numero_empleado, now_str))
        cursos_raw = cur.fetchall()

    cursos_agrupados = {}
    for c in cursos_raw:
        clave = normalizar_nombre_curso(c['nombre'])
        resumen = resumen_intentos.get(
            clave,
            {
                'nombre': c['nombre'],
                'aprobados': 0,
                'reprobados': 0,
                'abandonos': 0,
                'pendientes': 0,
            },
        )

        if resumen['pendientes'] > 0 or resumen['aprobados'] > 0:
            continue

        bloqueado = (
            resumen['reprobados'] >= LIMITE_REPROBADO
            or resumen['abandonos'] >= LIMITE_ABANDONO
        )

        fecha_inicio = c['fecha_inicio']
        clave_grupo = (clave, fecha_inicio)

        horarios_disponibles = obtener_horarios_disponibles_curso(conn, c['edicion_id'])
        edicion_info = {
            'edicion_id': c['edicion_id'],
            'jornada': c['jornada'],
            'hora': c['hora'],
            'horarios': horarios_disponibles
        }

        if clave_grupo not in cursos_agrupados:
            mensaje_oportunidades = construir_mensaje_oportunidades(resumen)
            modalidad = (c['modalidad'] or '').strip()
            if modalidad not in {'Virtual', 'Presencial', 'B-Learning'}:
                modalidad = 'Virtual'

            fecha_dt = _fecha_desde_iso(fecha_inicio)
            anio = str(fecha_dt.year) if fecha_dt else None
            mes = MESES_ES[fecha_dt.month - 1] if fecha_dt else None
            dia = str(fecha_dt.day) if fecha_dt else None

            cursos_agrupados[clave_grupo] = {
                'id': c['edicion_id'],
                'catalogo_id': c['catalogo_id'],
                'nombre': c['nombre'],
                'periodo': c['periodo'],
                'fecha_inicio': fecha_inicio,
                'anio': anio,
                'mes': mes,
                'dia': dia,
                'modalidad': modalidad,
                'modalidad_icono': 'B' if modalidad == 'B-Learning' else ('V' if modalidad == 'Virtual' else 'P'),
                'fecha_inicio_texto': _fecha_inicio_legible_desde_iso(fecha_inicio),
                'es_invitacion': bool(c.get('es_invitacion', False)),
                'mensaje_oportunidades': mensaje_oportunidades,
                'bloqueado': bloqueado,
                'ediciones': [edicion_info]
            }
        else:
            cursos_agrupados[clave_grupo]['ediciones'].append(edicion_info)

    cursos_disponibles = list(cursos_agrupados.values())

    avisos_oportunidades = []
    for item in resumen_intentos.values():
        if item['aprobados'] > 0:
            continue
        if item['reprobados'] == 0 and item['abandonos'] == 0:
            continue

        mensaje = construir_mensaje_oportunidades(item)
        bloqueado = (
            item['reprobados'] >= LIMITE_REPROBADO
            or item['abandonos'] >= LIMITE_ABANDONO
        )
        avisos_oportunidades.append(
            {
                'curso': item['nombre'],
                'mensaje': mensaje,
                'bloqueado': bloqueado,
            }
        )

    return cursos_disponibles, cursos_matriculados_list, avisos_oportunidades


def _fecha_iso_desde_partes_curso(anio, mes_nombre, dia):
    try:
        anio_int = int(str(anio).strip())
        dia_int = int(str(dia).strip())
    except (TypeError, ValueError):
        return None

    meses_map = {nombre.lower(): idx + 1 for idx, nombre in enumerate(MESES_ES)}
    mes_int = meses_map.get((mes_nombre or '').strip().lower())
    if not mes_int:
        return None

    try:
        fecha = datetime(anio_int, mes_int, dia_int)
    except ValueError:
        return None

    return fecha.strftime('%Y-%m-%d')


def _fecha_inicio_legible_desde_partes(anio, mes_nombre, dia):
    try:
        anio_int = int(str(anio).strip())
        dia_int = int(str(dia).strip())
    except (TypeError, ValueError):
        return None

    meses_map = {nombre.lower(): idx + 1 for idx, nombre in enumerate(MESES_ES)}
    mes_int = meses_map.get((mes_nombre or '').strip().lower())
    if not mes_int:
        return None

    try:
        fecha = datetime(anio_int, mes_int, dia_int)
    except ValueError:
        return None

    dia_semana = DIAS_SEMANA[fecha.weekday()]
    return f'{dia_semana}, {fecha.day} de {MESES_ES[fecha.month - 1]} de {fecha.year}'


def _fecha_desde_iso(fecha_iso):
    if not fecha_iso:
        return None
    if isinstance(fecha_iso, datetime):
        return fecha_iso
    if hasattr(fecha_iso, 'strftime'):
        return datetime(fecha_iso.year, fecha_iso.month, fecha_iso.day)
    try:
        return datetime.fromisoformat(str(fecha_iso).strip())
    except (ValueError, TypeError):
        return None


def _fecha_inicio_legible_desde_iso(fecha_iso):
    fecha = _fecha_desde_iso(fecha_iso)
    if not fecha:
        return None
    dia_semana = DIAS_SEMANA[fecha.weekday()]
    return f'{dia_semana}, {fecha.day} de {MESES_ES[fecha.month - 1]} de {fecha.year}'


def construir_eventos_calendario_docente(conn, numero_empleado):
    cursos_vinculados_query = '''
        SELECT DISTINCT edicion_id
        FROM matriculas
        WHERE numero_empleado = %s AND aprobado IS NULL
    '''

    params_vinculados = (numero_empleado,)

    with conn.cursor() as cur:
        cur.execute(
            f'''
            SELECT
                ef.id,
                ca.nombre,
                ca.modalidad,
                ef.fecha_inicio
            FROM ediciones_formativas ef
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            JOIN ({cursos_vinculados_query}) cv ON cv.edicion_id = ef.id
            ORDER BY ef.fecha_inicio ASC, ef.id ASC
            ''',
            params_vinculados,
        )
        cursos_vinculados = cur.fetchall()

        cur.execute(
            f'''
            SELECT
                s.id_sesion,
                s.edicion_id,
                s.fecha,
                s.hora_inicio,
                s.hora_fin,
                s.estado,
                ca.nombre,
                ca.modalidad
            FROM sesiones_curso s
            JOIN ediciones_formativas ef ON ef.id = s.edicion_id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            JOIN ({cursos_vinculados_query}) cv ON cv.edicion_id = s.edicion_id
            ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
            ''',
            params_vinculados,
        )
        sesiones_vinculadas = cur.fetchall()

    def _formatear_fecha_corta(fecha_str, hora_str=None):
        try:
            dt = datetime.strptime(fecha_str, '%Y-%m-%d')
            dia = DIAS_SEMANA[dt.weekday()].upper()
            if dt.date() == datetime.now().date():
                dia = "HOY"
            elif dt.date() == (datetime.now() + __import__('datetime').timedelta(days=1)).date():
                dia = "MAÑANA"
            
            res = f"{dia}, {dt.day} {MESES_ES[dt.month-1][:3].upper()}"
            if hora_str:
                res += f" {hora_str[:5]}"
            return res
        except:
            return f"{fecha_str} {hora_str or ''}"

    eventos = []
    for sesion in sesiones_vinculadas:
        fecha_val = sesion['fecha']
        if hasattr(fecha_val, 'strftime'):
            fecha_iso = fecha_val.strftime('%Y-%m-%d')
        else:
            fecha_iso = (fecha_val or '').strip()
        if not fecha_iso:
            continue

        try:
            dt_obj = datetime.strptime(fecha_iso, '%Y-%m-%d')
            dia_mes = str(dt_obj.day).zfill(2)
            # Determinar día semana corto (HOY, MAÑ, LUN, etc)
            dia_sem = DIAS_SEMANA[dt_obj.weekday()].upper()
            if dt_obj.date() == datetime.now().date():
                dia_sem = "HOY"
            elif dt_obj.date() == (datetime.now() + __import__('datetime').timedelta(days=1)).date():
                dia_sem = "MAÑ"
            else:
                dia_sem = dia_sem[:3]
        except:
            dia_mes = "00"
            dia_sem = "???"

        eventos.append(
            {
                'edicion_id': sesion['edicion_id'],
                'id_curso': sesion['edicion_id'],
                'nombre_curso': sesion['nombre'],
                'fecha_iso': fecha_iso,
                'hora_inicio': sesion['hora_inicio'],
                'hora_fin': sesion['hora_fin'],
                'tipo_evento': 'sesion',
                'estado': sesion['estado'],
                'modalidad': sesion['modalidad'] or '',
                'fecha_formateada': _formatear_fecha_corta(fecha_iso, sesion['hora_inicio']),
                'dia_mes': dia_mes,
                'dia_sem_corto': dia_sem
            }
        )

    eventos.sort(key=lambda ev: (ev.get('fecha_iso') or '', ev.get('hora_inicio') or '00:00', ev.get('edicion_id') or ''))
    return eventos


def construir_notificaciones_docente(
    cursos_disponibles,
    cursos_matriculados,
    avisos_oportunidades,
    historial_todas,
    ids_notificaciones_leidas=None,
):
    notificaciones = []
    claves = set()
    ids_leidas = set(ids_notificaciones_leidas or [])

    def agregar(
        tipo,
        titulo,
        mensaje,
        nivel='info',
        icono='ℹ️',
        fecha='Ahora',
        clave=None,
        accion_url=None,
        accion_label=None,
    ):
        id_unico = clave or f'{tipo}:{titulo}:{mensaje}'
        if id_unico in claves:
            return
        claves.add(id_unico)
        notificaciones.append(
            {
                'id': id_unico,
                'tipo': tipo,
                'titulo': titulo,
                'mensaje': mensaje,
                'nivel': nivel,
                'icono': icono,
                'fecha': fecha,
                'leida': id_unico in ids_leidas,
                'accion_url': accion_url,
                'accion_label': accion_label,
            }
        )

    for fila in historial_todas:
        estado = fila['estado_codigo']
        fecha_val = fila['fecha_evento']
        if hasattr(fecha_val, 'strftime'):
            fecha = fecha_val.strftime('%Y-%m-%d %H:%M')
        else:
            fecha = (fecha_val or '').strip()[:16] if fecha_val else 'Reciente'

        if estado == 'APROBADA':
            agregar(
                tipo='resultado',
                titulo='Resultado publicado: Aprobado',
                mensaje=f"{fila['nombre_accion']} ({fila['edicion_id']})",
                nivel='success',
                icono='✅',
                fecha=fecha,
                clave=f"res-apr-{fila['id']}",
            )
            agregar(
                tipo='certificado',
                titulo='Certificado disponible',
                mensaje=f"Tu certificado de {fila['nombre_accion']} está disponible.",
                nivel='success',
                icono='🎓',
                fecha=fecha,
                clave=f"cert-{fila['edicion_id']}-{fila['matricula_id']}",
            )
        elif estado == 'NO_APROBADA':
            agregar(
                tipo='resultado',
                titulo='Resultado publicado: No aprobado',
                mensaje=f"{fila['nombre_accion']} ({fila['edicion_id']})",
                nivel='danger',
                icono='❌',
                fecha=fecha,
                clave=f"res-noapr-{fila['id']}",
            )
        elif estado == 'ABANDONO':
            agregar(
                tipo='resultado',
                titulo='Estado actualizado: Abandono',
                mensaje=f"{fila['nombre_accion']} ({fila['edicion_id']})",
                nivel='warning',
                icono='⚠️',
                fecha=fecha,
                clave=f"res-ab-{fila['id']}",
            )
        elif estado == 'PENDIENTE':
            nombre_accion = fila.get('nombre_accion') or fila.get('nombre_curso') or 'Acción Formativa'
            detalle = fila.get('detalle', '')
            if 'administrativamente' in detalle or 'Grupo Cerrado' in detalle:
                agregar(
                    tipo='matricula',
                    titulo='Se te ha agregado a una nueva acción formativa',
                    mensaje=f"Fuiste inscrito(a) en: \"{nombre_accion}\".",
                    nivel='success',
                    icono='📝',
                    fecha=fecha,
                    clave=f"mat-pend-{fila['id']}",
                    accion_url='/dashboard?seccion=calendario',
                    accion_label='Ver Calendario'
                )
            else:
                agregar(
                    tipo='matricula',
                    titulo='Confirmación de Matrícula',
                    mensaje=f"Te has inscrito exitosamente en la Acción Formativa: \"{nombre_accion}\".",
                    nivel='success',
                    icono='✅',
                    fecha=fecha,
                    clave=f"mat-pend-{fila['id']}",
                    accion_url='/dashboard?seccion=calendario',
                    accion_label='Ver Calendario'
                )

    for curso in cursos_disponibles[:4]:
        if curso.get('es_invitacion'):
            agregar(
                tipo='invitacion',
                titulo='Invitación a acción formativa',
                mensaje=f"Has sido invitado(a) a participar en: {curso['nombre']} ({curso['id']})",
                nivel='info',
                icono='✉️',
                fecha='Disponible ahora',
                clave=f"invitacion-{curso['id']}",
                accion_url=f"/dashboard?seccion=disponibles#curso-{curso['id']}",
                accion_label='Ver invitación',
            )
        else:
            agregar(
                tipo='nueva_oferta',
                titulo='Nueva acción formativa disponible',
                mensaje=f"{curso['nombre']} · {curso['modalidad']} ({curso['id']})",
                nivel='info',
                icono='🆕',
                fecha='Disponible ahora',
                clave=f"oferta-{curso['id']}",
                accion_url=f"/dashboard?seccion=disponibles#curso-{curso['id']}",
                accion_label='Ir a la acción formativa',
            )
    if len(cursos_disponibles) > 4:
        agregar(
            tipo='nueva_oferta',
            titulo='Más acciones formativas disponibles',
            mensaje=f"Tienes {len(cursos_disponibles)} acciones activas en oferta.",
            nivel='info',
            icono='📚',
            fecha='Disponible ahora',
            clave='oferta-resumen',
        )

    cursos_pendientes = [c for c in cursos_matriculados if c['aprobado'] is None and c.get('sesiones_habilitadas', 0) > 0]
    for curso in cursos_pendientes[:4]:
        agregar(
            tipo='asistencia',
            titulo='Marcado de asistencia habilitado',
            mensaje=f"Puedes registrar asistencia en {curso['nombre']} ({curso['edicion_id']}).",
            nivel='warning',
            icono='⚡',
            fecha='Acción requerida',
            clave=f"asis-{curso['matricula_id']}",
            accion_url=f"/dashboard?seccion=disponibles#curso-{curso['edicion_id']}",
            accion_label='Registrar asistencia',
        )

    for aviso in avisos_oportunidades[:6]:
        agregar(
            tipo='oportunidades',
            titulo='Oportunidades de matrícula',
            mensaje=f"{aviso['curso']}: {aviso['mensaje']}",
            nivel='danger' if aviso['bloqueado'] else 'warning',
            icono='⛔' if aviso['bloqueado'] else '📌',
            fecha='Control activo',
            clave=f"opp-{aviso['curso']}-{aviso['bloqueado']}",
        )

    return notificaciones[:18]


def filtrar_notificaciones(notificaciones, filtro_notificacion):
    filtro_notificacion = normalizar_filtro_notificacion(filtro_notificacion)
    if filtro_notificacion == 'todas':
        return notificaciones

    mapa_tipo = {
        'nuevas': {'nueva_oferta'},
        'asistencia': {'asistencia'},
        'resultados': {'resultado'},
        'oportunidades': {'oportunidades'},
        'certificados': {'certificado'},
    }
    tipos = mapa_tipo.get(filtro_notificacion, set())
    return [n for n in notificaciones if n['tipo'] in tipos]


def resumir_notificaciones(notificaciones):
    resumen = {
        'todas': len(notificaciones),
        'nuevas': 0,
        'asistencia': 0,
        'resultados': 0,
        'oportunidades': 0,
        'certificados': 0,
    }

    for item in notificaciones:
        tipo = item['tipo']
        if tipo == 'nueva_oferta':
            resumen['nuevas'] += 1
        elif tipo == 'asistencia':
            resumen['asistencia'] += 1
        elif tipo == 'resultado':
            resumen['resultados'] += 1
        elif tipo == 'oportunidades':
            resumen['oportunidades'] += 1
        elif tipo == 'certificado':
            resumen['certificados'] += 1

    return resumen


def registrar_evento_matricula(
    conn,
    numero_empleado,
    edicion_id,
    nombre_accion,
    estado_codigo,
    matricula_id=None,
    detalle='',
):
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO matricula_historial (
                matricula_id, numero_empleado, edicion_id, nombre_accion,
                estado_codigo, detalle
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            (
                matricula_id,
                numero_empleado,
                edicion_id,
                nombre_accion,
                estado_codigo,
                detalle,
            ),
        )


def obtener_historial_acciones_formativas(conn, numero_empleado, filtro_historial='todas'):
    filtro_historial = normalizar_filtro_historial(filtro_historial)
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT
                h.id,
                h.matricula_id,
                h.edicion_id,
                h.nombre_accion,
                h.estado_codigo,
                h.fecha_evento,
                h.detalle,
                c.nombre AS estado_nombre,
                c.categoria AS estado_categoria,
                m_act.id AS matricula_activa_id,
                cap.modalidad AS modalidad_actual,
                ef.jornada AS jornada_edicion,
                ef.hora AS hora_edicion
            FROM matricula_historial h
            JOIN estado_matricula_catalogo c ON c.codigo = h.estado_codigo
            LEFT JOIN matriculas m_act ON m_act.id = h.matricula_id
            LEFT JOIN ediciones_formativas ef ON ef.id = h.edicion_id
            LEFT JOIN catalogo_acciones cap ON cap.id = ef.catalogo_id
            JOIN (
                SELECT COALESCE(matricula_id, -id) AS agrupador, MAX(id) AS max_id
                FROM matricula_historial
                WHERE numero_empleado = %s
                GROUP BY COALESCE(matricula_id, -id)
            ) ult ON ult.max_id = h.id
            WHERE h.numero_empleado = %s
            ORDER BY h.id DESC
            ''',
            (numero_empleado, numero_empleado),
        )
        filas_raw = cur.fetchall()

    filas = []
    for fila in filas_raw:
        estado_codigo = fila['estado_codigo']
        estado_nombre = fila['estado_nombre']
        estado_categoria = fila['estado_categoria']

        # Si la matrícula ya no existe y el último estado quedó pendiente,
        # se interpreta como cancelada por limpieza/eliminación administrativa.
        if estado_codigo == 'PENDIENTE' and fila['matricula_activa_id'] is None:
            estado_codigo = 'CANCELADA'
            estado_nombre = 'Cancelada'
            estado_categoria = 'canceladas'

        modalidad = (fila['modalidad_actual'] or '').strip()
        if modalidad not in {'Virtual', 'Presencial'}:
            modalidad = 'No definida'

        modalidad_icono = 'V' if modalidad == 'Virtual' else 'P' if modalidad == 'Presencial' else '?'

        filas.append(
            {
                'id': fila['id'],
                'matricula_id': fila['matricula_id'],
                'edicion_id': fila['edicion_id'],
                'nombre_accion': fila['nombre_accion'],
                'horario_elegido': _etiqueta_horario_desde_edicion(fila['jornada_edicion'], fila['hora_edicion']),
                'estado_codigo': estado_codigo,
                'estado_nombre': estado_nombre,
                'estado_categoria': estado_categoria,
                'fecha_evento': fila['fecha_evento'],
                'detalle': fila.get('detalle', ''),
                'modalidad': modalidad,
                'modalidad_icono': modalidad_icono,
            }
        )

    resumen = {
        'todas': len(filas),
        'aprobadas': 0,
        'no_aprobadas': 0,
        'canceladas': 0,
    }
    historial_filtrado = []

    for fila in filas:
        categoria = fila['estado_categoria']
        if categoria in resumen:
            resumen[categoria] += 1

        if filtro_historial != 'todas' and categoria != filtro_historial:
            continue

        historial_filtrado.append(fila)

    return historial_filtrado, resumen


def construir_contexto_dashboard(
    conn,
    numero_empleado,
    seccion_activa='disponibles',
    filtro_historial='todas',
    filtro_notificacion='todas',
    ids_notificaciones_leidas=None,
):
    seccion_activa = normalizar_seccion_dashboard(seccion_activa)
    filtro_historial = normalizar_filtro_historial(filtro_historial)
    filtro_notificacion = normalizar_filtro_notificacion(filtro_notificacion)

    cursos_disponibles, cursos_matriculados, avisos_oportunidades = cargar_contexto_dashboard_docente(
        conn,
        numero_empleado,
    )
    historial_todas, resumen_historial = obtener_historial_acciones_formativas(
        conn,
        numero_empleado,
        filtro_historial='todas',
    )

    if filtro_historial == 'todas':
        historial_acciones = historial_todas
    else:
        historial_acciones = [h for h in historial_todas if h['estado_categoria'] == filtro_historial]

    notificaciones = construir_notificaciones_docente(
        cursos_disponibles,
        cursos_matriculados,
        avisos_oportunidades,
        historial_todas,
        ids_notificaciones_leidas=ids_notificaciones_leidas,
    )
    notificaciones_filtradas = filtrar_notificaciones(notificaciones, filtro_notificacion)
    resumen_notificaciones = resumir_notificaciones(notificaciones)
    notificaciones_no_leidas = len([n for n in notificaciones if not n['leida']])
    calendario_eventos_docente = construir_eventos_calendario_docente(conn, numero_empleado)

    ahora_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    proximas_actividades = []
    for evt in calendario_eventos_docente:
        fecha = evt.get('fecha_iso', '')
        hora = evt.get('hora_fin', evt.get('hora_inicio', '00:00'))
        if not fecha:
            continue
        evt_dt_str = f"{fecha} {hora[:5]}"
        if evt_dt_str >= ahora_str:
            proximas_actividades.append(evt)

    return {
        'empleado': numero_empleado,
        'cursos': cursos_disponibles,
        'matriculados': cursos_matriculados,
        'avisos_oportunidades': avisos_oportunidades,
        'seccion_activa': seccion_activa,
        'filtro_historial': filtro_historial,
        'filtro_notificacion': filtro_notificacion,
        'historial_acciones': historial_acciones,
        'resumen_historial': resumen_historial,
        'notificaciones': notificaciones_filtradas,
        'notificaciones_todas': notificaciones,
        'resumen_notificaciones': resumen_notificaciones,
        'notificaciones_total': notificaciones_no_leidas,
        'calendario_eventos_docente': calendario_eventos_docente,
        'proximas_actividades': proximas_actividades,
    }
