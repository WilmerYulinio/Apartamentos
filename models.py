from datetime import datetime
from extensions import db


class Owner(db.Model):
    __tablename__ = 'owners'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    photo = db.Column(db.String(200), nullable=True)
    buildings = db.relationship('Building', backref='owner', cascade='all, delete-orphan')


class Building(db.Model):
    __tablename__ = 'buildings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)
    photo = db.Column(db.String(200), nullable=True)
    floors = db.relationship('Floor', backref='building', cascade='all, delete-orphan', lazy=True)


class Floor(db.Model):
    __tablename__ = 'floors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    apartments = db.relationship('Apartment', backref='floor', cascade='all, delete-orphan', lazy=True)


class Apartment(db.Model):
    __tablename__ = 'apartments'
    id = db.Column(db.Integer, primary_key=True)
    size = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id'), nullable=False)
    media = db.relationship('ApartmentMedia', backref='apartment', cascade='all, delete-orphan', lazy=True)
    clients = db.relationship('Client', backref='apartment', lazy=True)


class ApartmentMedia(db.Model):
    __tablename__ = 'apartment_media'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(50), nullable=False)
    apartment_id = db.Column(db.Integer, db.ForeignKey('apartments.id'), nullable=False)


class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    access_code = db.Column(db.String(50), unique=True, nullable=False)
    photo = db.Column(db.String(200), nullable=True)
    apartment_id = db.Column(db.Integer, db.ForeignKey('apartments.id'), nullable=True)
    photos = db.relationship('ClientPhoto', backref='client', lazy=True)
    payments = db.relationship('PaymentProof', backref='client', lazy=True)
    messages = db.relationship('ChatMessage', backref='client', lazy=True)


class ClientPhoto(db.Model):
    __tablename__ = 'client_photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    access_code = db.Column(db.String(100), nullable=False)


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_type = db.Column(db.String(50), nullable=False)
    sender_id = db.Column(db.Integer, nullable=False)
    receiver_id = db.Column(db.Integer, nullable=True)  # Opcional si es un mensaje global
    content = db.Column(db.Text, nullable=True)  # El mensaje puede ser opcional
    media = db.Column(db.String(200), nullable=True)  # Ruta del archivo multimedia opcional
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)



class PaymentProof(db.Model):
    __tablename__ = 'payment_proof'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    photo = db.Column(db.String(200), nullable=True)
