from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from werkzeug.utils import secure_filename
from models import Admin, ChatMessage, PaymentProof, Apartment, Client
import os
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db
from flask_socketio import emit
from extensions import socketio
from utils import allowed_file

admin_bp = Blueprint('administracion', __name__, template_folder='../templates/administracion')

@admin_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        photo = request.files.get('photo')
        
        existing_admin = Admin.query.filter_by(username=username).first()
        if existing_admin:
            flash('El nombre de usuario ya está en uso', 'error')
            return redirect(url_for('administracion.register'))

        photo_filename = 'default.jpg'
        if photo and allowed_file(photo.filename):
            photo_filename = secure_filename(photo.filename)
            photo_path = os.path.join('static/uploads/admins', photo_filename)
            os.makedirs(os.path.dirname(photo_path), exist_ok=True)
            photo.save(photo_path)

        hashed_password = generate_password_hash(password)
        new_admin = Admin(username=username, password=hashed_password, photo=photo_filename)
        db.session.add(new_admin)
        db.session.commit()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('administracion.login'))

    return render_template('administracion/register.html')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('administracion.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('administracion/login.html')

@admin_bp.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        flash("Debes iniciar sesión primero.", "danger")
        return redirect(url_for('administracion.login'))

    admin = Admin.query.get(session['admin_id'])
    if not admin:
        flash("Administrador no encontrado.", "danger")
        return redirect(url_for('administracion.login'))

    clients = Client.query.all()

    # Obtener el modo de chat y el cliente seleccionado
    chat_mode = request.args.get('chat_mode', 'general')
    selected_client_id = request.args.get('client_id', None)

    if chat_mode == 'general':
        chat_messages = ChatMessage.query.filter_by(receiver_id=None).order_by(ChatMessage.timestamp).all()
    elif chat_mode == 'individual' and selected_client_id:
        chat_messages = ChatMessage.query.filter(
            ((ChatMessage.sender_id == int(selected_client_id)) & (ChatMessage.sender_type == 'client')) |
            ((ChatMessage.receiver_id == int(selected_client_id)) & (ChatMessage.sender_type == 'admin'))
        ).order_by(ChatMessage.timestamp).all()
    else:
        chat_messages = []

    # Añadir sender_username a cada mensaje
    for message in chat_messages:
        if message.sender_type == 'admin':
            message.sender_username = 'Administrador'
        elif message.sender_type == 'client':
            client = Client.query.get(message.sender_id)
            message.sender_username = client.username if client else 'Cliente'
        else:
            message.sender_username = 'Desconocido'

    return render_template(
        'administracion/dashboard.html',
        admin=admin,
        clients=clients,
        chat_mode=chat_mode,
        selected_client_id=selected_client_id,
        chat_messages=chat_messages
    )

@admin_bp.route('/send_message', methods=['POST'])
def send_message():
    try:
        content = request.form.get('content', '').strip()
        media = request.files.get('media')
        chat_mode = request.form.get('chat_mode', 'general')
        receiver_id = request.form.get('client_id', None)

        if not content and not media:
            flash('Debes escribir un mensaje o adjuntar un archivo.', 'warning')
            return redirect(url_for('administracion.dashboard', chat_mode=chat_mode, client_id=receiver_id))

        media_filename = None
        if media and allowed_file(media.filename):
            media_filename = secure_filename(media.filename)
            media_path = os.path.join('static/uploads', media_filename)
            os.makedirs(os.path.dirname(media_path), exist_ok=True)
            media.save(media_path)
        elif media and not allowed_file(media.filename):
            flash('Formato de archivo no permitido.', 'danger')
            return redirect(url_for('administracion.dashboard', chat_mode=chat_mode, client_id=receiver_id))

        # Crear mensaje
        new_message = ChatMessage(
            sender_type='admin',
            sender_id=session.get('admin_id'),
            receiver_id=int(receiver_id) if chat_mode == 'individual' and receiver_id else None,
            content=content,
            media=media_filename
        )
        db.session.add(new_message)
        db.session.commit()

        # Emitir mensaje
        if chat_mode == 'individual' and receiver_id:
            room = f'client_{receiver_id}'
        else:
            room = 'general'

        socketio.emit('receive_message', {
            'sender_type': 'admin',
            'sender_id': session.get('admin_id'),
            'receiver_id': int(receiver_id) if receiver_id else None,
            'content': content,
            'media': media_filename,
            'timestamp': str(new_message.timestamp),
            'sender_username': 'Administrador'
        }, room=room)

        flash('Mensaje enviado correctamente.', 'success')
        return redirect(url_for('administracion.dashboard', chat_mode=chat_mode, client_id=receiver_id))
    except Exception as e:
        print(f"Error al enviar el mensaje: {e}")
        flash('Error interno al enviar el mensaje.', 'danger')
        return redirect(url_for('administracion.dashboard', chat_mode=chat_mode, client_id=receiver_id))

@admin_bp.route('/logout')
def logout():
    session.pop('admin_id', None)
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('administracion.login'))
