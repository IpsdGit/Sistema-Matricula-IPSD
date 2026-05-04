import os
import shutil
import pdfkit
from flask import render_template, current_app
from werkzeug.utils import secure_filename
from markupsafe import escape
from database import get_db_connection


def _tabla_tiene_columna(conn, tabla: str, columna: str) -> bool:
    try:
        filas = conn.execute(f'PRAGMA table_info({tabla})').fetchall()
        return any((fila['name'] == columna) for fila in (filas or []))
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
    ruta = ruta_absoluta.replace('\\', '/')
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
        columnas_plantillas = {row['name'] for row in conn.execute('PRAGMA table_info(plantillas_certificados)').fetchall()}
        
        campos = ['direccion_codigo', 'nombre_plantilla', 'tipo_documento', 'texto_certificado', 'firmante_nombre', 'firmante_cargo']
        valores = [direccion_codigo, nombre_plantilla, tipo_documento, texto_certificado, firmante_nombre, firmante_cargo]

        if 'ruta_firma_img' in columnas_plantillas:
            campos.append('ruta_firma_img')
            valores.append('')
        
        if 'ruta_fondo_img' in columnas_plantillas:
            campos.append('ruta_fondo_img')
            valores.append('')

        placeholders = ', '.join(['?'] * len(valores))
        campos_str = ', '.join(campos)

        conn.execute(
            f'''
            INSERT INTO plantillas_certificados
            ({campos_str})
            VALUES ({placeholders})
            ''',
            tuple(valores)
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
        
        columnas_plantillas = {row['name'] for row in conn.execute('PRAGMA table_info(plantillas_certificados)').fetchall()}
        
        campos_set = ['direccion_codigo = ?', 'nombre_plantilla = ?', 'tipo_documento = ?', 'texto_certificado = ?', 'firmante_nombre = ?', 'firmante_cargo = ?']
        valores = [direccion_codigo, nombre_plantilla, tipo_documento, texto_certificado, firmante_nombre, firmante_cargo]

        valores.append(id_plantilla)
        campos_str = ', '.join(campos_set)

        conn.execute(
            f'''
            UPDATE plantillas_certificados
            SET {campos_str}
            WHERE id = ?
            ''',
            tuple(valores)
        )
            
        conn.commit()
    finally:
        conn.close()

def eliminar_plantilla(id_plantilla):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE plantillas_certificados SET activo = 0 WHERE id = ?', (id_plantilla,))
        # Opcional: Podríamos también setear id_plantilla_certificado a NULL en capacitaciones
        # conn.execute('UPDATE capacitaciones SET id_plantilla_certificado = NULL WHERE id_plantilla_certificado = ?', (id_plantilla,))
        conn.commit()
    finally:
        conn.close()

def obtener_plantillas_por_direccion(direccion_codigo):
    conn = get_db_connection()
    try:
        plantillas = conn.execute(
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
                p.ruta_logo_img,
                d.ruta_firma_img
            FROM plantillas_certificados p
            LEFT JOIN direcciones d ON d.codigo = p.direccion_codigo
            WHERE p.direccion_codigo = ? AND p.activo = 1
            ORDER BY p.id DESC
            ''',
            (direccion_codigo,),
        ).fetchall()
        return [dict(p) for p in plantillas]
    finally:
        conn.close()

def obtener_todas_las_plantillas():
    conn = get_db_connection()
    try:
        plantillas = conn.execute(
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
        ).fetchall()
        return [dict(p) for p in plantillas]
    finally:
        conn.close()

def obtener_plantilla_por_id(id_plantilla):
    conn = get_db_connection()
    try:
        plantilla = conn.execute(
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
            WHERE p.id = ? AND p.activo = 1
            ''',
            (id_plantilla,),
        ).fetchone()
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
            fila = conn.execute(
                'SELECT ruta_firma_img, ruta_logo_img FROM direcciones WHERE codigo = ? LIMIT 1',
                (contexto['direccion_codigo'],),
            ).fetchone()
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
                d.nombre_completo as nombre_docente, d.numero_empleado, d.centro_universitario_regional,
                m.horario_elegido, m.fecha_aprobacion,
                c.nombre as curso_nombre, c.modalidad, c.horas_totales, c.semanas_duracion, c.tipo_accion,
                c.anio, c.mes, c.dia, c.anio_fin, c.mes_fin, c.dia_fin,
                p.tipo_documento, ddir.ruta_firma_img, ddir.ruta_logo_img, p.texto_certificado, p.firmante_nombre, p.firmante_cargo
            FROM matriculas m
            JOIN docentes d ON m.numero_empleado = d.numero_empleado
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            JOIN plantillas_certificados p ON c.id_plantilla_certificado = p.id
            LEFT JOIN direcciones ddir ON p.direccion_codigo = ddir.codigo
            WHERE m.id = ? AND m.aprobado = 1
        '''
        datos = conn.execute(query, (matricula_id,)).fetchone()
        
        if not datos:
            return None
            
        contexto = dict(datos)

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
            'margin-top': '0',
            'margin-right': '0',
            'margin-bottom': '0',
            'margin-left': '0',
            'encoding': "UTF-8",
            'enable-local-file-access': None,
            'print-media-type': None,
            'no-outline': None,
            'disable-smart-shrinking': None, 
            'zoom': '1.0' # <--- Asegura la escala 1:1
        }
        
        if contexto['tipo_documento'] == 'DIPLOMA':
            options['orientation'] = 'Landscape'
            html = render_template('certificados/base_diploma.html', **contexto)
        else:
            options['orientation'] = 'Portrait'
            html = render_template('certificados/base_constancia.html', **contexto)
            
        path_wkhtmltopdf = _resolver_wkhtmltopdf_path()
        if not path_wkhtmltopdf:
            raise RuntimeError(
                'wkhtmltopdf no está instalado o no se encontró. Define WKHTMLTOPDF_PATH o instala wkhtmltopdf.'
            )
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
        pdf_binario = pdfkit.from_string(html, False, options=options, configuration=config)
        return pdf_binario
    except Exception as e:
        try:
            current_app.logger.exception('Error generando PDF')
        except Exception:
            print(f"Error generando PDF: {e}")
        return None
    finally:
        conn.close()


def obtener_datos_empleado(matricula_id):
    """Obtiene el nombre y número de empleado para una matrícula."""
    conn = get_db_connection()
    try:
        query = '''
            SELECT d.nombre_completo, d.numero_empleado
            FROM matriculas m
            JOIN docentes d ON m.numero_empleado = d.numero_empleado
            WHERE m.id = ? AND m.aprobado = 1
        '''
        datos = conn.execute(query, (matricula_id,)).fetchone()
        
        if not datos:
            return None, None
        
        return dict(datos)['nombre_completo'], dict(datos)['numero_empleado']
    except Exception:
        return None, None
    finally:
        conn.close()
