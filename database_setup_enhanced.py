# database_setup.py
# Face Recognition Home Security System - Database Setup (Enhanced)
# Creates SQLite tables for family members, face encodings, and activity logs
# Added support for video files and deletion functionality

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
        image_path TEXT,
        video_path TEXT,
        status TEXT NOT NULL CHECK (status IN ('known', 'unknown', 'manual')),
        name TEXT,
        camera_id TEXT DEFAULT 'phone_camera',
        confidence_score REAL,
        video_duration REAL,
        file_size INTEGER,
        capture_type TEXT DEFAULT 'auto' CHECK (capture_type IN ('auto', 'manual')),
        notes TEXT,
        deleted_at TIMESTAMP NULL
    );
    '''
    
    # Create indexes for better performance
    create_indexes = [
        'CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp);',
        'CREATE INDEX IF NOT EXISTS idx_activity_logs_status ON activity_logs(status);',
        'CREATE INDEX IF NOT EXISTS idx_activity_logs_name ON activity_logs(name);',
        'CREATE INDEX IF NOT EXISTS idx_activity_logs_deleted ON activity_logs(deleted_at);',
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
            
            # Add new columns to existing table if they don't exist
            try:
                cursor.execute('ALTER TABLE activity_logs ADD COLUMN video_path TEXT;')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE activity_logs ADD COLUMN video_duration REAL;')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('ALTER TABLE activity_logs ADD COLUMN file_size INTEGER;')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('ALTER TABLE activity_logs ADD COLUMN capture_type TEXT DEFAULT "auto";')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('ALTER TABLE activity_logs ADD COLUMN deleted_at TIMESTAMP NULL;')
            except sqlite3.OperationalError:
                pass
            
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

def log_activity(image_path=None, video_path=None, status='unknown', name=None, 
                camera_id='phone_camera', confidence_score=None, video_duration=None,
                file_size=None, capture_type='auto', notes=None):
    """Log security system activity with enhanced video support"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO activity_logs (
                image_path, video_path, status, name, camera_id, 
                confidence_score, video_duration, file_size, capture_type, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (image_path, video_path, status, name, camera_id, 
              confidence_score, video_duration, file_size, capture_type, notes))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"📝 Logged activity: {status} - {name or 'Unknown'}")
        return log_id
        
    except sqlite3.Error as e:
        print(f"❌ Error logging activity: {e}")
        return None

def delete_activity_log(log_id, soft_delete=True):
    """Delete an activity log entry"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        if soft_delete:
            # Soft delete - mark as deleted but keep record
            cursor.execute('''
                UPDATE activity_logs 
                SET deleted_at = CURRENT_TIMESTAMP 
                WHERE id = ? AND deleted_at IS NULL
            ''', (log_id,))
        else:
            # Hard delete - completely remove from database
            # First get file paths to delete files
            cursor.execute('''
                SELECT image_path, video_path 
                FROM activity_logs 
                WHERE id = ?
            ''', (log_id,))
            
            result = cursor.fetchone()
            if result:
                image_path, video_path = result
                
                # Delete physical files
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"🗑️  Deleted image file: {image_path}")
                
                if video_path and os.path.exists(video_path):
                    os.remove(video_path)
                    print(f"🗑️  Deleted video file: {video_path}")
                
                # Delete database record
                cursor.execute('DELETE FROM activity_logs WHERE id = ?', (log_id,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            print(f"🗑️  {'Soft' if soft_delete else 'Hard'} deleted activity log ID: {log_id}")
            return True
        else:
            print(f"⚠️  Activity log ID {log_id} not found or already deleted")
            return False
        
    except sqlite3.Error as e:
        print(f"❌ Error deleting activity log: {e}")
        return False

def restore_activity_log(log_id):
    """Restore a soft-deleted activity log"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE activity_logs 
            SET deleted_at = NULL 
            WHERE id = ? AND deleted_at IS NOT NULL
        ''', (log_id,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            print(f"♻️  Restored activity log ID: {log_id}")
            return True
        else:
            print(f"⚠️  Activity log ID {log_id} not found in deleted records")
            return False
        
    except sqlite3.Error as e:
        print(f"❌ Error restoring activity log: {e}")
        return False

def bulk_delete_logs(log_ids, soft_delete=True):
    """Delete multiple activity logs at once"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        if soft_delete:
            # Soft delete multiple records
            placeholders = ','.join('?' for _ in log_ids)
            cursor.execute(f'''
                UPDATE activity_logs 
                SET deleted_at = CURRENT_TIMESTAMP 
                WHERE id IN ({placeholders}) AND deleted_at IS NULL
            ''', log_ids)
        else:
            # Hard delete multiple records (get file paths first)
            placeholders = ','.join('?' for _ in log_ids)
            cursor.execute(f'''
                SELECT id, image_path, video_path 
                FROM activity_logs 
                WHERE id IN ({placeholders})
            ''', log_ids)
            
            records = cursor.fetchall()
            
            # Delete physical files
            for record_id, image_path, video_path in records:
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"🗑️  Deleted image file: {image_path}")
                
                if video_path and os.path.exists(video_path):
                    os.remove(video_path)
                    print(f"🗑️  Deleted video file: {video_path}")
            
            # Delete database records
            cursor.execute(f'DELETE FROM activity_logs WHERE id IN ({placeholders})', log_ids)
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"🗑️  {'Soft' if soft_delete else 'Hard'} deleted {rows_affected} activity logs")
        return rows_affected
        
    except sqlite3.Error as e:
        print(f"❌ Error bulk deleting activity logs: {e}")
        return 0

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

def get_recent_logs(limit=50, include_deleted=False):
    """Get recent activity logs"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        deleted_filter = "" if include_deleted else "WHERE deleted_at IS NULL"
        
        cursor.execute(f'''
            SELECT id, timestamp, image_path, video_path, status, name, 
                   camera_id, confidence_score, video_duration, file_size, 
                   capture_type, notes, deleted_at
            FROM activity_logs
            {deleted_filter}
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
        
    except sqlite3.Error as e:
        print(f"❌ Error retrieving logs: {e}")
        return []

def get_storage_stats():
    """Get storage statistics"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Get total file sizes
        cursor.execute('''
            SELECT 
                COUNT(*) as total_files,
                SUM(file_size) as total_size,
                AVG(video_duration) as avg_duration,
                COUNT(CASE WHEN video_path IS NOT NULL THEN 1 END) as video_count,
                COUNT(CASE WHEN image_path IS NOT NULL THEN 1 END) as image_count
            FROM activity_logs 
            WHERE deleted_at IS NULL
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total_files': result[0] or 0,
            'total_size_bytes': result[1] or 0,
            'total_size_mb': round((result[1] or 0) / 1024 / 1024, 2),
            'avg_duration': round(result[2] or 0, 2),
            'video_count': result[3] or 0,
            'image_count': result[4] or 0
        }
        
    except sqlite3.Error as e:
        print(f"❌ Error getting storage stats: {e}")
        return {}

def create_required_directories():
    """Create necessary directories for the system"""
    directories = [
        'known', 
        'unknown', 
        'unknown/videos',
        'unknown/images', 
        'static', 
        'static/css',
        'static/js',
        'static/videos',
        'templates',
        'live_stream'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")
        else:
            print(f"📁 Directory exists: {directory}")

def cleanup_orphaned_files():
    """Clean up files that exist on disk but not in database"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Get all file paths from database
        cursor.execute('''
            SELECT image_path, video_path 
            FROM activity_logs 
            WHERE deleted_at IS NULL
        ''')
        
        db_files = set()
        for row in cursor.fetchall():
            if row[0]:  # image_path
                db_files.add(row[0])
            if row[1]:  # video_path
                db_files.add(row[1])
        
        conn.close()
        
        # Check unknown directory for orphaned files
        unknown_dirs = ['unknown', 'unknown/videos', 'unknown/images']
        orphaned_count = 0
        
        for directory in unknown_dirs:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path) and file_path not in db_files:
                        print(f"🧹 Found orphaned file: {file_path}")
                        # Optionally delete orphaned files
                        # os.remove(file_path)
                        orphaned_count += 1
        
        print(f"🧹 Found {orphaned_count} orphaned files")
        return orphaned_count
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return 0

def initialize_system():
    """Initialize the complete database system"""
    print("🚀 Initializing Enhanced Face Recognition Security System...")
    print("=" * 60)
    
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
    
    # Get storage stats
    stats = get_storage_stats()
    if stats:
        print(f"\n📊 Storage Statistics:")
        print(f"  • Total files: {stats['total_files']}")
        print(f"  • Storage used: {stats['total_size_mb']} MB")
        print(f"  • Videos: {stats['video_count']}")
        print(f"  • Images: {stats['image_count']}")
    
    print("\n✅ System initialization complete!")
    print("📝 Next steps:")
    print("  1. Add family member photos to 'known/' folder")
    print("  2. Run encodegenerator.py to create face encodings")
    print("  3. Run main.py to start face recognition (720p with video recording)")
    print("  4. Run app.py to start enhanced web interface")
    print("  5. Access live feed and controls from web dashboard")

if __name__ == "__main__":
    initialize_system()