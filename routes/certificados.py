from flask import Blueprint, request, redirect, url_for, flash, session, make_response, current_app, abort
from utils import admin_requerido, validar_csrf
from services.admin_service import actualizar_identidad_direccion
import os
from services.certificate_service import (
    registrar_plantilla,
    generar_binario_pdf,
    actualizar_plantilla,
    eliminar_plantilla,
    obtener_plantilla_por_id,
    generar_html_preview_plantilla,
    obtener_datos_empleado,
)

certificados_bp = Blueprint('certificados', __name__)

@certificados_bp.route('/admin/certificados/identidad', methods=['POST'])
@admin_requerido
def configurar_identidad():
    if not validar_csrf(request.form.get('_csrf_token')):
        abort(403)
        
    es_superadmin = session.get('admin_rol') == 'superadmin'
    admin_direccion = session.get('admin_direccion')
    
    direccion_codigo = request.form.get('direccion_codigo')
    if not es_superadmin:
        direccion_codigo = admin_direccion
        
    if not direccion_codigo:
        flash('Debes especificar una dirección válida.', 'danger')
        return redirect(url_for('admin', view='certificados'))
        
    file_firma = request.files.get('firma_img')
    file_logo = request.files.get('logo_img')
    
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'direcciones')
    resultado = actualizar_identidad_direccion(direccion_codigo, file_firma, file_logo, upload_dir)
    
    if resultado.get('ok'):
        flash('Identidad visual actualizada correctamente.', 'success')
    else:
        flash(f"Error al actualizar la identidad: {resultado.get('error', 'Desconocido')}", 'danger')
        
    return redirect(url_for('admin', view='certificados'))


@certificados_bp.route('/admin/certificados/plantilla', methods=['POST'])
@admin_requerido
def crear_plantilla():
    # Solo superadmin o admin de la dirección
    es_superadmin = session.get('admin_rol') == 'superadmin'
    admin_direccion = session.get('admin_direccion')
    
    direccion_codigo = request.form.get('direccion_codigo')
    
    # Si no es superadmin, forzamos su propia dirección
    if not es_superadmin:
        direccion_codigo = admin_direccion
        
    if not direccion_codigo:
        flash('Debes especificar una dirección válida.', 'danger')
        return redirect(url_for('admin', view='certificados'))
    nombre_plantilla = request.form.get('nombre_plantilla')
    tipo_documento = request.form.get('tipo_documento')
    firmante_nombre = request.form.get('firmante_nombre')
    firmante_cargo = request.form.get('firmante_cargo')
    texto_certificado = request.form.get('texto_certificado', '')

    if not (texto_certificado or '').strip():
        flash('Debes ingresar el texto del certificado.', 'danger')
        return redirect(url_for('admin', view='certificados'))
        
    if not es_superadmin and direccion_codigo != admin_direccion:
        flash('No tienes permiso para crear plantillas para otra dirección.', 'danger')
        return redirect(url_for('admin', view='certificados'))
        
    try:
        registrar_plantilla(
            direccion_codigo=direccion_codigo,
            nombre_plantilla=nombre_plantilla,
            tipo_documento=tipo_documento,
            texto_certificado=texto_certificado,
            firmante_nombre=firmante_nombre,
            firmante_cargo=firmante_cargo
        )
        flash('Plantilla registrada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al registrar plantilla: {str(e)}', 'danger')
        
    return redirect(url_for('admin', view='certificados'))

@certificados_bp.route('/admin/certificados/plantilla/editar/<int:id_plantilla>', methods=['POST'])
@admin_requerido
def editar_plantilla_route(id_plantilla):
    es_superadmin = session.get('admin_rol') == 'superadmin'
    admin_direccion = session.get('admin_direccion')
    
    direccion_codigo = request.form.get('direccion_codigo')
    if not es_superadmin:
        direccion_codigo = admin_direccion
        
    nombre_plantilla = request.form.get('nombre_plantilla')
    tipo_documento = request.form.get('tipo_documento')
    firmante_nombre = request.form.get('firmante_nombre')
    firmante_cargo = request.form.get('firmante_cargo')
    texto_certificado = request.form.get('texto_certificado', '')
    
    try:
        actualizar_plantilla(
            id_plantilla=id_plantilla,
            direccion_codigo=direccion_codigo,
            nombre_plantilla=nombre_plantilla,
            tipo_documento=tipo_documento,
            texto_certificado=texto_certificado,
            firmante_nombre=firmante_nombre,
            firmante_cargo=firmante_cargo
        )
        flash('Plantilla actualizada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar plantilla: {str(e)}', 'danger')
        
    return redirect(url_for('admin', view='certificados'))

@certificados_bp.route('/admin/certificados/plantilla/eliminar/<int:id_plantilla>', methods=['POST'])
@admin_requerido
def eliminar_plantilla_route(id_plantilla):
    try:
        eliminar_plantilla(id_plantilla)
        flash('Plantilla eliminada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar plantilla: {str(e)}', 'danger')
        
    return redirect(url_for('admin', view='certificados'))

@certificados_bp.route('/admin/certificados/plantilla/preview/<int:id_plantilla>')
@admin_requerido
def preview_plantilla_route(id_plantilla):
    plantilla = obtener_plantilla_por_id(id_plantilla)
    if not plantilla:
        return (
            '<h3>Plantilla no encontrada</h3>',
            404,
            {'Content-Type': 'text/html; charset=utf-8'},
        )

    es_superadmin = session.get('admin_rol') == 'superadmin'
    admin_direccion = session.get('admin_direccion')
    if not es_superadmin and plantilla.get('direccion_codigo') != admin_direccion:
        return (
            '<h3>No autorizado</h3>',
            403,
            {'Content-Type': 'text/html; charset=utf-8'},
        )

    html = generar_html_preview_plantilla(plantilla)
    if not html:
        return (
            '<h3>Vista previa no disponible</h3>'
            '<p>La plantilla necesita una firma PNG para renderizarse.</p>',
            409,
            {'Content-Type': 'text/html; charset=utf-8'},
        )

    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

@certificados_bp.route('/descargar_certificado/<int:matricula_id>')
def descargar_certificado(matricula_id):
    if not session.get('empleado_portal'):
        return redirect(url_for('login'))
        
    # El servicio ya valida que la matrícula esté aprobada = 1
    pdf_binario = generar_binario_pdf(matricula_id)
    
    if not isinstance(pdf_binario, (bytes, bytearray)):
        return (
            '<h3>Certificado no disponible</h3>'
            '<p>Este certificado no está configurado todavía (plantilla incompleta) o la matrícula no ha sido aprobada.</p>',
            409,
            {'Content-Type': 'text/html; charset=utf-8'},
        )
    
    # Obtener nombre y número de empleado para el nombre del archivo
    nombre_empleado, numero_empleado, tipo_documento = obtener_datos_empleado(matricula_id)
    tipo_archivo = (tipo_documento or 'Certificado').strip().title() or 'Certificado'
    prefijo_archivo = tipo_archivo.replace(' ', '_')
    
    # Construir nombre del archivo
    if nombre_empleado and numero_empleado:
        nombre_archivo = f'{prefijo_archivo}_{numero_empleado}_{nombre_empleado.replace(" ", "_")}.pdf'
    else:
        nombre_archivo = f'{prefijo_archivo}_{matricula_id}.pdf'
        
    response = make_response(pdf_binario)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
    response.headers['Content-Length'] = str(len(pdf_binario))
    return response