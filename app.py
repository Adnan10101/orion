from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_db():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        port=5432
    )

# Endpoint 1: GET - View all records in a table
@app.route('/table/<table_name>', methods=['GET'])
def get_table(table_name):
    """GET request to view all records in a table"""
    
    allowed_tables = [
        'lab_tests', 'medicines', 'prescription', 'vitals', 
        'medical_history', 'patients_registration',
        'chat_history', 'image_analysis'
    ]
    
    if table_name not in allowed_tables:
        return jsonify({"error": "Invalid table name"}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all records from the table
        cur.execute(f"SELECT * FROM {table_name}")
        records = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "table": table_name,
            "count": len(records),
            "data": records
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint 2: POST - Insert new record into a table
@app.route('/table/<table_name>', methods=['POST'])
def insert_into_table(table_name):
    """POST request to insert a new record into a table"""
    
    allowed_tables = [
        'lab_tests', 'medicines', 'prescription', 'vitals', 
        'medical_history', 'patients_registration',
        'chat_history', 'image_analysis'
    ]
    
    if table_name not in allowed_tables:
        return jsonify({"error": "Invalid table name"}), 400
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Handle different tables
        if table_name == 'chat_history':
            cur.execute("""
                INSERT INTO chat_history (session_id, patient_id, prompt, response, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING chat_id
            """, (
                data.get('session_id'),
                data.get('patient_id'),
                data.get('prompt'),
                data.get('response'),
                datetime.now()
            ))
            
        elif table_name == 'image_analysis':
            cur.execute("""
                INSERT INTO image_analysis (patient_id, image_type, segmented_image_url, description, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING analysis_id
            """, (
                data.get('patient_id'),
                data.get('image_type'),
                data.get('segmented_image_url'),
                data.get('description'),
                datetime.now()
            ))
        
        else:
            # For other tables, build dynamic INSERT
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            values = tuple(data.values())
            
            cur.execute(
                f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                values
            )
        
        conn.commit()
        result = cur.fetchone() if cur.description else None
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Record inserted into {table_name}",
            "result": result
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
