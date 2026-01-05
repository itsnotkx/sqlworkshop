"""
Database Loader Script
Run this script to pre-load the MySQL database before starting the workshop.

Usage:
    python load_database.py <sql_file_path>
    
Example:
    python load_database.py create_insert.sql

Environment Variables (optional):
    MYSQL_HOST - MySQL host (default: localhost)
    MYSQL_PORT - MySQL port (default: 3306)
    MYSQL_USER - MySQL user (default: root)
    MYSQL_PASSWORD - MySQL password (default: empty)
    MYSQL_DATABASE - Database name (default: workshop_db)
"""

import mysql.connector
import sys
import os

def load_database(sql_file_path):
    """Load SQL script into MySQL database"""
    
    # Check if SQL file exists
    if not os.path.exists(sql_file_path):
        print(f"❌ Error: File '{sql_file_path}' not found.")
        return False
    
    # Check if it's a .sql file
    if not sql_file_path.endswith('.sql'):
        print(f"⚠️  Warning: File '{sql_file_path}' doesn't have .sql extension.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return False
    
    # MySQL Configuration
    mysql_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
    }
    database_name = os.getenv('MYSQL_DATABASE', 'workshop_db')
    
    try:
        # Read SQL file
        print(f"📖 Reading SQL file: {sql_file_path}")
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Connect to MySQL server (without database)
        print(f"🔌 Connecting to MySQL server at {mysql_config['host']}:{mysql_config['port']}...")
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        
        # Drop and recreate database
        print(f"🗑️  Dropping existing database '{database_name}' if it exists...")
        cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        
        print(f"🔨 Creating new database: {database_name}")
        cursor.execute(f"CREATE DATABASE {database_name}")
        cursor.execute(f"USE {database_name}")
        
        # Split SQL content by semicolons and execute each statement
        print("⚙️  Executing SQL script...")
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        for i, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)
            except mysql.connector.Error as err:
                print(f"⚠️  Warning on statement {i}: {err}")
                # Continue with other statements
        
        conn.commit()
        
        # Get table count
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall("create_insert.sql")
        print("\nMySQL Configuration (via environment variables):")
        print("  MYSQL_HOST (default: localhost)")
        print("  MYSQL_PORT (default: 3306)")
        print("  MYSQL_USER (default: root)")
        print("  MYSQL_PASSWORD (default: empty)")
        print("  MYSQL_DATABASE (default: workshop_db)")
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ Database loaded successfully!")
        print(f"📊 Tables created: {len(tables)}")
        for table in tables:
            print(f"   - {table[0]}")
        
        print(f"\n🚀 You can now start the web application with: python app.py")
        return True
        
    except Exception as e:
        print(f"\n❌ Error loading database: {str(e)}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python load_database.py <sql_file_path>")
        print("\nExample:")
        print("  python load_database.py sample.sql")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    success = load_database(sql_file)
    
    sys.exit(0 if success else 1)
