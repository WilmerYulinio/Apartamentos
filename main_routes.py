# main_routes.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from werkzeug.utils import secure_filename
from random import randint
from models import Owner, Building, Floor, Apartment, ApartmentMedia, Client
from extensions import db
import os
from utils import allowed_file

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@main_bp.route('/owner_register', methods=['GET', 'POST'])
def owner_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if 'photo' not in request.files:
            flash('No se encontró el archivo', 'danger')
            return redirect(request.url)
        file = request.files['photo']
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            new_owner = Owner(username=username, password=password, photo=filename)
            db.session.add(new_owner)
            db.session.commit()
            flash('Registro exitoso', 'success')
            return redirect(url_for('main.owner_login'))
        else:
            flash('Tipo de archivo no permitido', 'danger')
            return redirect(request.url)
    return render_template('owner_register.html')


@main_bp.route('/owner_login', methods=['GET', 'POST'])
def owner_login():
    if request.method == 'POST':
        print("SESSION:", session)
        print("Token CSRF recibido:", request.form.get('csrf_token'))
        print("Token CSRF en sesión:", session.get('csrf_token'))
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Por favor, completa todos los campos.', 'warning')
            return redirect(url_for('main.owner_login'))

        owner = Owner.query.filter_by(username=username).first()

        if owner and owner.password == password:
            session['owner_id'] = owner.id
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('main.owner_dashboard'))
        else:
            flash('Nombre de usuario o contraseña incorrectos.', 'danger')
            return redirect(url_for('main.owner_login'))
    return render_template('owner_login.html')


@main_bp.route('/owner_dashboard')
def owner_dashboard():
    if 'owner_id' in session:
        owner = Owner.query.get(session['owner_id'])
        buildings = Building.query.filter_by(owner_id=owner.id).all()
        return render_template('owner_dashboard.html', owner=owner, buildings=buildings)
    else:
        flash('Por favor, inicia sesión', 'warning')
        return redirect(url_for('main.owner_login'))

@main_bp.route('/owner/add_building', methods=['GET', 'POST'])
def add_building():
    if 'owner_id' not in session:
        flash('Por favor, inicia sesión')
        return redirect(url_for('main.owner_login'))
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        city = request.form['city']
        country = request.form['country']
        if 'photo' not in request.files:
            flash('No se encontró el archivo')
            return redirect(request.url)
        file = request.files['photo']
        if file.filename == '':
            flash('No se seleccionó ningún archivo')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            new_building = Building(
                name=name,
                photo=filename,
                address=address,
                city=city,
                country=country,
                owner_id=session['owner_id']
            )
            db.session.add(new_building)
            db.session.commit()
            flash('Edificio agregado exitosamente')
            return redirect(url_for('main.owner_dashboard'))
        else:
            flash('Tipo de archivo no permitido')
            return redirect(request.url)
    return render_template('add_building.html')

@main_bp.route('/owner/building/<int:building_id>')
def view_building(building_id):
    if 'owner_id' not in session:
        flash('Por favor, inicia sesión')
        return redirect(url_for('main.owner_login'))
    building = Building.query.get_or_404(building_id)
    if building.owner_id != session['owner_id']:
        flash('No tienes permiso para ver este edificio')
        return redirect(url_for('main.owner_dashboard'))
    floors = Floor.query.filter_by(building_id=building.id).all()
    return render_template('view_building.html', building=building, floors=floors)

@main_bp.route('/owner/building/<int:building_id>/add_floor', methods=['POST'])
def add_floor(building_id):
    if 'owner_id' not in session:
        flash('Por favor, inicia sesión')
        return redirect(url_for('main.owner_login'))

    building = Building.query.get_or_404(building_id)
    if building.owner_id != session['owner_id']:
        flash('No tienes permiso para agregar pisos a este edificio')
        return redirect(url_for('main.owner_dashboard'))

    existing_floors = Floor.query.filter_by(building_id=building_id).count()
    next_floor_number = existing_floors + 1
    floor_name = f"Piso {next_floor_number}"

    new_floor = Floor(name=floor_name, building_id=building_id)
    db.session.add(new_floor)
    db.session.commit()

    flash(f'Se agregó el {floor_name} exitosamente')
    return redirect(url_for('main.view_building', building_id=building_id))

@main_bp.route('/owner/floor/<int:floor_id>/add_apartment', methods=['GET', 'POST'])
def add_apartment(floor_id):
    if 'owner_id' not in session:
        flash('Por favor, inicia sesión')
        return redirect(url_for('main.owner_login'))

    floor = Floor.query.get_or_404(floor_id)
    building = Building.query.get_or_404(floor.building_id)

    if request.method == 'POST':
        size = request.form['size']
        description = request.form['description']
        price = request.form['price']

        while True:
            random_number = randint(1000, 9999)
            code = f"B{building.id}F{floor.id}A{random_number}"
            existing_code = Apartment.query.filter_by(code=code).first()
            if not existing_code:
                break

        new_apartment = Apartment(
            size=size,
            description=description,
            price=price,
            code=code,
            floor_id=floor_id
        )
        db.session.add(new_apartment)
        db.session.commit()

        files = request.files.getlist('media')
        media_descriptions = request.form.get('media_descriptions', '').split(',')

        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                media_type = 'image' if 'image' in file.mimetype else 'video'
                media_description = media_descriptions[i].strip() if i < len(media_descriptions) else ''

                media = ApartmentMedia(
                    filename=filename,
                    description=media_description,
                    media_type=media_type,
                    apartment_id=new_apartment.id
                )
                db.session.add(media)

        db.session.commit()

        flash(f'Departamento agregado exitosamente. Código: {code}')
        return redirect(url_for('main.view_floor', floor_id=floor_id))

    return render_template('add_apartment.html', floor=floor)

@main_bp.route('/owner/apartment/<int:apartment_id>/delete', methods=['POST'])
def delete_apartment(apartment_id):
    apartment = Apartment.query.get_or_404(apartment_id)
    db.session.delete(apartment)
    db.session.commit()
    flash('Departamento eliminado con éxito.')
    return redirect(url_for('main.view_floor', floor_id=apartment.floor_id))

@main_bp.route('/view_apartments')
def view_apartments():
    apartments = Apartment.query.all()
    return render_template('view_apartments.html', apartments=apartments)



@main_bp.route('/owner/floor/<int:floor_id>/delete', methods=['POST'])
def delete_floor(floor_id):
    if 'owner_id' not in session:
        flash('Por favor, inicia sesión', 'warning')
        return redirect(url_for('main.owner_login'))

    floor = Floor.query.get_or_404(floor_id)
    building = Building.query.get_or_404(floor.building_id)
    if building.owner_id != session['owner_id']:
        flash('No tienes permiso para eliminar este piso', 'danger')
        return redirect(url_for('main.owner_dashboard'))

    apartments = Apartment.query.filter_by(floor_id=floor.id).all()
    for apartment in apartments:
        ApartmentMedia.query.filter_by(apartment_id=apartment.id).delete()
        db.session.delete(apartment)

    db.session.delete(floor)
    db.session.commit()

    flash('Piso eliminado con éxito', 'success')
    return redirect(url_for('main.view_building', building_id=building.id))

@main_bp.route('/owner/building/<int:building_id>/delete', methods=['POST'])
def delete_building(building_id):
    if 'owner_id' not in session:
        flash('Por favor, inicia sesión', 'warning')
        return redirect(url_for('main.owner_login'))

    building = Building.query.get_or_404(building_id)
    if building.owner_id != session['owner_id']:  # Corrección aquí
        flash('No tienes permiso para eliminar este edificio.', 'danger')
        return redirect(url_for('main.owner_dashboard'))

    # Eliminar archivos asociados al edificio (por ejemplo, la foto)
    if building.photo:
        photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], building.photo)
        if os.path.exists(photo_path):
            os.remove(photo_path)

    db.session.delete(building)
    db.session.commit()

    flash('Edificio eliminado correctamente.', 'success')
    return redirect(url_for('main.owner_dashboard'))




@main_bp.route('/owner/apartment/<int:apartment_id>')
def view_apartment(apartment_id):
    apartment = Apartment.query.get_or_404(apartment_id)
    media = ApartmentMedia.query.filter_by(apartment_id=apartment_id).all()
    return render_template('view_apartment.html', apartment=apartment, media=media)

@main_bp.route('/owner/apartment/<int:apartment_id>/add_media', methods=['GET', 'POST'])
def add_apartment_media(apartment_id):
    if 'owner_id' not in session:
        flash('Por favor, inicia sesión', 'warning')
        return redirect(url_for('main.owner_login'))

    apartment = Apartment.query.get_or_404(apartment_id)

    if request.method == 'POST':
        files = request.files.getlist('media')
        media_descriptions = request.form.get('media_descriptions', '').split(',')

        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                if file.mimetype.startswith('image'):
                    media_type = 'image'
                elif file.mimetype.startswith('video'):
                    media_type = 'video'
                else:
                    flash(f"El archivo {file.filename} no es válido.", 'warning')
                    continue

                # Obtener la descripción correspondiente
                media_description = media_descriptions[i].strip() if i < len(media_descriptions) else ''

                new_media = ApartmentMedia(
                    filename=filename,
                    description=media_description,
                    media_type=media_type,
                    apartment_id=apartment_id
                )
                db.session.add(new_media)
        db.session.commit()
        flash('Media agregada exitosamente.', 'success')
        return redirect(url_for('main.view_apartment', apartment_id=apartment_id))
    return render_template('add_apartment_media.html', apartment=apartment)

@main_bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.')
    return redirect(url_for('main.index'))

@main_bp.route('/owner/floor/<int:floor_id>')
def view_floor(floor_id):
    if 'owner_id' not in session:
        flash('Por favor, inicia sesión')
        return redirect(url_for('main.owner_login'))
    floor = Floor.query.get_or_404(floor_id)
    building = Building.query.get_or_404(floor.building_id)
    if building.owner_id != session['owner_id']:
        flash('No tienes permiso para ver este piso')
        return redirect(url_for('main.owner_dashboard'))
    apartments = Apartment.query.filter_by(floor_id=floor.id).all()
    return render_template('view_floor.html', floor=floor, building=building, apartments=apartments)

@main_bp.route('/owner/apartment/media/<int:media_id>/delete', methods=['POST'])
def delete_media(media_id):
    media = ApartmentMedia.query.get_or_404(media_id)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], media.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(media)
    db.session.commit()
    flash('Archivo multimedia eliminado exitosamente.')
    return redirect(request.referrer)

def register_routes(app):
    """Registrar el Blueprint principal en la aplicación."""
    app.register_blueprint(main_bp)
