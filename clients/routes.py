from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from models import Client, Apartment, ChatMessage, ClientPhoto
from extensions import db, socketio
from flask_socketio import emit, join_room
from datetime import datetime
from models import PaymentProof
from utils import allowed_file



client_bp = Blueprint('clients', __name__, template_folder='../templates/clients')

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@client_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        access_code = request.form['access_code']
        photo = request.files.get('photo')

        apartment = Apartment.query.filter_by(code=access_code).first()
        if not apartment:
            flash('Código inválido.', 'danger')
            return redirect(url_for('clients.register'))

        filename = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(UPLOAD_FOLDER, filename))

        hashed_password = generate_password_hash(password)
        new_client = Client(username=username, password=hashed_password,
                            access_code=access_code, photo=filename,
                            apartment_id=apartment.id)
        db.session.add(new_client)
        db.session.commit()

        flash('Registro exitoso.', 'success')
        return redirect(url_for('clients.login'))
    return render_template('clients/register.html')

@client_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        client = Client.query.filter_by(username=username).first()
        if client and check_password_hash(client.password, password):
            session['client_id'] = client.id
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('clients.dashboard'))
        else:
            flash('Credenciales incorrectas.', 'danger')

    return render_template('clients/login.html')
# Panel principal
@client_bp.route('/dashboard', methods=['GET'])
def dashboard():
    if 'client_id' not in session:
        flash('Por favor, inicie sesión primero.', 'danger')
        return redirect(url_for('clients.login'))

    client = Client.query.get(session['client_id'])
    if not client:
        flash('Cliente no encontrado.', 'danger')
        return redirect(url_for('clients.login'))

    apartment = client.apartment
    floor = getattr(apartment, 'floor', None)
    building = getattr(floor, 'building', None)

    # Obtener todos los mensajes relevantes
    chat_messages = ChatMessage.query.filter(
        ((ChatMessage.sender_id == client.id) & (ChatMessage.sender_type == 'client')) |
        ((ChatMessage.receiver_id == client.id) & (ChatMessage.sender_type == 'admin')) |
        (ChatMessage.receiver_id == None)  # Mensajes generales
    ).order_by(ChatMessage.timestamp).all()

    additional_photos = ClientPhoto.query.filter_by(client_id=client.id).all()

    return render_template('clients/dashboard.html', client=client, apartment=apartment,
                           floor=floor, building=building, chat_messages=chat_messages,
                           additional_photos=additional_photos)

# Subir foto adicional
@client_bp.route('/add_photo', methods=['POST'])
def add_photo():
    if 'client_id' not in session:
        flash('Por favor, inicie sesión primero.', 'danger')
        return redirect(url_for('clients.login'))

    client = Client.query.get(session['client_id'])
    if not client:
        flash('Cliente no encontrado.', 'danger')
        return redirect(url_for('clients.login'))

    photo = request.files.get('photo')
    if photo and allowed_file(photo.filename):
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(UPLOAD_FOLDER, filename))

        new_photo = ClientPhoto(
            filename=filename,
            client_id=client.id,
            access_code=client.access_code
        )
        db.session.add(new_photo)
        db.session.commit()

        flash('Foto subida exitosamente.', 'success')
    else:
        flash('Error al subir la foto. Verifique el formato.', 'danger')

    return redirect(url_for('clients.dashboard'))

# Eliminar foto adicional
# Eliminar foto adicional
@client_bp.route('/delete_photo', methods=['POST'])
def delete_photo():
    if 'client_id' not in session:
        flash('Por favor, inicie sesión primero.', 'danger')
        return redirect(url_for('clients.login'))

    photo_id = request.form.get('photo_id')
    if not photo_id:
        flash('ID de foto no proporcionado.', 'danger')
        return redirect(url_for('clients.dashboard'))

    try:
        photo_id = int(photo_id)
    except ValueError:
        flash('ID de foto inválido.', 'danger')
        return redirect(url_for('clients.dashboard'))

    photo = ClientPhoto.query.get(photo_id)

    if photo and photo.client_id == session['client_id']:
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        if not upload_folder:
            flash('Carpeta de subida no está configurada.', 'danger')
            return redirect(url_for('clients.dashboard'))
        
        photo_path = os.path.join(upload_folder, photo.filename)
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
                flash('Archivo de foto eliminado del servidor.', 'success')
            except Exception as e:
                flash('Error al eliminar el archivo de la foto.', 'danger')
                print(f"Error al eliminar el archivo: {e}")
                return redirect(url_for('clients.dashboard'))
        else:
            flash('Archivo de foto no encontrado en el servidor.', 'warning')

        try:
            db.session.delete(photo)
            db.session.commit()
            flash('Foto eliminada con éxito.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al eliminar la foto de la base de datos.', 'danger')
            print(f"Error al eliminar la foto de DB: {e}")
    else:
        flash('Foto no encontrada o no autorizada.', 'danger')

    return redirect(url_for('clients.dashboard'))

# Enviar mensaje al administrador

@client_bp.route('/send_message', methods=['POST'])
def send_message():
    try:
        content = request.form.get('content', '').strip()
        sender_id = session.get('client_id')
        media = request.files.get('media')

        if not sender_id:
            flash('El cliente no está autenticado.', 'danger')
            return redirect(url_for('clients.login'))

        if not content and not media:
            flash('Debe enviar un mensaje o un archivo.', 'warning')
            return redirect(url_for('clients.dashboard'))

        media_filename = None
        if media and allowed_file(media.filename):
            media_filename = secure_filename(media.filename)
            media_path = os.path.join(UPLOAD_FOLDER, media_filename)
            media.save(media_path)
        elif media and not allowed_file(media.filename):
            flash('Formato de archivo no permitido.', 'danger')
            return redirect(url_for('clients.dashboard'))

        # Guardar el mensaje en la base de datos
        new_message = ChatMessage(
            sender_type='client',
            sender_id=sender_id,
            receiver_id=1,  # ID del administrador
            content=content,
            media=media_filename
        )
        db.session.add(new_message)
        db.session.commit()

        # Emitir el mensaje al administrador
        socketio.emit('receive_message', {
            'sender_type': 'client',
            'sender_id': sender_id,
            'receiver_id': 1,  # ID del administrador
            'content': content,
            'media': media_filename,
            'timestamp': str(new_message.timestamp)
        }, room='admin_room')  # Asegúrate de que el administrador está unido a 'admin_room'

        flash('Mensaje enviado correctamente.', 'success')
        return redirect(url_for('clients.dashboard'))
    except Exception as e:
        print(f"Error al enviar el mensaje: {e}")
        flash('Error interno al enviar el mensaje.', 'danger')
        return redirect(url_for('clients.dashboard'))

@client_bp.route('/clear_chat', methods=['POST'])
def clear_chat():
    """
    Limpiar el chat del cliente (mensajes entre el cliente y el administrador).
    """
    if 'client_id' not in session:
        flash('No autenticado. Por favor, inicia sesión.', 'danger')
        return redirect(url_for('clients.login'))

    client_id = session['client_id']

    try:
        # Eliminar los mensajes del chat del cliente
        ChatMessage.query.filter(
            ((ChatMessage.sender_id == client_id) & (ChatMessage.sender_type == 'client')) |
            ((ChatMessage.receiver_id == client_id) & (ChatMessage.sender_type == 'admin')) |
            (ChatMessage.receiver_id == None)  # Mensajes generales
        ).delete(synchronize_session=False)
        db.session.commit()

        # Emitir un evento a través de SocketIO si es necesario
        socketio.emit('chat_cleared', {'message': 'Chat limpiado correctamente.'}, room=f'client_{client_id}')

        flash('Chat limpiado correctamente.', 'success')
        return redirect(url_for('clients.dashboard'))
    except Exception as e:
        print(f"Error al limpiar el chat: {e}")
        flash('Error al limpiar el chat.', 'danger')
        return redirect(url_for('clients.dashboard'))


# Enviar comprobante de pago
@client_bp.route('/send_payment', methods=['POST'])
def send_payment():
    if 'client_id' not in session:
        flash('Por favor, inicie sesión primero.', 'danger')
        return redirect(url_for('clients.login'))

    payment_file = request.files.get('payment_proof')
    if payment_file:
        filename = secure_filename(payment_file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, 'payments', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        payment_file.save(file_path)

        new_payment = PaymentProof(
            client_id=session['client_id'],
            filename=filename,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_payment)
        db.session.commit()

        flash('Comprobante de pago enviado correctamente.', 'success')
    else:
        flash('Por favor, sube un archivo de comprobante.', 'danger')

    return redirect(url_for('clients.dashboard'))

# Cerrar sesión
@client_bp.route('/logout')
def logout():
    session.pop('client_id', None)
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('clients.login'))

