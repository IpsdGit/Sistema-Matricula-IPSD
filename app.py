# pyrefly: ignore [missing-import]
from flask import Flask, render_template, send_from_directory, request, g
import os
import logging
import time
from logging.handlers import RotatingFileHandler

from config import configure_app
from database import asegurar_migraciones_minimas
from routes.admin import register_admin_routes
from routes.chat import register_chat_routes
from routes.portal import register_portal_routes
from routes.certificados import certificados_bp
from routes.validacion import validacion_bp
from utils import generar_csrf_token


# ── Configuración de Logging Centralizado ────────────────────────────────────
def configurar_logging(app: Flask) -> None:
    """Configura el sistema de logging estructurado de la aplicación."""
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s (%(funcName)s:%(lineno)d): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Logging a consola (siempre activo)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Logging a archivo rotativo en producción
    if not app.debug:
        log_dir = os.path.join(app.root_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'sistema_unah.log'),
            maxBytes=10 * 1024 * 1024,  # 10 MB por archivo
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(log_format)
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    app.logger.info('Sistema UNAH iniciado. Logging configurado correctamente.')


app = Flask(__name__)
configure_app(app)
configurar_logging(app)

asegurar_migraciones_minimas()

app.jinja_env.globals['csrf_token'] = generar_csrf_token


# ── Cache Busting Dinámico ───────────────────────────────────────────────────
@app.template_filter('cache_bust')
def cache_bust_filter(filename: str) -> str:
    """Filtro Jinja que añade el timestamp del archivo como query param."""
    ruta_absoluta = os.path.join(app.static_folder, filename)
    try:
        ts = int(os.path.getmtime(ruta_absoluta))
    except OSError:
        ts = 0
    return f"/static/{filename}?v={ts}"

app.jinja_env.globals['cache_bust'] = cache_bust_filter


# ── Logging de cada Request ──────────────────────────────────────────────────
@app.before_request
def log_request_start():
    g.start_time = time.time()


@app.after_request
def log_request_end(response):
    duration_ms = round((time.time() - getattr(g, 'start_time', time.time())) * 1000, 1)
    # Solo logear errores o requests lentos (>1s) para no saturar el log
    if response.status_code >= 400:
        app.logger.warning(
            '%s %s → %s (%.1fms) | IP: %s',
            request.method, request.path,
            response.status_code, duration_ms,
            request.remote_addr
        )
    elif duration_ms > 1000:
        app.logger.info(
            'LENTO: %s %s → %s (%.1fms)',
            request.method, request.path,
            response.status_code, duration_ms
        )
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


register_portal_routes(app)
register_admin_routes(app)
register_chat_routes(app)
app.register_blueprint(certificados_bp)
app.register_blueprint(validacion_bp)


@app.route('/uploads/direcciones/<codigo_direccion>/<filename>')
def uploaded_file(codigo_direccion, filename):
    directorio = os.path.join(app.config['UPLOAD_FOLDER'], 'direcciones', codigo_direccion)
    return send_from_directory(directorio, filename)


# ── Manejadores de Error HTTP ────────────────────────────────────────────────
@app.errorhandler(400)
def bad_request(e):
    app.logger.warning('400 Bad Request: %s | URL: %s', str(e), request.url)
    return render_template('index.html', error='Solicitud inválida.'), 400


@app.errorhandler(403)
def forbidden(e):
    app.logger.warning('403 Forbidden: %s | URL: %s | IP: %s', str(e), request.url, request.remote_addr)
    return render_template('index.html', error='Acceso denegado. Token de seguridad inválido.'), 403


@app.errorhandler(404)
def not_found(e):
    app.logger.info('404 Not Found: %s', request.url)
    return render_template('index.html', error='Página no encontrada.'), 404


@app.errorhandler(500)
def internal_error(e):
    app.logger.exception('500 Internal Server Error: %s | URL: %s', str(e), request.url)
    return render_template('index.html', error='Error interno del servidor. El equipo ha sido notificado.'), 500


@app.errorhandler(Exception)
def unhandled_exception(e):
    app.logger.exception('Excepción no manejada: %s | URL: %s | IP: %s', str(e), request.url, request.remote_addr)
    return render_template('index.html', error='Ocurrió un error inesperado. Por favor intenta de nuevo.'), 500


if __name__ == '__main__':
    app.run(debug=True)
