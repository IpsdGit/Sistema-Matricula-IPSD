# pyrefly: ignore [missing-import]
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from utils import admin_requerido
from services.reportes_service import obtener_reporte_jerarquico, generar_excel_y_registrar, obtener_historial_reportes
import json

reportes_bp = Blueprint('reportes', __name__)

@reportes_bp.route('/admin/reportes')
@admin_requerido
def reportes_dashboard():
    from routes.admin import _obtener_centros_regionales_admin
    centros_regionales = _obtener_centros_regionales_admin()
    
    # Parámetros de filtro
    anio = request.args.get('anio', '').strip()
    calendario = request.args.get('calendario', '').strip()
    periodo = request.args.get('periodo', '').strip()
    centro_regional = request.args.get('cur', '').strip()
    facultad = request.args.get('facultad', '').strip()
    
    admin_rol = session.get('admin_rol', 'admin')
    admin_direccion = session.get('admin_direccion', 'IPSD')
    
    res = obtener_reporte_jerarquico(anio, calendario, periodo, centro_regional, facultad, admin_rol, admin_direccion)
    jerarquia = res.get('jerarquia', [])
    
    historial = obtener_historial_reportes()

    # Pasar los filtros a la vista para mantener el estado
    filtros = {
        'anio': anio,
        'calendario': calendario,
        'periodo': periodo,
        'cur': centro_regional,
        'facultad': facultad
    }
    
    return render_template('admin/reportes.html', 
                          jerarquia=jerarquia, 
                          filtros=filtros,
                          historial=historial,
                          centros_regionales=centros_regionales)

@reportes_bp.route('/admin/reportes/exportar')
@admin_requerido
def exportar_reporte():
    anio = request.args.get('anio', '').strip()
    calendario = request.args.get('calendario', '').strip()
    periodo = request.args.get('periodo', '').strip()
    centro_regional = request.args.get('cur', '').strip()
    facultad = request.args.get('facultad', '').strip()
    
    admin_rol = session.get('admin_rol', 'admin')
    admin_direccion = session.get('admin_direccion', 'IPSD')

    # Obtener admin id 
    admin_id = session.get('admin_id') # Asegurarse que se guarda en sesión al loguear
    # Fallback si no está el id pero sí el user
    admin_username = session.get('admin_user', 'Admin')
    if not admin_id:
        admin_id = 1 # Fallback dummy si no logran arreglar la tabla a tiempo 

    res = obtener_reporte_jerarquico(anio, calendario, periodo, centro_regional, facultad, admin_rol, admin_direccion)
    filas_planas = res.get('filas_planas', [])
    
    if not filas_planas:
        flash('No hay datos para exportar con los filtros seleccionados.', 'warning')
        return redirect(url_for('reportes.reportes_dashboard', **request.args))
        
    titulo = f"Reporte Acciones Formativas"
    if anio: titulo += f" {anio}"
    if periodo: titulo += f" - {periodo}"
    
    parametros = {
        'anio': anio,
        'calendario': calendario,
        'periodo': periodo,
        'cur': centro_regional,
        'facultad': facultad
    }

    resultado_export = generar_excel_y_registrar(filas_planas, titulo, admin_id, admin_username, parametros, formato="Excel")
    
    if resultado_export['ok']:
        flash(f'Reporte generado con {resultado_export["total"]} registros.', 'success')
        # Redirigir al archivo físico generado
        return redirect(resultado_export['ruta_archivo'])
    else:
        flash('Hubo un error al generar el reporte.', 'danger')
        return redirect(url_for('reportes.reportes_dashboard'))

