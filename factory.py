# factory.py
import os
from flask import Flask
from extensions import db, socketio, csrf
from flask_migrate import Migrate
from clients.routes import client_bp
from administracion.routes import admin_bp
from main_routes import main_bp
from flask_wtf.csrf import generate_csrf
from dotenv import load_dotenv
from api.routes import api_bp

def create_app():
    app = Flask(__name__)
    load_dotenv()  # Cargar variables de entorno desde el archivo .env

    # Configuración de la aplicación
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'sqlite:///apartamentos.db'  # Base de datos SQLite por defecto si no se encuentra DATABASE_URL
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_segura_y_unica')

    app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken']
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicialización de extensiones
    db.init_app(app)
    migrate = Migrate(app, db)  # Inicializar Flask-Migrate
    socketio.init_app(app, cors_allowed_origins=os.environ.get('CORS_ALLOWED_ORIGINS', '*'), manage_session=False)
    csrf.init_app(app)

    # Registrar Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(client_bp, url_prefix='/clients')
    app.register_blueprint(admin_bp, url_prefix='/administracion')
    app.register_blueprint(api_bp, url_prefix='/api')
    # Función para generar el token CSRF
    def generate_csrf_token():
        return csrf.generate_csrf()

    app.jinja_env.globals['csrf_token'] = generate_csrf_token

    return app
