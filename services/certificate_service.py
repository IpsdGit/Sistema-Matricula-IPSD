import os
import pdfkit
from flask import render_template, current_app
from werkzeug.utils import secure_filename
from database import get_db_connection

def registrar_plantilla(direccion_codigo, nombre_plantilla, tipo_documento, file, firmante_nombre, firmante_cargo):
    # Guardar archivo
    filename = secure_filename(file.filename)
    upload_folder = os.path.join(current_app.root_path, 'static', 'certificados', 'fondos')
    os.makedirs(upload_folder, exist_ok=True)
    
    # Asegurar nombre único agregando un timestamp simple o usando el nombre tal cual (sobreescribiendo si ya existe)
    import time
    filename = f"{int(time.time())}_{filename}"
    ruta_guardado = os.path.join(upload_folder, filename)
    file.save(ruta_guardado)
    
    ruta_db = f'/static/certificados/fondos/{filename}'
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO plantillas_certificados 
            (direccion_codigo, nombre_plantilla, tipo_documento, ruta_fondo_img, firmante_nombre, firmante_cargo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (direccion_codigo, nombre_plantilla, tipo_documento, ruta_db, firmante_nombre, firmante_cargo))
        conn.commit()
    finally:
        conn.close()

def actualizar_plantilla(id_plantilla, direccion_codigo, nombre_plantilla, tipo_documento, file, firmante_nombre, firmante_cargo):
    conn = get_db_connection()
    try:
        if file and file.filename != '':
            # Se proporcionó un nuevo archivo
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'certificados', 'fondos')
            os.makedirs(upload_folder, exist_ok=True)
            import time
            filename = f"{int(time.time())}_{filename}"
            ruta_guardado = os.path.join(upload_folder, filename)
            file.save(ruta_guardado)
            ruta_db = f'/static/certificados/fondos/{filename}'
            
            conn.execute('''
                UPDATE plantillas_certificados 
                SET direccion_codigo = ?, nombre_plantilla = ?, tipo_documento = ?, 
                    ruta_fondo_img = ?, firmante_nombre = ?, firmante_cargo = ?
                WHERE id = ?
            ''', (direccion_codigo, nombre_plantilla, tipo_documento, ruta_db, firmante_nombre, firmante_cargo, id_plantilla))
        else:
            # No se proporcionó un nuevo archivo, mantenemos el anterior
            conn.execute('''
                UPDATE plantillas_certificados 
                SET direccion_codigo = ?, nombre_plantilla = ?, tipo_documento = ?, 
                    firmante_nombre = ?, firmante_cargo = ?
                WHERE id = ?
            ''', (direccion_codigo, nombre_plantilla, tipo_documento, firmante_nombre, firmante_cargo, id_plantilla))
            
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
        plantillas = conn.execute('''
            SELECT * FROM plantillas_certificados 
            WHERE direccion_codigo = ? AND activo = 1
            ORDER BY id DESC
        ''', (direccion_codigo,)).fetchall()
        return [dict(p) for p in plantillas]
    finally:
        conn.close()

def obtener_todas_las_plantillas():
    conn = get_db_connection()
    try:
        plantillas = conn.execute('''
            SELECT * FROM plantillas_certificados 
            WHERE activo = 1
            ORDER BY id DESC
        ''').fetchall()
        return [dict(p) for p in plantillas]
    finally:
        conn.close()

def generar_binario_pdf(matricula_id):
    conn = get_db_connection()
    try:
        # Obtener datos de la matrícula, docente, curso y plantilla
        query = '''
            SELECT 
                d.nombre_completo as nombre_docente, d.numero_empleado,
                c.nombre as curso_nombre, c.modalidad, c.horas_totales, c.semanas_duracion, c.tipo_accion,
                p.tipo_documento, p.ruta_fondo_img, p.firmante_nombre, p.firmante_cargo,
                c.anio, c.mes, c.dia
            FROM matriculas m
            JOIN docentes d ON m.numero_empleado = d.numero_empleado
            JOIN capacitaciones c ON m.id_capacitacion = c.id
            JOIN plantillas_certificados p ON c.id_plantilla_certificado = p.id
            WHERE m.id = ? AND m.aprobado = 1
        '''
        datos = conn.execute(query, (matricula_id,)).fetchone()
        
        if not datos:
            return None
            
        contexto = dict(datos)
        
        # Necesitamos la ruta absoluta para pdfkit
        # Convertimos '/static/certificados/fondos/img.png' a 'C:/.../static/...'
        fondo_relativo = contexto['ruta_fondo_img'].lstrip('/')
        contexto['ruta_fondo_absoluta'] = os.path.join(current_app.root_path, fondo_relativo).replace('\\', '/')
        
        # Opciones de pdfkit
        options = {
            'page-size': 'Letter',
            'margin-top': '0',
            'margin-right': '0',
            'margin-bottom': '0',
            'margin-left': '0',
            'encoding': "UTF-8",
            'enable-local-file-access': True,
            'no-outline': None
        }
        
        if contexto['tipo_documento'] == 'DIPLOMA':
            options['orientation'] = 'Landscape'
            html = render_template('certificados/base_diploma.html', **contexto)
        else:
            options['orientation'] = 'Portrait'
            html = render_template('certificados/base_constancia.html', **contexto)
            
        path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
        pdf_binario = pdfkit.from_string(html, False, options=options, configuration=config)
        return pdf_binario
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return None
    finally:
        conn.close()
