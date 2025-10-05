# migrate_database.py
# Database Migration Script for Enhanced Face Recognition System
# Safely updates existing database schema to support new features

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

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        return column_name in columns
    except sqlite3.Error:
        return False

def migrate_database():
    """Migrate existing database to new enhanced schema"""
    print("🔄 Starting database migration...")
    print("=" * 50)
    
    try:
        conn = create_connection()
        if not conn:
            print("❌ Cannot connect to database!")
            return False
        
        cursor = conn.cursor()
        
        # Check if we need to migrate
        needs_migration = False
        new_columns = [
            ('video_path', 'TEXT'),
            ('video_duration', 'REAL'), 
            ('file_size', 'INTEGER'),
            ('capture_type', 'TEXT DEFAULT "auto"'),
            ('deleted_at', 'TIMESTAMP NULL')
        ]
        
        print("🔍 Checking existing schema...")
        
        for column_name, column_type in new_columns:
            if not check_column_exists(cursor, 'activity_logs', column_name):
                print(f"  📝 Need to add column: {column_name}")
                needs_migration = True
        
        if not needs_migration:
            print("✅ Database schema is already up to date!")
            conn.close()
            return True
        
        print("\n🛠️  Applying migrations...")
        
        # Add new columns one by one
        for column_name, column_type in new_columns:
            if not check_column_exists(cursor, 'activity_logs', column_name):
                try:
                    sql = f"ALTER TABLE activity_logs ADD COLUMN {column_name} {column_type};"
                    cursor.execute(sql)
                    print(f"  ✅ Added column: {column_name}")
                except sqlite3.Error as e:
                    print(f"  ⚠️  Column {column_name} might already exist: {e}")
        
        # Update existing records to set default values
        print("\n📝 Updating existing records...")
        
        # Set default capture_type for existing records
        cursor.execute("""
            UPDATE activity_logs 
            SET capture_type = 'auto' 
            WHERE capture_type IS NULL
        """)
        
        # Update status column to include new 'manual' option if needed
        try:
            cursor.execute("""
                UPDATE activity_logs 
                SET status = 'unknown' 
                WHERE status NOT IN ('known', 'unknown', 'manual')
            """)
        except sqlite3.Error:
            pass
        
        # Create new indexes for performance
        new_indexes = [
            'CREATE INDEX IF NOT EXISTS idx_activity_logs_video_path ON activity_logs(video_path);',
            'CREATE INDEX IF NOT EXISTS idx_activity_logs_capture_type ON activity_logs(capture_type);',
            'CREATE INDEX IF NOT EXISTS idx_activity_logs_file_size ON activity_logs(file_size);'
        ]
        
        print("\n📊 Creating performance indexes...")
        for index_sql in new_indexes:
            try:
                cursor.execute(index_sql)
                print(f"  ✅ Created index")
            except sqlite3.Error as e:
                print(f"  ⚠️  Index might already exist: {e}")
        
        # Commit all changes
        conn.commit()
        conn.close()
        
        print("\n✅ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def verify_migration():
    """Verify that migration was successful"""
    print("\n🔍 Verifying migration...")
    
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Check table schema
        cursor.execute("PRAGMA table_info(activity_logs)")
        columns = cursor.fetchall()
        
        expected_columns = [
            'id', 'timestamp', 'image_path', 'video_path', 'status', 
            'name', 'camera_id', 'confidence_score', 'video_duration', 
            'file_size', 'capture_type', 'notes', 'deleted_at'
        ]
        
        existing_columns = [col[1] for col in columns]
        
        print("📋 Current table schema:")
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            is_required = "✅" if col_name in expected_columns else "⚠️ "
            print(f"  {is_required} {col_name} ({col_type})")
        
        # Check for missing columns
        missing_columns = [col for col in expected_columns if col not in existing_columns]
        if missing_columns:
            print(f"\n⚠️  Missing columns: {missing_columns}")
            return False
        
        # Test basic operations
        cursor.execute("SELECT COUNT(*) FROM activity_logs")
        total_logs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM activity_logs WHERE deleted_at IS NULL")
        active_logs = cursor.fetchone()[0]
        
        print(f"\n📊 Database statistics:")
        print(f"  • Total logs: {total_logs}")
        print(f"  • Active logs: {active_logs}")
        print(f"  • Deleted logs: {total_logs - active_logs}")
        
        conn.close()
        
        print("\n✅ Migration verification successful!")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def backup_database():
    """Create a backup of the existing database"""
    if not os.path.exists(DATABASE_PATH):
        print("⚠️  No existing database to backup")
        return True
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{DATABASE_PATH}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"💾 Database backup created: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False

def main():
    """Main migration function"""
    print("🏠 Enhanced Face Recognition System - Database Migration")
    print("=" * 60)
    
    # Create backup first
    if not backup_database():
        print("⚠️  Continuing without backup...")
    
    # Run migration
    if migrate_database():
        # Verify migration
        if verify_migration():
            print("\n🎉 Database migration completed successfully!")
            print("\n📝 You can now run:")
            print("  • python main_enhanced.py (for face recognition)")
            print("  • python app_enhanced.py (for web interface)")
        else:
            print("\n⚠️  Migration completed but verification failed")
    else:
        print("\n❌ Migration failed!")
        print("📝 You may need to:")
        print("  • Check database permissions")
        print("  • Restore from backup if needed")
        print("  • Run database_setup_enhanced.py with fresh database")

if __name__ == "__main__":
    main()