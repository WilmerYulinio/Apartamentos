from flask_socketio import SocketIO, emit, join_room
from flask import session
from models import ChatMessage, db

socketio = SocketIO()

def init_socketio(app):
    socketio.init_app(app)



@socketio.on('connect')
def handle_connect():
    if 'client_id' in session:
        client_id = session['client_id']
        join_room(f'client_{client_id}')
        print(f"Cliente {client_id} unido a la sala client_{client_id}")
    elif 'admin_id' in session:
        join_room('admin_room')
        print("Administrador unido a la sala admin_room")

@socketio.on('join')
def handle_join(data):
    if 'client_id' in data:
        client_id = data['client_id']
        join_room(f'client_{client_id}')
        print(f"Cliente {client_id} unido a la sala client_{client_id}")
    elif 'admin_id' in data:
        join_room('admin_room')
        print("Administrador unido a la sala admin_room")



@socketio.on('disconnect')
def handle_disconnect():
    print("Usuario desconectado.")

@socketio.on('send_message')
def handle_message(data):
    """
    Manejar el envío de mensajes desde cliente o administrador.
    """
    sender_type = data.get('sender_type')
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    content = data.get('content')

    if not sender_type or not sender_id or not content:
        emit('error', {'message': 'Datos incompletos.'})
        return

    # Guardar mensaje en la base de datos
    new_message = ChatMessage(
        sender_type=sender_type,
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(new_message)
    db.session.commit()

    # Emitir el mensaje
    room = f'client_{receiver_id}' if sender_type == 'admin' else 'admin'
    emit('receive_message', {
        'sender_type': sender_type,
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'content': content,
        'timestamp': str(new_message.timestamp)
    }, room=room)

@socketio.on('clear_chat')
def handle_clear_chat(data):
    """
    Manejar la limpieza completa del chat.
    """
    ChatMessage.query.delete()
    db.session.commit()
    emit('chat_cleared', {'message': 'Chat limpiado.'}, broadcast=True)
