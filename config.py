import os
import secrets

DB_ENV_VAR = 'DATABASE_URL'

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

MESES_ES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

HORARIOS_BASE = [
    '08:00 AM - 10:00 AM',
    '10:00 AM - 12:00 PM',
    '12:00 PM - 02:00 PM',
    '02:00 PM - 04:00 PM',
    '04:00 PM - 06:00 PM',
    '06:00 PM - 08:00 PM'
]

LIMITE_REPROBADO = 3
LIMITE_ABANDONO = 2

SECCIONES_DASHBOARD_PERMITIDAS = {'historial', 'disponibles', 'notificaciones', 'calendario'}
FILTROS_HISTORIAL_PERMITIDOS = {'todas', 'aprobadas', 'no_aprobadas', 'canceladas'}
FILTROS_NOTIFICACION_PERMITIDOS = {
    'todas',
    'nuevas',
    'asistencia',
    'resultados',
    'oportunidades',
    'certificados',
}
VISTAS_ADMIN_PERMITIDAS = {
    'dashboard',
    'cursos',
    'ediciones',
    'calendario',
    'matriculas',
    'usuarios',
    'certificados',
}


def configure_app(app):
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    # Llave secreta estable para evitar cierres de sesión en reinicios locales
    app.secret_key = os.environ.get('SECRET_KEY', 'ipsd_secret_key_development_only_12345')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'direcciones'), exist_ok=True)
