from flask import Blueprint, request, redirect, url_for, flash, session, make_response, current_app
from utils import admin_requerido
from services.certificate_service import registrar_plantilla, generar_binario_pdf, actualizar_plantilla, eliminar_plantilla

certificados_bp = Blueprint('certificados', __name__)

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
    file = request.files.get('fondo_img')
    
    if not file or file.filename == '':
        flash('Debes seleccionar una imagen de fondo.', 'danger')
        return redirect(url_for('admin', view='certificados'))
        
    if not es_superadmin and direccion_codigo != admin_direccion:
        flash('No tienes permiso para crear plantillas para otra dirección.', 'danger')
        return redirect(url_for('admin', view='certificados'))
        
    try:
        registrar_plantilla(
            direccion_codigo=direccion_codigo,
            nombre_plantilla=nombre_plantilla,
            tipo_documento=tipo_documento,
            file=file,
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
    file = request.files.get('fondo_img')
    
    try:
        actualizar_plantilla(
            id_plantilla=id_plantilla,
            direccion_codigo=direccion_codigo,
            nombre_plantilla=nombre_plantilla,
            tipo_documento=tipo_documento,
            file=file,
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

@certificados_bp.route('/descargar_certificado/<int:matricula_id>')
def descargar_certificado(matricula_id):
    if not session.get('empleado_portal'):
        return redirect(url_for('login'))
        
    # El servicio ya valida que la matrícula esté aprobada = 1
    pdf_binario = generar_binario_pdf(matricula_id)
    
    if not pdf_binario:
        flash('El certificado no está disponible o el curso no ha sido aprobado.', 'danger')
        return redirect(url_for('dashboard'))
        
    response = make_response(pdf_binario)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=certificado_{matricula_id}.pdf'
    return response
