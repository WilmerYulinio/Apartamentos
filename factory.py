from flask import Flask
from extensions import db, socketio, csrf
from flask_migrate import Migrate, upgrade
from clients.routes import client_bp
from administracion.routes import admin_bp
from main_routes import main_bp
from flask_wtf.csrf import generate_csrf
from dotenv import load_dotenv
import os
import pymysql

pymysql.install_as_MySQLdb()

def create_app():
    app = Flask(__name__)
    load_dotenv()

    # Configuración de la aplicación
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('MYSQL_URL')  # Usar MYSQL_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_segura_y_unica')
    app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken']
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicialización de extensiones
    db.init_app(app)
    Migrate(app, db)
    socketio.init_app(app, cors_allowed_origins=os.environ.get('CORS_ALLOWED_ORIGINS', '*'), manage_session=False)
    csrf.init_app(app)

    # Registrar Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(client_bp, url_prefix='/clients')
    app.register_blueprint(admin_bp, url_prefix='/administracion')

    # Función para generar el token CSRF
    def generate_csrf_token():
        return csrf.generate_csrf()

    app.jinja_env.globals['csrf_token'] = generate_csrf_token
# @csrf.exempt
# @app.route('/migrate/run', methods=['POST'])
# def run_migrations():
#     """Endpoint temporal para ejecutar migraciones en el servidor."""
#     try:
#         upgrade()
#         return "Migraciones aplicadas exitosamente", 200
#     except Exception as e:
#         return f"Error al ejecutar migraciones: {str(e)}", 500



    return app

# Asegúrate de que este objeto esté disponible para Gunicorn
app = create_app()
