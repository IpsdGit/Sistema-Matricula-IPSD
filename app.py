from flask import Flask, render_template

from config import configure_app
from database import asegurar_migraciones_minimas
from routes.admin import register_admin_routes
from routes.chat import register_chat_routes
from routes.portal import register_portal_routes
from routes.certificados import certificados_bp
from utils import generar_csrf_token

app = Flask(__name__)
configure_app(app)

asegurar_migraciones_minimas()
app.jinja_env.globals['csrf_token'] = generar_csrf_token


@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


register_portal_routes(app)
register_admin_routes(app)
register_chat_routes(app)
app.register_blueprint(certificados_bp)


@app.errorhandler(403)
def forbidden(e):
    return render_template('index.html', error='Acceso denegado. Token de seguridad inválido.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error='Página no encontrada.'), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template('index.html', error='Solicitud inválida.'), 400


if __name__ == '__main__':
    app.run(debug=False)
