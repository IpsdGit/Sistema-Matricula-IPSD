import os
import shutil
# pyrefly: ignore [missing-import]
import pdfkit
from datetime import datetime
# pyrefly: ignore [missing-import]
from flask import render_template, current_app, url_for
# pyrefly: ignore [missing-import]
from werkzeug.utils import secure_filename
# pyrefly: ignore [missing-import]
from markupsafe import escape
from database import get_db_connection
from services import validacion_service


def _tabla_tiene_columna(conn, tabla: str, columna: str) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                  AND column_name = %s
                LIMIT 1
                ''',
                (tabla, columna),
            )
            return bool(cur.fetchone())
    except Exception:
        return False


def _ruta_web_a_ruta_absoluta(ruta_web: str) -> str:
    if not ruta_web:
        return ''
    ruta_relativa = ruta_web.lstrip('/')
    return os.path.join(current_app.root_path, ruta_relativa).replace('\\', '/')

def _ruta_absoluta_a_file_url(ruta_absoluta: str) -> str:
    if not ruta_absoluta:
        return ''
    import pathlib
    ruta = pathlib.Path(ruta_absoluta).as_posix()
    if ruta.startswith('/'):
        return f'file://{ruta}'
    return f'file:///{ruta}'


def _resolver_wkhtmltopdf_path() -> str:
    env_path = (os.environ.get('WKHTMLTOPDF_PATH') or '').strip()
    if env_path and os.path.exists(env_path):
        return env_path

    candidatos = [
        r'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
        r'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
    ]
    for candidato in candidatos:
        if os.path.exists(candidato):
            return candidato

    which_path = shutil.which('wkhtmltopdf')
    return which_path or ''


def _parse_fecha_iso(fecha_str: str):
    texto = (fecha_str or '').strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto[:10], '%Y-%m-%d')
    except ValueError:
        return None


def _partes_fecha(dt_obj):
    if not dt_obj:
        return '', '', ''
    meses = [
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ]
    mes = meses[dt_obj.month - 1].capitalize()
    return str(dt_obj.day), mes, str(dt_obj.year)


def _etiqueta_horario_edicion(jornada, hora):
    nombres = {
        'UNICA': 'Unica',
        'MATUTINA': 'Matutina',
        'VESPERTINA': 'Vespertina',
        'NOCTURNA': 'Nocturna',
    }
    jornada_norm = (jornada or '').strip().upper()
    jornada_texto = nombres.get(jornada_norm, 'Unica')
    hora_texto = (hora or '').strip()
    if not hora_texto:
        return jornada_texto
    if jornada_texto.lower() in hora_texto.lower():
        return hora_texto
    return f"{jornada_texto} {hora_texto}".strip()


def _horas_default_por_tipo(tipo_accion):
    tipo = (tipo_accion or '').strip().upper()
    if tipo == 'CONFERENCIA':
        return 4
    if tipo == 'SEMINARIO':
        return 16
    return 20


def _calcular_datos_sesiones(conn, edicion_id):
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT fecha, hora_inicio, hora_fin
            FROM sesiones_curso
            WHERE edicion_id = %s
            ''',
            (edicion_id,),
        )
        filas = cur.fetchall()

    if not filas:
        return None

    fechas = []
    total_horas = 0.0
    for fila in filas:
        fecha_dt = _parse_fecha_iso(fila['fecha'])
        if fecha_dt:
            fechas.append(fecha_dt)

        hora_inicio = (fila['hora_inicio'] or '').strip()[:5]
        hora_fin = (fila['hora_fin'] or '').strip()[:5]
        try:
            hi = datetime.strptime(hora_inicio, '%H:%M')
            hf = datetime.strptime(hora_fin, '%H:%M')
            delta = (hf - hi).seconds / 3600
            if delta > 0:
                total_horas += delta
        except Exception:
            continue

    if not fechas:
        return None

    fecha_inicio = min(fechas)
    fecha_fin = max(fechas)
    delta_dias = max(0, (fecha_fin.date() - fecha_inicio.date()).days)
    semanas = (delta_dias // 7) + 1
    return fecha_inicio, fecha_fin, int(round(total_horas)), semanas


def _formatear_fecha_larga(dia: str, mes: str, anio: str) -> str:
    dia = (dia or '').strip()
    mes = (mes or '').strip()
    anio = (anio or '').strip()
    if not (dia and mes and anio):
        return ''
    return f'{dia} de {mes} de {anio}'


def _formatear_rango_diploma(dia_ini: str, mes_ini: str, anio_ini: str, dia_fin: str, mes_fin: str, anio_fin: str) -> str:
    dia_ini = (dia_ini or '').strip()
    mes_ini = (mes_ini or '').strip()
    anio_ini = (anio_ini or '').strip()
    dia_fin = (dia_fin or '').strip()
    mes_fin = (mes_fin or '').strip()
    anio_fin = (anio_fin or '').strip()
    
    # Manejar caso de un solo día
    if dia_ini == dia_fin and mes_ini == mes_fin and anio_ini == anio_fin:
        return f'{dia_ini} de {mes_ini} de {anio_ini}'

    if not (dia_ini and mes_ini and anio_ini and dia_fin and mes_fin and anio_fin):
        return ''

    if anio_ini == anio_fin:
        if mes_ini == mes_fin:
            return f'del {dia_ini} al {dia_fin} de {mes_ini} de {anio_fin}'
        return f'del {dia_ini} de {mes_ini} al {dia_fin} de {mes_fin} de {anio_fin}'
    return f'del {dia_ini} de {mes_ini} de {anio_ini} al {dia_fin} de {mes_fin} de {anio_fin}'


def _reemplazar_etiquetas(texto: str, mapping: dict) -> str:
    texto = (texto or '').replace('\r\n', '\n')
    for etiqueta, valor in (mapping or {}).items():
        if etiqueta and (valor is not None):
            texto = texto.replace(etiqueta, f'<strong>{escape(str(valor))}</strong>')
    return texto.replace('\n', '<br>')

def registrar_plantilla(
    direccion_codigo,
    nombre_plantilla,
    tipo_documento,
    texto_certificado,
    firmante_nombre,
    firmante_cargo,
):
    upload_folder_backgrounds = os.path.join(current_app.root_path, 'static', 'certificados', 'backgrounds')
    os.makedirs(upload_folder_backgrounds, exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    texto_certificado = (texto_certificado or '').strip()
    if not texto_certificado:
        raise ValueError('Debes ingresar el texto del certificado.')

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                ''',
                ('plantillas_certificados',),
            )
            columnas_plantillas = {row['column_name'] for row in cur.fetchall()}

            campos = [
                'direccion_codigo',
                'nombre_plantilla',
                'tipo_documento',
                'texto_certificado',
                'firmante_nombre',
                'firmante_cargo',
            ]
            valores = [
                direccion_codigo,
                nombre_plantilla,
                tipo_documento,
                texto_certificado,
                firmante_nombre,
                firmante_cargo,
            ]

            if 'ruta_firma_img' in columnas_plantillas:
                campos.append('ruta_firma_img')
                valores.append('')

            if 'ruta_fondo_img' in columnas_plantillas:
                campos.append('ruta_fondo_img')
                valores.append('')

            placeholders = ', '.join(['%s'] * len(valores))
            campos_str = ', '.join(campos)

            cur.execute(
                f'''
                INSERT INTO plantillas_certificados
                ({campos_str})
                VALUES ({placeholders})
                ''',
                tuple(valores),
            )
        conn.commit()
    finally:
        conn.close()

def actualizar_plantilla(
    id_plantilla,
    direccion_codigo,
    nombre_plantilla,
    tipo_documento,
    texto_certificado,
    firmante_nombre,
    firmante_cargo,
):
    conn = get_db_connection()
    try:
        texto_certificado = (texto_certificado or '').strip()
        if not texto_certificado:
            raise ValueError('Debes ingresar el texto del certificado.')

        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                ''',
                ('plantillas_certificados',),
            )
            columnas_plantillas = {row['column_name'] for row in cur.fetchall()}

            campos_set = [
                'direccion_codigo = %s',
                'nombre_plantilla = %s',
                'tipo_documento = %s',
                'texto_certificado = %s',
                'firmante_nombre = %s',
                'firmante_cargo = %s',
            ]
            valores = [
                direccion_codigo,
                nombre_plantilla,
                tipo_documento,
                texto_certificado,
                firmante_nombre,
                firmante_cargo,
            ]

            valores.append(id_plantilla)
            campos_str = ', '.join(campos_set)

            cur.execute(
                f'''
                UPDATE plantillas_certificados
                SET {campos_str}
                WHERE id = %s
                ''',
                tuple(valores),
            )
            
        conn.commit()
    finally:
        conn.close()

def eliminar_plantilla(id_plantilla):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE plantillas_certificados SET activo = 0 WHERE id = %s', (id_plantilla,))
        # Opcional: Podríamos también setear id_plantilla_certificado a NULL en catalogo_acciones
        # conn.execute('UPDATE catalogo_acciones SET id_plantilla_certificado = NULL WHERE id_plantilla_certificado = %s', (id_plantilla,))
        conn.commit()
    finally:
        conn.close()

def obtener_plantillas_por_direccion(direccion_codigo):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    p.id,
                    p.direccion_codigo,
                    p.nombre_plantilla,
                    p.tipo_documento,
                    p.texto_certificado,
                    p.firmante_nombre,
                    p.firmante_cargo,
                    p.activo,
                    d.ruta_logo_img,
                    d.ruta_firma_img
                FROM plantillas_certificados p
                LEFT JOIN direcciones d ON d.codigo = p.direccion_codigo
                WHERE p.direccion_codigo = %s AND p.activo = 1
                ORDER BY p.id DESC
                ''',
                (direccion_codigo,),
            )
            plantillas = cur.fetchall()
        return [dict(p) for p in plantillas]
    finally:
        conn.close()

def obtener_todas_las_plantillas():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    p.id,
                    p.direccion_codigo,
                    p.nombre_plantilla,
                    p.tipo_documento,
                    p.texto_certificado,
                    p.firmante_nombre,
                    p.firmante_cargo,
                    p.activo,
                    d.ruta_logo_img,
                    d.ruta_firma_img
                FROM plantillas_certificados p
                LEFT JOIN direcciones d ON d.codigo = p.direccion_codigo
                WHERE p.activo = 1
                ORDER BY p.id DESC
                '''
            )
            plantillas = cur.fetchall()
        return [dict(p) for p in plantillas]
    finally:
        conn.close()

def obtener_plantilla_por_id(id_plantilla):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    p.id,
                    p.direccion_codigo,
                    p.nombre_plantilla,
                    p.tipo_documento,
                    p.texto_certificado,
                    p.firmante_nombre,
                    p.firmante_cargo,
                    p.activo,
                    d.ruta_logo_img,
                    d.ruta_firma_img
                FROM plantillas_certificados p
                LEFT JOIN direcciones d ON d.codigo = p.direccion_codigo
                WHERE p.id = %s AND p.activo = 1
                ''',
                (id_plantilla,),
            )
            plantilla = cur.fetchone()
        return dict(plantilla) if plantilla else None
    finally:
        conn.close()

def generar_html_preview_plantilla(plantilla):
    if not plantilla:
        return None

    contexto = dict(plantilla)
    ruta_firma_web = (contexto.get('ruta_firma_img') or '').strip()
    if not ruta_firma_web and contexto.get('direccion_codigo'):
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT ruta_firma_img, ruta_logo_img FROM direcciones WHERE codigo = %s LIMIT 1',
                    (contexto['direccion_codigo'],),
                )
                fila = cur.fetchone()
            ruta_firma_web = (fila['ruta_firma_img'] or '').strip() if fila else ''
            if fila and not contexto.get('ruta_logo_img'):
                contexto['ruta_logo_img'] = (fila['ruta_logo_img'] or '').strip()
        finally:
            conn.close()
        contexto['ruta_firma_img'] = ruta_firma_web
    if not ruta_firma_web:
        return None

    contexto['ruta_firma_src'] = ruta_firma_web
    
    ruta_logo_web = (contexto.get('ruta_logo_img') or '').strip()
    contexto['ruta_logo_src'] = ruta_logo_web or ''
    
    # Inyectar el fondo del diploma
    ruta_fondo_web = '/static/certificados/backgrounds/diploma_background.png'
    ruta_fondo = _ruta_web_a_ruta_absoluta(ruta_fondo_web)
    if os.path.exists(ruta_fondo):
        contexto['ruta_fondo_src'] = ruta_fondo_web
    else:
        contexto['ruta_fondo_src'] = ''

    contexto.update(
        {
            'nombre_docente': 'Carlos Daniel Interiano Irias',
            'numero_empleado': '000000',
            'horario_elegido': 'Nocturna 18:00-20:00',
            'curso_nombre': 'La Evolucion de la Docencia a Nivel Universitario',
            'modalidad': 'Presencial',
            'horas_totales': '20',
            'semanas_duracion': '4',
            'tipo_accion': 'CURSO',
            'centro_universitario_regional': 'Ciudad Universitaria',
            'anio': '2026',
            'mes': 'Abril',
            'dia': '27',
            'anio_fin': '2026',
            'mes_fin': 'Abril',
            'dia_fin': '27',
            'fecha_aprobacion': '2026-04-27',
        }
    )

    fecha_emision_str = ''
    if contexto.get('fecha_aprobacion'):
        try:
            fa = contexto['fecha_aprobacion']
            from datetime import datetime
            dt_aprob = datetime.strptime(fa, '%Y-%m-%d')
            meses = [
                'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
            ]
            fecha_emision_str = f"{dt_aprob.day} de {meses[dt_aprob.month-1]} de {dt_aprob.year}"
        except Exception:
            fecha_emision_str = contexto['fecha_aprobacion']

    contexto['fecha_emision_formateada'] = fecha_emision_str

    fecha_rango = _formatear_rango_diploma(
        contexto.get('dia'),
        contexto.get('mes'),
        contexto.get('anio'),
        contexto.get('dia_fin'),
        contexto.get('mes_fin'),
        contexto.get('anio_fin'),
    )
    fecha_exacta = _formatear_fecha_larga(contexto.get('dia'), contexto.get('mes'), contexto.get('anio'))

    mapping = {
        '[NOMBRE]': contexto.get('nombre_docente', ''),
        '[CURSO]': contexto.get('curso_nombre', ''),
        '[MODALIDAD]': contexto.get('modalidad', ''),
        '[HORAS]': contexto.get('horas_totales', ''),
        '[HORARIO]': contexto.get('horario_elegido', ''),
        '[FECHA]': fecha_exacta,
        '[FECHA_RANGO]': fecha_rango,
        '[FECHA_APROBACION]': fecha_emision_str,
        '[CENTRO_UNIVERSITARIO_REGIONAL]': contexto.get('centro_universitario_regional', ''),
        '[FECHA_EMISION]': fecha_emision_str,
    }

    texto_base = contexto.get('texto_certificado') or ''
    contexto['texto_certificado_renderizado'] = _reemplazar_etiquetas(texto_base, mapping)

    if contexto.get('tipo_documento') == 'DIPLOMA':
        return render_template('certificados/base_diploma.html', **contexto)
    return render_template('certificados/base_constancia.html', **contexto)

def generar_binario_pdf(matricula_id):
    conn = get_db_connection()
    try:
        # Obtener datos de la matrícula, docente, curso y plantilla
        query = '''
            SELECT
                m.edicion_id,
                d.nombre_completo as nombre_docente, d.numero_empleado, d.centro_universitario_regional,
                m.fecha_aprobacion,
                ca.nombre as curso_nombre, ca.modalidad, ca.tipo_accion,
                ef.fecha_inicio, ef.jornada, ef.hora,
                p.tipo_documento, p.direccion_codigo,
                ddir.ruta_firma_img, ddir.ruta_logo_img,
                p.texto_certificado, p.firmante_nombre, p.firmante_cargo
            FROM matriculas m
            JOIN docentes d ON m.numero_empleado = d.numero_empleado
            JOIN ediciones_formativas ef ON m.edicion_id = ef.id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            JOIN plantillas_certificados p ON ca.id_plantilla_certificado = p.id
            LEFT JOIN direcciones ddir ON p.direccion_codigo = ddir.codigo
            WHERE m.id = %s AND m.aprobado = 1
        '''
        with conn.cursor() as cur:
            cur.execute(query, (matricula_id,))
            datos = cur.fetchone()
        
        if not datos:
            return None
            
        contexto = dict(datos)

        # Completar datos faltantes desde sesiones
        contexto['horario_elegido'] = _etiqueta_horario_edicion(contexto.get('jornada'), contexto.get('hora'))

        datos_sesiones = _calcular_datos_sesiones(conn, contexto.get('edicion_id'))
        if datos_sesiones:
            fecha_inicio_dt, fecha_fin_dt, horas_totales, semanas_duracion = datos_sesiones
        else:
            fecha_inicio_dt = _parse_fecha_iso(contexto.get('fecha_inicio'))
            fecha_fin_dt = fecha_inicio_dt
            horas_totales = _horas_default_por_tipo(contexto.get('tipo_accion'))
            semanas_duracion = 1

        contexto['horas_totales'] = horas_totales
        contexto['semanas_duracion'] = semanas_duracion

        dia_ini, mes_ini, anio_ini = _partes_fecha(fecha_inicio_dt)
        dia_fin, mes_fin, anio_fin = _partes_fecha(fecha_fin_dt)
        contexto['dia'] = dia_ini
        contexto['mes'] = mes_ini
        contexto['anio'] = anio_ini
        contexto['dia_fin'] = dia_fin
        contexto['mes_fin'] = mes_fin
        contexto['anio_fin'] = anio_fin

        # Formatear fecha de aprobación para el sello
        fecha_emision_str = ''
        if contexto.get('fecha_aprobacion'):
            try:
                # La fecha_aprobacion está en formato YYYY-MM-DD
                fa = contexto['fecha_aprobacion']
                from datetime import datetime
                dt_aprob = datetime.strptime(fa, '%Y-%m-%d')
                meses = [
                    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
                ]
                fecha_emision_str = f"{dt_aprob.day} de {meses[dt_aprob.month-1]} de {dt_aprob.year}"
            except Exception:
                fecha_emision_str = contexto['fecha_aprobacion']
        
        contexto['fecha_emision_formateada'] = fecha_emision_str

        ruta_firma_web = (contexto.get('ruta_firma_img') or '').strip()
        if not ruta_firma_web:
            return None

        ruta_firma_absoluta = _ruta_web_a_ruta_absoluta(ruta_firma_web)
        contexto['ruta_firma_src'] = _ruta_absoluta_a_file_url(ruta_firma_absoluta)
        
        ruta_logo_web = (contexto.get('ruta_logo_img') or '').strip()
        if ruta_logo_web:
            ruta_logo_absoluta = _ruta_web_a_ruta_absoluta(ruta_logo_web)
            contexto['ruta_logo_src'] = _ruta_absoluta_a_file_url(ruta_logo_absoluta)
        else:
            contexto['ruta_logo_src'] = ''
        
        # Inyectar el fondo según tipo de documento
        if contexto['tipo_documento'] == 'DIPLOMA':
            ruta_fondo_web = '/static/certificados/backgrounds/diploma_background.png'
        else:
            ruta_fondo_web = '/static/certificados/backgrounds/constancia_background.png'
        
        ruta_fondo = _ruta_web_a_ruta_absoluta(ruta_fondo_web)
        if os.path.exists(ruta_fondo):
            contexto['ruta_fondo_src'] = _ruta_absoluta_a_file_url(ruta_fondo)
        else:
            contexto['ruta_fondo_src'] = ''

        fecha_rango = _formatear_rango_diploma(
            contexto.get('dia'),
            contexto.get('mes'),
            contexto.get('anio'),
            contexto.get('dia_fin'),
            contexto.get('mes_fin'),
            contexto.get('anio_fin'),
        )
        fecha_exacta = _formatear_fecha_larga(contexto.get('dia'), contexto.get('mes'), contexto.get('anio'))

        mapping = {
            '[NOMBRE]': contexto.get('nombre_docente', ''),
            '[CURSO]': contexto.get('curso_nombre', ''),
            '[MODALIDAD]': contexto.get('modalidad', ''),
            '[HORAS]': contexto.get('horas_totales', ''),
            '[HORARIO]': contexto.get('horario_elegido', ''),
            # Soportamos ambos: fecha exacta y rango.
            '[FECHA]': fecha_exacta,
            '[FECHA_RANGO]': fecha_rango,
            '[FECHA_APROBACION]': fecha_emision_str,
            '[CENTRO_UNIVERSITARIO_REGIONAL]': contexto.get('centro_universitario_regional', ''),
            '[FECHA_EMISION]': fecha_emision_str,
        }

        texto_base = contexto.get('texto_certificado') or ''
        contexto['texto_certificado_renderizado'] = _reemplazar_etiquetas(texto_base, mapping)
        
        # Opciones de pdfkit
        options = {
            'page-size': 'Letter',
            'margin-top': '0mm',
            'margin-right': '0mm',
            'margin-bottom': '0mm',
            'margin-left': '0mm',
            'encoding': "UTF-8",
            'enable-local-file-access': "",
            'print-media-type': None,
            'no-outline': None,
            'disable-smart-shrinking': "",
            'zoom': '1.0' # <--- Asegura la escala 1:1
        }
        
        # ── QR de validación ─────────────────────────────────────────────
        token_cert = ''
        qr_b64 = ''
        try:
            id_edicion = contexto.get('edicion_id') or ''
            cod_dir = contexto.get('direccion_codigo') or 'IPSD'
            token_cert = validacion_service.registrar_o_obtener_certificado(
                conn=conn,
                matricula_id=int(matricula_id),
                numero_empleado=contexto.get('numero_empleado', ''),
                edicion_id=id_edicion,
                tipo_documento=contexto['tipo_documento'],
                codigo_direccion=cod_dir,
            )
            # Construir la URL del validador
            try:
                url_validacion = url_for(
                    'validacion_bp.validar_token',
                    token=token_cert,
                    _external=True,
                )
            except Exception:
                url_validacion = f'http://localhost:5000/v/{token_cert}'

            qr_b64 = validacion_service.generar_qr_base64(url_validacion)
        except Exception as e:
            try:
                current_app.logger.warning(f'QR no generado: {e}')
            except Exception:
                pass

        contexto['qr_base64'] = qr_b64
        contexto['token_certificado'] = token_cert

        if contexto['tipo_documento'] == 'DIPLOMA':
            options['orientation'] = 'Landscape'
            html = render_template('certificados/base_diploma.html', **contexto)
        else:
            options['orientation'] = 'Portrait'
            html = render_template('certificados/base_constancia.html', **contexto)
            
        path_wkhtmltopdf = _resolver_wkhtmltopdf_path()
        if not path_wkhtmltopdf:
            raise RuntimeError(
                'wkhtmltopdf no está instalado o no se encontró en el servidor. Define WKHTMLTOPDF_PATH o instala wkhtmltopdf.'
            )
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
        pdf_binario = pdfkit.from_string(html, False, options=options, configuration=config)
        return pdf_binario
    except Exception as e:
        try:
            current_app.logger.exception('Error generando PDF')
        except Exception:
            pass
        raise e
    finally:
        conn.close()


def obtener_datos_empleado(matricula_id):
    """Obtiene el nombre, número de empleado y tipo de documento para una matrícula."""
    conn = get_db_connection()
    try:
        query = '''
            SELECT d.nombre_completo, d.numero_empleado, p.tipo_documento
            FROM matriculas m
            JOIN docentes d ON m.numero_empleado = d.numero_empleado
            JOIN ediciones_formativas ef ON m.edicion_id = ef.id
            JOIN catalogo_acciones ca ON ca.id = ef.catalogo_id
            JOIN plantillas_certificados p ON ca.id_plantilla_certificado = p.id
            WHERE m.id = %s AND m.aprobado = 1
        '''
        with conn.cursor() as cur:
            cur.execute(query, (matricula_id,))
            datos = cur.fetchone()
        
        if not datos:
            return None, None, None
        
        fila = dict(datos)
        return fila.get('nombre_completo'), fila.get('numero_empleado'), fila.get('tipo_documento')
    except Exception:
        return None, None, None
    finally:
        conn.close()
