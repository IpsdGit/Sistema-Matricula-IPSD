import re
import secrets
from datetime import datetime
from functools import wraps

from flask import abort, redirect, request, session, url_for

from config import (
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
    return numero and re.match(r'^\d{4,12}$', numero.strip())


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
    return conn.execute('SELECT codigo, nombre FROM direcciones ORDER BY codigo').fetchall()


def direccion_existe(conn, direccion_codigo):
    return bool(
        conn.execute(
            'SELECT 1 FROM direcciones WHERE codigo = ?',
            (direccion_codigo,),
        ).fetchone()
    )


def obtener_codigo_modalidad(modalidad):
    if modalidad == 'Virtual':
        return 'V'
    if modalidad == 'Presencial':
        return 'P'
    return None


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
    inicio = (hora_inicio or '').strip()[:5]
    fin = (hora_fin or '').strip()[:5]
    if not inicio or not fin:
        return None
    return f"{_nombre_jornada_horario(jornada)} {inicio}-{fin}"


def obtener_horarios_disponibles_curso(conn, id_curso):
    horarios_bd = conn.execute(
        'SELECT horario FROM horarios_curso WHERE id_capacitacion = ? ORDER BY id ASC',
        (id_curso,),
    ).fetchall()

    horarios_norm = []
    vistos = set()
    for fila in horarios_bd:
        horario = (fila['horario'] or '').strip()
        if not horario or horario in vistos:
            continue
        vistos.add(horario)
        horarios_norm.append(horario)

    horarios_validos = [h for h in horarios_norm if not _es_horario_por_definir(h)]
    if horarios_validos:
        return horarios_validos

    sesiones = conn.execute(
        '''
        SELECT jornada, hora_inicio, hora_fin, MIN(fecha) AS primera_fecha
        FROM sesiones_curso
        WHERE id_curso = ?
        GROUP BY jornada, hora_inicio, hora_fin
        ORDER BY primera_fecha ASC, hora_inicio ASC, hora_fin ASC
        ''',
        (id_curso,),
    ).fetchall()

    horarios_sesiones = []
    vistos_sesiones = set()
    for fila in sesiones:
        etiqueta = _etiqueta_horario_desde_sesion(fila['jornada'], fila['hora_inicio'], fila['hora_fin'])
        if not etiqueta or etiqueta in vistos_sesiones:
            continue
        vistos_sesiones.add(etiqueta)
        horarios_sesiones.append(etiqueta)

    return horarios_sesiones


def normalizar_nombre_curso(nombre):
    return re.sub(r'\s+', ' ', (nombre or '').strip().lower())


def obtener_resumen_intentos_por_curso(conn, numero_empleado):
    filas = conn.execute(
        '''
        SELECT c.nombre, m.aprobado
        FROM matriculas m
        JOIN capacitaciones c ON c.id = m.id_capacitacion
        WHERE m.numero_empleado = ?
        ''',
        (numero_empleado,),
    ).fetchall()

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
    prefijo = f'AF-{direccion}-{codigo_modalidad}-'

    existentes = conn.execute(
        'SELECT id FROM capacitaciones WHERE id LIKE ?',
        (f'{prefijo}%',),
    ).fetchall()

    ultimo = 0
    patron = re.compile(rf'^{re.escape(prefijo)}(\d{{3}})$')
    for row in existentes:
        match = patron.match((row['id'] or '').upper())
        if match:
            ultimo = max(ultimo, int(match.group(1)))

    return f'{prefijo}{ultimo + 1:03d}'


def cargar_contexto_dashboard_docente(conn, numero_empleado):
    query_matriculados = '''
        SELECT c.id, c.nombre, c.mes, c.anio, m.horario_elegido, m.id as matricula_id, m.aprobado
        FROM matriculas m
        JOIN capacitaciones c ON m.id_capacitacion = c.id
        WHERE m.numero_empleado = ?
        ORDER BY m.id DESC
    '''
    cursos_matriculados = conn.execute(query_matriculados, (numero_empleado,)).fetchall()

    resumen_intentos = obtener_resumen_intentos_por_curso(conn, numero_empleado)

    query_disponibles = '''
        SELECT id, nombre, mes, anio, trimestre, modalidad FROM capacitaciones
        ORDER BY anio DESC, mes
    '''
    cursos_raw = conn.execute(query_disponibles).fetchall()

    cursos_disponibles = []
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

        bloqueado = (
            resumen['aprobados'] > 0
            or resumen['pendientes'] > 0
            or resumen['reprobados'] >= LIMITE_REPROBADO
            or resumen['abandonos'] >= LIMITE_ABANDONO
        )
        if bloqueado:
            continue

        horarios_disponibles = obtener_horarios_disponibles_curso(conn, c['id'])

        mensaje_oportunidades = construir_mensaje_oportunidades(resumen)
        modalidad = (c['modalidad'] or '').strip()
        if modalidad not in {'Virtual', 'Presencial'}:
            modalidad = 'Virtual' if '-V-' in (c['id'] or '').upper() else 'Presencial'

        cursos_disponibles.append(
            {
                'id': c['id'],
                'nombre': c['nombre'],
                'mes': c['mes'],
                'anio': c['anio'],
                'trimestre': c['trimestre'],
                'modalidad': modalidad,
                'modalidad_icono': 'V' if modalidad == 'Virtual' else 'P',
                'horarios': horarios_disponibles,
                'horarios_preview': horarios_disponibles[:2],
                'mensaje_oportunidades': mensaje_oportunidades,
            }
        )

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

    return cursos_disponibles, cursos_matriculados, avisos_oportunidades


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


def construir_eventos_calendario_docente(conn, numero_empleado):
    cursos_vinculados_query = '''
        SELECT DISTINCT id_capacitacion AS id_curso
        FROM matriculas
        WHERE numero_empleado = ?
        UNION
        SELECT DISTINCT id_capacitacion AS id_curso
        FROM matricula_historial
        WHERE numero_empleado = ?
    '''

    params_vinculados = (numero_empleado, numero_empleado)

    cursos_vinculados = conn.execute(
        f'''
        SELECT
            c.id,
            c.nombre,
            c.modalidad,
            c.anio,
            c.mes,
            c.dia
        FROM capacitaciones c
        JOIN ({cursos_vinculados_query}) cv ON cv.id_curso = c.id
        ORDER BY c.anio ASC, c.id ASC
        ''',
        params_vinculados,
    ).fetchall()

    sesiones_vinculadas = conn.execute(
        f'''
        SELECT
            s.id_sesion,
            s.id_curso,
            s.fecha,
            s.hora_inicio,
            s.hora_fin,
            s.estado,
            c.nombre,
            c.modalidad
        FROM sesiones_curso s
        JOIN capacitaciones c ON c.id = s.id_curso
        JOIN ({cursos_vinculados_query}) cv ON cv.id_curso = s.id_curso
        ORDER BY s.fecha ASC, s.hora_inicio ASC, s.id_sesion ASC
        ''',
        params_vinculados,
    ).fetchall()

    eventos = []
    for curso in cursos_vinculados:
        fecha_iso = _fecha_iso_desde_partes_curso(curso['anio'], curso['mes'], curso['dia'])
        if not fecha_iso:
            continue

        eventos.append(
            {
                'id_curso': curso['id'],
                'nombre_curso': curso['nombre'],
                'fecha_iso': fecha_iso,
                'hora_inicio': None,
                'hora_fin': None,
                'tipo_evento': 'curso',
                'estado': None,
                'modalidad': curso['modalidad'] or '',
            }
        )

    for sesion in sesiones_vinculadas:
        fecha_iso = (sesion['fecha'] or '').strip()
        if not fecha_iso:
            continue

        eventos.append(
            {
                'id_curso': sesion['id_curso'],
                'nombre_curso': sesion['nombre'],
                'fecha_iso': fecha_iso,
                'hora_inicio': sesion['hora_inicio'],
                'hora_fin': sesion['hora_fin'],
                'tipo_evento': 'sesion',
                'estado': sesion['estado'],
                'modalidad': sesion['modalidad'] or '',
            }
        )

    eventos.sort(key=lambda ev: (ev.get('fecha_iso') or '', ev.get('hora_inicio') or '00:00', ev.get('id_curso') or ''))
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
        fecha = fila['fecha_evento'][:16] if fila['fecha_evento'] else 'Reciente'

        if estado == 'APROBADA':
            agregar(
                tipo='resultado',
                titulo='Resultado publicado: Aprobado',
                mensaje=f"{fila['nombre_curso']} ({fila['id_capacitacion']})",
                nivel='success',
                icono='✅',
                fecha=fecha,
                clave=f"res-apr-{fila['id']}",
            )
            agregar(
                tipo='certificado',
                titulo='Certificado disponible',
                mensaje=f"Tu certificado de {fila['nombre_curso']} está disponible.",
                nivel='success',
                icono='🎓',
                fecha=fecha,
                clave=f"cert-{fila['id_capacitacion']}-{fila['matricula_id']}",
            )
        elif estado == 'NO_APROBADA':
            agregar(
                tipo='resultado',
                titulo='Resultado publicado: No aprobado',
                mensaje=f"{fila['nombre_curso']} ({fila['id_capacitacion']})",
                nivel='danger',
                icono='❌',
                fecha=fecha,
                clave=f"res-noapr-{fila['id']}",
            )
        elif estado == 'ABANDONO':
            agregar(
                tipo='resultado',
                titulo='Estado actualizado: Abandono',
                mensaje=f"{fila['nombre_curso']} ({fila['id_capacitacion']})",
                nivel='warning',
                icono='⚠️',
                fecha=fecha,
                clave=f"res-ab-{fila['id']}",
            )

    for curso in cursos_disponibles[:4]:
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

    cursos_pendientes = [c for c in cursos_matriculados if c['aprobado'] is None]
    for curso in cursos_pendientes[:4]:
        agregar(
            tipo='asistencia',
            titulo='Marcado de asistencia habilitado',
            mensaje=f"Puedes registrar asistencia en {curso['nombre']} ({curso['id']}).",
            nivel='warning',
            icono='🗓️',
            fecha='Acción requerida',
            clave=f"asis-{curso['matricula_id']}",
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
    id_capacitacion,
    nombre_curso,
    horario_elegido,
    estado_codigo,
    matricula_id=None,
    detalle='',
):
    conn.execute(
        '''
        INSERT INTO matricula_historial (
            matricula_id, numero_empleado, id_capacitacion, nombre_curso,
            horario_elegido, estado_codigo, detalle
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            matricula_id,
            numero_empleado,
            id_capacitacion,
            nombre_curso,
            horario_elegido,
            estado_codigo,
            detalle,
        ),
    )


def obtener_historial_acciones_formativas(conn, numero_empleado, filtro_historial='todas'):
    filtro_historial = normalizar_filtro_historial(filtro_historial)
    filas_raw = conn.execute(
        '''
        SELECT
            h.id,
            h.matricula_id,
            h.id_capacitacion,
            h.nombre_curso,
            h.horario_elegido,
            h.estado_codigo,
            h.fecha_evento,
            c.nombre AS estado_nombre,
            c.categoria AS estado_categoria,
            m_act.id AS matricula_activa_id,
            cap.modalidad AS modalidad_actual
        FROM matricula_historial h
        JOIN estado_matricula_catalogo c ON c.codigo = h.estado_codigo
        LEFT JOIN matriculas m_act ON m_act.id = h.matricula_id
        LEFT JOIN capacitaciones cap ON cap.id = h.id_capacitacion
        JOIN (
            SELECT COALESCE(matricula_id, -id) AS agrupador, MAX(id) AS max_id
            FROM matricula_historial
            WHERE numero_empleado = ?
            GROUP BY COALESCE(matricula_id, -id)
        ) ult ON ult.max_id = h.id
        WHERE h.numero_empleado = ?
        ORDER BY h.id DESC
        ''',
        (numero_empleado, numero_empleado),
    ).fetchall()

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
            curso_id = (fila['id_capacitacion'] or '').upper()
            if '-V-' in curso_id:
                modalidad = 'Virtual'
            elif '-P-' in curso_id:
                modalidad = 'Presencial'
            else:
                modalidad = 'No definida'

        modalidad_icono = 'V' if modalidad == 'Virtual' else 'P' if modalidad == 'Presencial' else '?'

        filas.append(
            {
                'id': fila['id'],
                'matricula_id': fila['matricula_id'],
                'id_capacitacion': fila['id_capacitacion'],
                'nombre_curso': fila['nombre_curso'],
                'horario_elegido': fila['horario_elegido'],
                'estado_codigo': estado_codigo,
                'estado_nombre': estado_nombre,
                'estado_categoria': estado_categoria,
                'fecha_evento': fila['fecha_evento'],
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
    }
