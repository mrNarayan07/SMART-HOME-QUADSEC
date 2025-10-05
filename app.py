# app.py
# Face Recognition Home Security System - Flask Web Interface
# Dashboard for viewing activity logs and managing the security system

from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import os
from datetime import datetime, timedelta
import json
from pathlib import Path

from database_setup import (
    create_connection, 
    get_recent_logs, 
    DATABASE_PATH
)

# Flask app configuration
app = Flask(__name__)
app.secret_key = 'face_recognition_security_system_2024'

# Configuration
UNKNOWN_FACES_DIR = "unknown"
ITEMS_PER_PAGE = 20
MAX_LOGS_DISPLAY = 1000

class SecurityDashboard:
    def __init__(self):
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        dirs = [UNKNOWN_FACES_DIR, 'static', 'templates']
        for directory in dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"📁 Created directory: {directory}")

    def get_logs_with_pagination(self, page=1, per_page=ITEMS_PER_PAGE, 
                                status_filter=None, name_filter=None, 
                                date_filter=None):
        """Get activity logs with pagination and filtering"""
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # Build query with filters
            query = "SELECT id, timestamp, image_path, status, name, camera_id, confidence_score FROM activity_logs WHERE 1=1"
            params = []
            
            # Apply filters
            if status_filter and status_filter != 'all':
                query += " AND status = ?"
                params.append(status_filter)
            
            if name_filter:
                query += " AND (name LIKE ? OR name IS NULL)"
                params.append(f"%{name_filter}%")
            
            if date_filter:
                try:
                    filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
                    next_day = filter_date + timedelta(days=1)
                    query += " AND timestamp >= ? AND timestamp < ?"
                    params.extend([filter_date.isoformat(), next_day.isoformat()])
                except ValueError:
                    pass  # Invalid date format, ignore filter
            
            # Add ordering and pagination
            query += " ORDER BY timestamp DESC"
            
            # Get total count
            count_query = query.replace(
                "SELECT id, timestamp, image_path, status, name, camera_id, confidence_score FROM activity_logs", 
                "SELECT COUNT(*) FROM activity_logs"
            )
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Add pagination
            offset = (page - 1) * per_page
            query += f" LIMIT {per_page} OFFSET {offset}"
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            conn.close()
            
            # Calculate pagination info
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            return {
                'logs': logs,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }
            
        except Exception as e:
            print(f"Error getting logs: {e}")
            return {
                'logs': [],
                'total_count': 0,
                'page': 1,
                'per_page': per_page,
                'total_pages': 1,
                'has_prev': False,
                'has_next': False
            }

    def get_statistics(self):
        """Get dashboard statistics"""
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # Total logs
            cursor.execute("SELECT COUNT(*) FROM activity_logs")
            total_logs = cursor.fetchone()[0]
            
            # Known vs Unknown
            cursor.execute("SELECT status, COUNT(*) FROM activity_logs GROUP BY status")
            status_counts = dict(cursor.fetchall())
            
            # Recent activity (last 24 hours)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor.execute("SELECT COUNT(*) FROM activity_logs WHERE timestamp >= ?", (yesterday,))
            recent_activity = cursor.fetchone()[0]
            
            # Family members count
            cursor.execute("SELECT COUNT(*) FROM family_members WHERE is_active = 1")
            family_count = cursor.fetchone()[0]
            
            # Most active family member (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT name, COUNT(*) as count 
                FROM activity_logs 
                WHERE status = 'known' AND timestamp >= ? AND name IS NOT NULL
                GROUP BY name 
                ORDER BY count DESC 
                LIMIT 1
            """, (week_ago,))
            
            most_active = cursor.fetchone()
            most_active_name = most_active[0] if most_active else "None"
            
            conn.close()
            
            return {
                'total_logs': total_logs,
                'known_count': status_counts.get('known', 0),
                'unknown_count': status_counts.get('unknown', 0),
                'recent_activity': recent_activity,
                'family_count': family_count,
                'most_active_member': most_active_name
            }
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {
                'total_logs': 0,
                'known_count': 0,
                'unknown_count': 0,
                'recent_activity': 0,
                'family_count': 0,
                'most_active_member': 'None'
            }

    def format_log_for_display(self, log):
        """Format log entry for display"""
        log_id, timestamp, image_path, status, name, camera_id, confidence_score = log
        
        # Parse timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            relative_time = self.get_relative_time(dt)
        except:
            formatted_time = timestamp
            relative_time = "Unknown"
        
        # Check if image exists
        image_exists = False
        if image_path and os.path.exists(image_path):
            image_exists = True
        
        return {
            'id': log_id,
            'timestamp': formatted_time,
            'relative_time': relative_time,
            'image_path': image_path,
            'image_exists': image_exists,
            'status': status,
            'name': name or 'Unknown',
            'camera_id': camera_id or 'phone_camera',
            'confidence_score': round(confidence_score, 1) if confidence_score else None,
            'status_class': 'success' if status == 'known' else 'danger',
            'status_icon': '👤' if status == 'known' else '🚨'
        }
    
    def get_relative_time(self, dt):
        """Get relative time string"""
        now = datetime.now()
        diff = now - dt.replace(tzinfo=None)
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"

# Initialize dashboard
dashboard = SecurityDashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    name_filter = request.args.get('name', '').strip()
    date_filter = request.args.get('date', '').strip()
    
    # Get logs with filters
    logs_data = dashboard.get_logs_with_pagination(
        page=page,
        status_filter=status_filter,
        name_filter=name_filter,
        date_filter=date_filter
    )
    
    # Format logs for display
    formatted_logs = []
    for log in logs_data['logs']:
        formatted_logs.append(dashboard.format_log_for_display(log))
    
    # Get statistics
    stats = dashboard.get_statistics()
    
    return render_template('dashboard.html', 
                         logs=formatted_logs,
                         pagination=logs_data,
                         stats=stats,
                         filters={
                             'status': status_filter,
                             'name': name_filter,
                             'date': date_filter
                         })

@app.route('/api/logs')
def api_logs():
    """API endpoint for getting logs (for AJAX updates)"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    name_filter = request.args.get('name', '').strip()
    date_filter = request.args.get('date', '').strip()
    
    logs_data = dashboard.get_logs_with_pagination(
        page=page,
        status_filter=status_filter,
        name_filter=name_filter,
        date_filter=date_filter
    )
    
    # Format logs for JSON response
    formatted_logs = []
    for log in logs_data['logs']:
        formatted_logs.append(dashboard.format_log_for_display(log))
    
    return jsonify({
        'logs': formatted_logs,
        'pagination': {
            'page': logs_data['page'],
            'total_pages': logs_data['total_pages'],
            'total_count': logs_data['total_count'],
            'has_prev': logs_data['has_prev'],
            'has_next': logs_data['has_next']
        }
    })

@app.route('/api/stats')
def api_stats():
    """API endpoint for getting dashboard statistics"""
    stats = dashboard.get_statistics()
    return jsonify(stats)

@app.route('/image/<path:filename>')
def serve_image(filename):
    """Serve images from unknown faces directory"""
    try:
        return send_from_directory(UNKNOWN_FACES_DIR, filename)
    except FileNotFoundError:
        # Return placeholder image or 404
        return "Image not found", 404

@app.route('/logs')
def logs_page():
    """Dedicated logs page (alternative view)"""
    return index()  # Use same logic as main page

@app.route('/search')
def search():
    """Search page with advanced filters"""
    return render_template('search.html')

@app.route('/api/search')
def api_search():
    """API endpoint for search functionality"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'results': []})
    
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Search in logs
        cursor.execute("""
            SELECT id, timestamp, image_path, status, name, camera_id, confidence_score
            FROM activity_logs 
            WHERE (name LIKE ? OR status LIKE ?)
            ORDER BY timestamp DESC
            LIMIT 50
        """, (f"%{query}%", f"%{query}%"))
        
        results = cursor.fetchall()
        conn.close()
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(dashboard.format_log_for_display(result))
        
        return jsonify({'results': formatted_results})
        
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'results': [], 'error': str(e)})

@app.route('/api/system/status')
def system_status():
    """Get system status information"""
    try:
        # Check database connection
        conn = create_connection()
        if conn:
            conn.close()
            db_status = "Connected"
        else:
            db_status = "Error"
        
        # Check directories
        dirs_status = {
            'known': os.path.exists('known'),
            'unknown': os.path.exists('unknown'),
            'templates': os.path.exists('templates'),
            'static': os.path.exists('static')
        }
        
        # Check if main.py is running (simple check)
        import psutil
        main_running = any('main.py' in p.cmdline() for p in psutil.process_iter(['cmdline']))
        
        return jsonify({
            'database': db_status,
            'directories': dirs_status,
            'recognition_system': 'Running' if main_running else 'Stopped',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'database': 'Error',
            'directories': {},
            'recognition_system': 'Unknown',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_code=404,
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error"), 500

def create_sample_data():
    """Create sample data for testing (development only)"""
    from database_setup import log_activity
    
    # Add some sample logs
    sample_logs = [
        ("known/dad.jpg", "known", "Dad", "phone_camera", 95.5),
        ("unknown/unknown_20241002_143022.jpg", "unknown", None, "phone_camera", None),
        ("known/mom.jpg", "known", "Mom", "phone_camera", 87.3),
        ("unknown/unknown_20241002_143155.jpg", "unknown", None, "phone_camera", None),
    ]
    
    print("📝 Creating sample data...")
    for image_path, status, name, camera_id, confidence in sample_logs:
        log_activity(image_path, status, name, camera_id, confidence)
    
    print("✅ Sample data created")

def main():
    """Main function to run the Flask app"""
    print("🌐 Face Recognition Security System - Web Dashboard")
    print("=" * 50)
    
    # Check if database exists
    if not os.path.exists(DATABASE_PATH):
        print("⚠️  Database not found! Please run database_setup.py first.")
        return
    
    print(f"📊 Dashboard starting...")
    print(f"🗃️  Database: {DATABASE_PATH}")
    print(f"📁 Unknown faces: {UNKNOWN_FACES_DIR}")
    print("=" * 50)
    
    # Development options
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'sample':
            create_sample_data()
        elif sys.argv[1] == 'debug':
            print("🐛 Starting in debug mode...")
            app.run(debug=True, host='0.0.0.0', port=5000)
            return
    
    print("🚀 Starting web server...")
    print("📱 Access on phone: http://[YOUR_IP]:5000")
    print("💻 Access on PC: http://localhost:5000")
    print("⛔ Press Ctrl+C to stop")
    print()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == '__main__':
    main()