from flask import Flask, render_template, request, jsonify
import mysql.connector
from mysql.connector import pooling
import re
import os
from werkzeug.utils import secure_filename
import threading

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# MySQL Configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', '3306'))
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DATABASE'] = os.getenv('MYSQL_DATABASE', 'workshop_db')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MySQL Connection Pool
connection_pool = None

def init_connection_pool():
    """Initialize MySQL connection pool"""
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="workshop_pool",
            pool_size=50,  # Support ~40 concurrent users
            pool_reset_session=True,
            host=app.config['MYSQL_HOST'],
            port=app.config['MYSQL_PORT'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DATABASE']
        )
        print(f"✅ Connected to MySQL database: {app.config['MYSQL_DATABASE']}")
    except mysql.connector.Error as err:
        print(f"❌ Error connecting to MySQL: {err}")
        raise

def get_db():
    """Get database connection from pool"""
    return connection_pool.get_connection()

def is_query_safe(query):
    """
    Check if query is safe (only SELECT allowed).
    Blocks INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, etc.
    """
    query_upper = query.strip().upper()
    
    # Remove comments
    query_upper = re.sub(r'--.*', '', query_upper)
    query_upper = re.sub(r'/\*.*?\*/', '', query_upper, flags=re.DOTALL)
    
    # Check for dangerous keywords
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER',
        'CREATE', 'TRUNCATE', 'REPLACE', 'PRAGMA',
        'ATTACH', 'DETACH', 'VACUUM'
    ]
    
    for keyword in dangerous_keywords:
        if re.search(r'\b' + keyword + r'\b', query_upper):
            return False, f"Query contains forbidden keyword: {keyword}"
    
    # Must start with SELECT (after whitespace)
    if not re.match(r'^\s*SELECT\b', query_upper):
        return False, "Only SELECT queries are allowed"
    
    return True, "Query is safe"

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

@app.route('/upload_sql', methods=['POST'])
def upload_sql():
    """Upload and execute SQL script to populate database"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.sql'):
            return jsonify({'error': 'File must be a .sql file'}), 400
        
        # Read SQL content
        sql_content = file.read().decode('utf-8')
        
        # Close existing connections and recreate database
        if hasattr(db_local, 'connection'):
            db_local.connection.close()
            delattr(db_local, 'connection')
        
        # Remove old database and create new one
        if os.path.exists(app.config['DATABASE']):
            os.remove(app.config['DATABASE'])
        
        # Execute SQL script
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()
        cursor.executescript(sql_content)
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Database loaded successfully',
            'filename': secure_filename(file.filename)
        })
    
    except Exception as e:
        return jsonify({'error': f'Failed to load SQL: {str(e)}'}), 500

@app.route('/execute_query', methods=['POST'])
def execute_query():
    """Execute a SELECT query and return results"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Check if query is safe
        is_safe, message = is_query_safe(query)
        if not is_safe:
            return jsonify({'error': message}), 403
        
        # Execute query
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        
        # Fetch results
        rows = cursor.fetchall()
        columns = list(rows[0].keys()) if rows else []
        
        # Convert to JSON-serializable format
        results = []
        for row in rows:
            results.append({k: str(v) if v is not None else None for k, v in row.items()})
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'columns': columns,
            'rows': results,
            'count': len(results)
        })
    
    except mysql.connector.Error as e:
        return jsonify({'error': f'SQL Error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/list_tables', methods=['GET'])
def list_tables():
    """List all tables in the database"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'tables': tables})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/table_schema/<table_name>', methods=['GET'])
def table_schema(table_name):
    """Get schema for a specific table"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"DESCRIBE {table_name}")
        rows = cursor.fetchall()
        schema = []
        for row in rows:
            schema.append({
                'column': row['Field'],
                'type': row['Type'],
                'nullable': row['Null'] == 'YES',
                'primary_key': row['Key'] == 'PRI'
            })
        cursor.close()
        conn.close()
        return jsonify({'table': table_name, 'schema': schema})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    # Initialize MySQL connection pool
    init_connection_pool()
    
    # Run with threading support for concurrent users
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
