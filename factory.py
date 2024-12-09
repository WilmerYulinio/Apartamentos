# factory.py
import os
from flask import Flask
from extensions import db, migrate, socketio, csrf
from clients.routes import client_bp
from administracion.routes import admin_bp
from main_routes import register_routes
from flask_wtf.csrf import generate_csrf
from main_routes import main_bp
from dotenv import load_dotenv
def create_app():
    app = Flask(__name__)

    # Configuración de la aplicación
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///apartamentos.db').replace("postgres://", "postgresql://")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'una_clave_secreta_muy_segura_y_unica'
    app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken'] 
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicialización de extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins=os.environ.get('CORS_ALLOWED_ORIGINS', '*'), manage_session=False)
    csrf.init_app(app)
    load_dotenv()
    
    # Registrar rutas
    app.register_blueprint(main_bp)
    app.register_blueprint(client_bp, url_prefix='/clients')
    app.register_blueprint(admin_bp, url_prefix='/administracion')

    # Función para generar el token CSRF
    def generate_csrf_token():
        return csrf.generate_csrf()

    app.jinja_env.globals['csrf_token'] = generate_csrf_token

    return app

