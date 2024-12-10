from flask import Blueprint, jsonify
from extensions import db
from sqlalchemy.sql import text

api_bp = Blueprint('api', __name__)

@api_bp.route('/extract_clients_data', methods=['GET'])
def extract_clients_data():
    try:
        # Especifica las tablas que quieres extraer
        tables_to_extract = ['clients', 'client_photos']
        extracted_data = {}

        for table in tables_to_extract:
            # Obtener datos de la tabla
            query = text(f"SELECT * FROM {table};")
            rows = db.session.execute(query).fetchall()
            columns_query = db.session.execute(text(f"PRAGMA table_info({table});"))
            columns = [column[1] for column in columns_query]

            # Formatear los datos como diccionario
            table_data = [dict(zip(columns, row)) for row in rows]
            extracted_data[table] = table_data

        return jsonify({"success": True, "data": extracted_data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
