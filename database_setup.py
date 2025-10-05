# database_setup.py
# Face Recognition Home Security System - Database Setup
# Creates SQLite tables for family members, face encodings, and activity logs

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = 'security_system.db'

def create_connection():
    """Create a database connection to SQLite database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def create_tables():
    """Create all required tables for the security system"""
    
    # SQL statements for creating tables
    create_family_members_table = '''
    CREATE TABLE IF NOT EXISTS family_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        image_path TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    );
    '''
    
    create_face_encodings_table = '''
    CREATE TABLE IF NOT EXISTS face_encodings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_member_id INTEGER NOT NULL,
        encoding BLOB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (family_member_id) REFERENCES family_members (id)
    );
    '''
    
    create_activity_logs_table = '''
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        image_path TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('known', 'unknown')),
        name TEXT,
        camera_id TEXT DEFAULT 'phone_camera',
        confidence_score REAL,
        notes TEXT
    );
    '''
    
    # Create indexes for better performance
    create_indexes = [
        'CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp);',
        'CREATE INDEX IF NOT EXISTS idx_activity_logs_status ON activity_logs(status);',
        'CREATE INDEX IF NOT EXISTS idx_activity_logs_name ON activity_logs(name);',
        'CREATE INDEX IF NOT EXISTS idx_family_members_name ON family_members(name);'
    ]
    
    try:
        conn = create_connection()
        if conn is not None:
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute(create_family_members_table)
            cursor.execute(create_face_encodings_table)
            cursor.execute(create_activity_logs_table)
            
            # Create indexes
            for index_sql in create_indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            print("✅ Database tables created successfully!")
            print(f"📁 Database file: {os.path.abspath(DATABASE_PATH)}")
            
        else:
            print("❌ Error! Cannot create database connection.")
            
    except sqlite3.Error as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        if conn:
            conn.close()

def add_family_member(name, image_path):
    """Add a new family member to the database"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO family_members (name, image_path)
            VALUES (?, ?)
        ''', (name, image_path))
        
        family_member_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Added family member: {name}")
        return family_member_id
        
    except sqlite3.IntegrityError:
        print(f"⚠️  Family member '{name}' already exists!")
        return None
    except sqlite3.Error as e:
        print(f"❌ Error adding family member: {e}")
        return None

def add_face_encoding(family_member_id, encoding):
    """Add face encoding for a family member"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Convert numpy array to bytes for storage
        encoding_bytes = encoding.tobytes()
        
        cursor.execute('''
            INSERT INTO face_encodings (family_member_id, encoding)
            VALUES (?, ?)
        ''', (family_member_id, encoding_bytes))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Added face encoding for family member ID: {family_member_id}")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error adding face encoding: {e}")
        return False

def log_activity(image_path, status, name=None, camera_id='phone_camera', confidence_score=None):
    """Log security system activity"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO activity_logs (image_path, status, name, camera_id, confidence_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (image_path, status, name, camera_id, confidence_score))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"📝 Logged activity: {status} - {name or 'Unknown'}")
        return log_id
        
    except sqlite3.Error as e:
        print(f"❌ Error logging activity: {e}")
        return None

def get_all_family_encodings():
    """Retrieve all family member encodings"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fm.name, fe.encoding 
            FROM family_members fm
            JOIN face_encodings fe ON fm.id = fe.family_member_id
            WHERE fm.is_active = 1
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
        
    except sqlite3.Error as e:
        print(f"❌ Error retrieving encodings: {e}")
        return []

def get_recent_logs(limit=50):
    """Get recent activity logs"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, image_path, status, name, camera_id, confidence_score
            FROM activity_logs
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
        
    except sqlite3.Error as e:
        print(f"❌ Error retrieving logs: {e}")
        return []

def create_required_directories():
    """Create necessary directories for the system"""
    directories = ['known', 'unknown', 'static', 'templates']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")
        else:
            print(f"📁 Directory exists: {directory}")

def initialize_system():
    """Initialize the complete database system"""
    print("🚀 Initializing Face Recognition Security System...")
    print("=" * 50)
    
    # Create required directories
    create_required_directories()
    
    # Create database tables
    create_tables()
    
    # Verify tables exist
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\n📋 Created tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  • {table[0]} ({count} records)")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Error verifying tables: {e}")
    
    print("\n✅ System initialization complete!")
    print("📝 Next steps:")
    print("  1. Add family member photos to 'known/' folder")
    print("  2. Run encodegenerator.py to create face encodings")
    print("  3. Run main.py to start face recognition")
    print("  4. Run app.py to start web interface")

if __name__ == "__main__":
    initialize_system()