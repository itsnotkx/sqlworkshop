from flask import Flask, render_template, request, jsonify
import re
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Supabase/PostgreSQL Configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db_connection():
    """Create a new database connection"""
    try:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL must be set in .env file")
        return psycopg2.connect(DATABASE_URL)
    except Exception as err:
        print(f"❌ Error connecting to database: {err}")
        raise

def test_connection():
    """Test database connection on startup"""
    try:
        conn = get_db_connection()
        conn.close()
        print(f"✅ Connected to Supabase PostgreSQL database")
    except Exception as err:
        print(f"❌ Error connecting to database: {err}")
        raise

def is_query_safe(query):
    """
    Check if query is safe (only SELECT and read-only operations allowed).
    Supports: SELECT, JOINs, subqueries, CTEs (WITH), UNION, aliases (AS), window functions, etc.
    Blocks: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, and other write operations.
    """
    query_upper = query.strip().upper()
    
    # Remove comments
    query_upper = re.sub(r'--.*', '', query_upper)
    query_upper = re.sub(r'/\*.*?\*/', '', query_upper, flags=re.DOTALL)
    
    # Check for dangerous keywords (write operations)
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER',
        'CREATE', 'TRUNCATE', 'REPLACE', 'PRAGMA',
        'ATTACH', 'DETACH', 'VACUUM', 'GRANT', 'REVOKE'
    ]
    
    for keyword in dangerous_keywords:
        if re.search(r'\b' + keyword + r'\b', query_upper):
            return False, f"Query contains forbidden keyword: {keyword}"
    
    # Must start with SELECT or WITH (for CTEs)
    if not re.match(r'^\s*(SELECT|WITH)\b', query_upper):
        return False, "Only SELECT queries (including CTEs with WITH, UNION, JOINs) are allowed"
    
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
    conn = None
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
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query)
        
        # Fetch results
        rows = cursor.fetchall()
        columns = list(rows[0].keys()) if rows else []
        
        # Convert to JSON-serializable format
        results = []
        for row in rows:
            results.append({k: str(v) if v is not None else None for k, v in dict(row).items()})
        
        cursor.close()
        
        return jsonify({
            'columns': columns,
            'rows': results,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/list_tables', methods=['GET'])
def list_tables():
    """List all tables in the database"""
    conn = None
    try:
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query)
        rows = cursor.fetchall()
        tables = [row['table_name'] for row in rows]
        cursor.close()
        return jsonify({'tables': tables})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/table_schema/<table_name>', methods=['GET'])
def table_schema(table_name):
    """Get schema for a specific table"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND table_name = %s
        ORDER BY ordinal_position
        """
        cursor.execute(query, (table_name,))
        rows = cursor.fetchall()
        
        # Get primary key info
        pk_query = """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass AND i.indisprimary
        """
        cursor.execute(pk_query, (table_name,))
        pk_rows = cursor.fetchall()
        primary_keys = [row['attname'] for row in pk_rows]
        
        schema = []
        for row in rows:
            schema.append({
                'column': row['column_name'],
                'type': row['data_type'],
                'nullable': row['is_nullable'] == 'YES',
                'primary_key': row['column_name'] in primary_keys
            })
        
        cursor.close()
        return jsonify({'table': table_name, 'schema': schema})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Test database connection
    test_connection()
    
    # Run with threading support for concurrent users
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
