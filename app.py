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

# ✅ ADD ROOT ENDPOINT
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "healthy",
        "service": "Medical Records API",
        "version": "1.0",
        "endpoints": {
            "GET /table/<table_name>": "View all records in a table",
            "POST /table/<table_name>": "Insert a new record"
        },
        "available_tables": [
            "chat_history",
            "image_analysis",
            "patients_registration",
            "medicines",
            "lab_tests",
            "vitals",
            "medical_history",
            "prescription"
        ]
    })

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
            # ✅ UPDATED: Now handles all required fields
            cur.execute("""
                INSERT INTO image_analysis (
                    patient_id, 
                    session_id,
                    image_type, 
                    original_image_url,
                    segmented_image_url, 
                    description, 
                    timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, to_timestamp(%s))
                RETURNING analysis_id
            """, (
                data.get('patient_id'),
                data.get('session_id'),
                data.get('image_type', 'surgical_frame'),
                data.get('original_image_url'),  # ✅ NEW
                data.get('segmented_image_url'),
                data.get('description'),
                data.get('timestamp')  # ✅ CHANGED: Use timestamp from request
            ))
        
        else:
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


# Endpoint 3: DELETE - Delete records from a table
@app.route('/table/<table_name>', methods=['DELETE'])
def delete_from_table(table_name):
    """DELETE request to delete records from a table"""
    
    allowed_tables = [
        'lab_tests', 'medicines', 'prescription', 'vitals', 
        'medical_history', 'patients_registration',
        'chat_history', 'image_analysis'
    ]
    
    if table_name not in allowed_tables:
        return jsonify({"error": "Invalid table name"}), 400
    
    try:
        # Get filter parameters from query string or JSON body
        filters = request.args.to_dict() or request.get_json() or {}
        
        if not filters:
            return jsonify({"error": "No filters provided. Use ?chat_id=123 or send JSON body"}), 400
        
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build DELETE query with WHERE clause
        where_conditions = []
        values = []
        
        for key, value in filters.items():
            where_conditions.append(f"{key} = %s")
            values.append(value)
        
        where_clause = " AND ".join(where_conditions)
        delete_query = f"DELETE FROM {table_name} WHERE {where_clause} RETURNING *"
        
        cur.execute(delete_query, tuple(values))
        deleted_records = cur.fetchall()
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Deleted {len(deleted_records)} record(s) from {table_name}",
            "deleted_count": len(deleted_records),
            "deleted_records": deleted_records
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint 4: DELETE specific chat by ID (convenience endpoint)
@app.route('/table/chat_history/<int:chat_id>', methods=['DELETE'])
def delete_chat_by_id(chat_id):
    """DELETE a specific chat by chat_id"""
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("DELETE FROM chat_history WHERE chat_id = %s RETURNING *", (chat_id,))
        deleted = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        if deleted:
            return jsonify({
                "message": f"Chat {chat_id} deleted successfully",
                "deleted_record": deleted
            }), 200
        else:
            return jsonify({"error": f"Chat {chat_id} not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint 5: DELETE all chats for a session
@app.route('/table/chat_history/session/<session_id>', methods=['DELETE'])
def delete_session_chats(session_id):
    """DELETE all chats from a specific session"""
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("DELETE FROM chat_history WHERE session_id = %s RETURNING chat_id", (session_id,))
        deleted = cur.fetchall()
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Deleted {len(deleted)} chat(s) from session {session_id}",
            "deleted_count": len(deleted),
            "deleted_chat_ids": [d['chat_id'] for d in deleted]
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/migrate_database', methods=['POST'])
def migrate_database():
    """Migrate ONLY image_analysis table - chat_history untouched"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        print("Starting migration for image_analysis only...")
        
        # Migration SQL - ONLY for image_analysis
        migration_sql = """
        -- Drop and recreate image_analysis with all required fields
        DROP TABLE IF EXISTS image_analysis CASCADE;
        
        CREATE TABLE image_analysis (
            analysis_id SERIAL PRIMARY KEY,
            patient_id VARCHAR(50) NOT NULL,
            session_id VARCHAR(100),
            image_type VARCHAR(50),
            original_image_url TEXT,
            segmented_image_url TEXT,
            description TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create indexes for image_analysis only
        CREATE INDEX idx_image_patient ON image_analysis(patient_id);
        CREATE INDEX idx_image_session ON image_analysis(session_id);
        CREATE INDEX idx_image_timestamp ON image_analysis(timestamp DESC);
        """
        
        cur.execute(migration_sql)
        conn.commit()
        
        print("Migration complete, verifying...")
        
        # Verify image_analysis structure
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'image_analysis'
            ORDER BY ordinal_position
        """)
        
        image_columns = [
            {"name": col[0], "type": col[1], "nullable": col[2]} 
            for col in cur.fetchall()
        ]
        
        # Check indexes for image_analysis
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public' 
            AND tablename = 'image_analysis'
            ORDER BY indexname
        """)
        
        indexes = [idx[0] for idx in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "image_analysis table recreated successfully (chat_history unchanged)",
            "image_analysis": {
                "columns": image_columns,
                "indexes": indexes
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/admin/verify_schema', methods=['GET'])
def verify_schema():
    """Verify current database schema"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Get image_analysis columns
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'image_analysis'
            ORDER BY ordinal_position
        """)
        
        image_columns = cur.fetchall()
        
        # Get chat_history columns to verify it's untouched
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'chat_history'
            ORDER BY ordinal_position
        """)
        
        chat_columns = cur.fetchall()
        
        # Count records
        cur.execute("SELECT COUNT(*) FROM image_analysis")
        image_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM chat_history")
        chat_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "tables": {
                "image_analysis": {
                    "columns": [
                        {"name": col[0], "type": col[1], "nullable": col[2]} 
                        for col in image_columns
                    ],
                    "record_count": image_count
                },
                "chat_history": {
                    "columns": [
                        {"name": col[0], "type": col[1], "nullable": col[2]} 
                        for col in chat_columns
                    ],
                    "record_count": chat_count
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
