from flask import Blueprint, render_template
from database import get_db_connection
from services import validacion_service

validacion_bp = Blueprint('validacion_bp', __name__)


@validacion_bp.route('/v/<token>')
def validar_token(token):
    """Ruta pública del validador de certificados. Accesible sin autenticación."""
    conn = get_db_connection()
    try:
        datos = validacion_service.validar_certificado(conn, token)
    finally:
        conn.close()

    return render_template('validador.html', datos=datos, token=token)
