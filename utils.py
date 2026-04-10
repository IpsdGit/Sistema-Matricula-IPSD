import re
import secrets
from functools import wraps

from flask import abort, redirect, request, session, url_for

from config import (
    FILTROS_HISTORIAL_PERMITIDOS,
    LIMITE_ABANDONO,
    LIMITE_REPROBADO,
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
        SELECT id, nombre, mes, anio, trimestre FROM capacitaciones
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

        horarios = conn.execute(
            'SELECT horario FROM horarios_curso WHERE id_capacitacion = ?',
            (c['id'],),
        ).fetchall()

        mensaje_oportunidades = construir_mensaje_oportunidades(resumen)
        cursos_disponibles.append(
            {
                'id': c['id'],
                'nombre': c['nombre'],
                'mes': c['mes'],
                'anio': c['anio'],
                'trimestre': c['trimestre'],
                'horarios': [h['horario'] for h in horarios],
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
    filas = conn.execute(
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
            c.categoria AS estado_categoria
        FROM matricula_historial h
        JOIN estado_matricula_catalogo c ON c.codigo = h.estado_codigo
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


def construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles', filtro_historial='todas'):
    seccion_activa = normalizar_seccion_dashboard(seccion_activa)
    filtro_historial = normalizar_filtro_historial(filtro_historial)

    cursos_disponibles, cursos_matriculados, avisos_oportunidades = cargar_contexto_dashboard_docente(
        conn,
        numero_empleado,
    )
    historial_acciones, resumen_historial = obtener_historial_acciones_formativas(
        conn,
        numero_empleado,
        filtro_historial=filtro_historial,
    )

    return {
        'empleado': numero_empleado,
        'cursos': cursos_disponibles,
        'matriculados': cursos_matriculados,
        'avisos_oportunidades': avisos_oportunidades,
        'seccion_activa': seccion_activa,
        'filtro_historial': filtro_historial,
        'historial_acciones': historial_acciones,
        'resumen_historial': resumen_historial,
    }
