# app.py
# Enhanced Face Recognition Home Security System - Flask Web Interface
# Dashboard with live streaming, video player, deletion, and in-browser capture

from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import sqlite3
import os
from datetime import datetime, timedelta
import json
from pathlib import Path
import cv2
import base64
import threading
import time

from database_setup_enhanced import (
    create_connection, 
    get_recent_logs, 
    delete_activity_log,
    bulk_delete_logs,
    get_storage_stats,
    DATABASE_PATH
)

# Flask app configuration
app = Flask(__name__)
app.secret_key = 'enhanced_face_recognition_security_system_2024'

# Enhanced Configuration
UNKNOWN_VIDEOS_DIR = "unknown/videos"
UNKNOWN_IMAGES_DIR = "unknown/images"
LIVE_STREAM_DIR = "live_stream"
ITEMS_PER_PAGE = 20
MAX_LOGS_DISPLAY = 1000

class EnhancedSecurityDashboard:
    def __init__(self):
        self.ensure_directories()
        self.live_stream_active = False
        self.camera_feed = None
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        dirs = [UNKNOWN_VIDEOS_DIR, UNKNOWN_IMAGES_DIR, LIVE_STREAM_DIR, 
                'static', 'static/css', 'static/js', 'templates']
        for directory in dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def get_logs_with_pagination(self, page=1, per_page=ITEMS_PER_PAGE, 
                                status_filter=None, name_filter=None, 
                                date_filter=None, include_deleted=False):
        """Get activity logs with enhanced filtering"""
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT id, timestamp, image_path, video_path, status, name, 
                       camera_id, confidence_score, video_duration, file_size, 
                       capture_type, notes, deleted_at
                FROM activity_logs 
                WHERE 1=1
            """
            params = []
            
            # Include/exclude deleted logs
            if not include_deleted:
                query += " AND deleted_at IS NULL"
            
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
                    pass
            
            # Add ordering and pagination
            query += " ORDER BY timestamp DESC"
            
            # Get total count
            count_query = query.replace(
                "SELECT id, timestamp, image_path, video_path, status, name, camera_id, confidence_score, video_duration, file_size, capture_type, notes, deleted_at FROM activity_logs", 
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

    def get_enhanced_statistics(self):
        """Get enhanced dashboard statistics"""
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # Basic counts
            cursor.execute("SELECT COUNT(*) FROM activity_logs WHERE deleted_at IS NULL")
            total_logs = cursor.fetchone()[0]
            
            # Status breakdown
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM activity_logs 
                WHERE deleted_at IS NULL 
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Recent activity (last 24 hours)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM activity_logs 
                WHERE timestamp >= ? AND deleted_at IS NULL
            """, (yesterday,))
            recent_activity = cursor.fetchone()[0]
            
            # Video statistics
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN video_path IS NOT NULL THEN 1 END) as video_count,
                    AVG(video_duration) as avg_duration,
                    SUM(file_size) as total_size
                FROM activity_logs 
                WHERE deleted_at IS NULL
            """)
            video_stats = cursor.fetchone()
            
            # Family members count
            cursor.execute("SELECT COUNT(*) FROM family_members WHERE is_active = 1")
            family_count = cursor.fetchone()[0]
            
            # Most active family member (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT name, COUNT(*) as count 
                FROM activity_logs 
                WHERE status = 'known' AND timestamp >= ? 
                AND name IS NOT NULL AND deleted_at IS NULL
                GROUP BY name 
                ORDER BY count DESC 
                LIMIT 1
            """, (week_ago,))
            
            most_active = cursor.fetchone()
            
            # Storage stats
            storage_stats = get_storage_stats()
            
            conn.close()
            
            return {
                'total_logs': total_logs,
                'known_count': status_counts.get('known', 0),
                'unknown_count': status_counts.get('unknown', 0),
                'manual_count': status_counts.get('manual', 0),
                'recent_activity': recent_activity,
                'family_count': family_count,
                'most_active_member': most_active[0] if most_active else "None",
                'video_count': video_stats[0] if video_stats else 0,
                'avg_video_duration': round(video_stats[1] or 0, 2),
                'total_storage_mb': round((video_stats[2] or 0) / 1024 / 1024, 2),
                'storage_stats': storage_stats
            }
            
        except Exception as e:
            print(f"Error getting enhanced statistics: {e}")
            return {
                'total_logs': 0,
                'known_count': 0,
                'unknown_count': 0,
                'manual_count': 0,
                'recent_activity': 0,
                'family_count': 0,
                'most_active_member': 'None',
                'video_count': 0,
                'avg_video_duration': 0,
                'total_storage_mb': 0,
                'storage_stats': {}
            }

    def format_log_for_display(self, log):
        """Format log entry for enhanced display"""
        (log_id, timestamp, image_path, video_path, status, name, camera_id, 
         confidence_score, video_duration, file_size, capture_type, notes, deleted_at) = log
        
        # Parse timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            relative_time = self.get_relative_time(dt)
        except:
            formatted_time = timestamp
            relative_time = "Unknown"
        
        # Check if files exist
        image_exists = bool(image_path and os.path.exists(image_path))
        video_exists = bool(video_path and os.path.exists(video_path))
        
        # Format file size
        file_size_mb = round(file_size / 1024 / 1024, 2) if file_size else None
        
        return {
            'id': log_id,
            'timestamp': formatted_time,
            'relative_time': relative_time,
            'image_path': image_path,
            'video_path': video_path,
            'image_exists': image_exists,
            'video_exists': video_exists,
            'status': status,
            'name': name or 'Unknown',
            'camera_id': camera_id or 'phone_camera',
            'confidence_score': round(confidence_score, 1) if confidence_score else None,
            'video_duration': round(video_duration, 1) if video_duration else None,
            'file_size_mb': file_size_mb,
            'capture_type': capture_type or 'auto',
            'notes': notes,
            'is_deleted': bool(deleted_at),
            'status_class': 'success' if status == 'known' else 'warning' if status == 'manual' else 'danger',
            'status_icon': '👤' if status == 'known' else '📱' if status == 'manual' else '🚨'
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

# Initialize enhanced dashboard
dashboard = EnhancedSecurityDashboard()

@app.route('/')
def index():
    """Enhanced main dashboard page"""
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    name_filter = request.args.get('name', '').strip()
    date_filter = request.args.get('date', '').strip()
    include_deleted = request.args.get('include_deleted', False, type=bool)
    
    # Get logs with filters
    logs_data = dashboard.get_logs_with_pagination(
        page=page,
        status_filter=status_filter,
        name_filter=name_filter,
        date_filter=date_filter,
        include_deleted=include_deleted
    )
    
    # Format logs for display
    formatted_logs = []
    for log in logs_data['logs']:
        formatted_logs.append(dashboard.format_log_for_display(log))
    
    # Get enhanced statistics
    stats = dashboard.get_enhanced_statistics()
    
    return render_template('enhanced_dashboard.html', 
                         logs=formatted_logs,
                         pagination=logs_data,
                         stats=stats,
                         filters={
                             'status': status_filter,
                             'name': name_filter,
                             'date': date_filter,
                             'include_deleted': include_deleted
                         })

@app.route('/camera')
def camera_page():
    """In-browser camera capture page"""
    return render_template('camera_capture.html')

@app.route('/live')
def live_stream_page():
    """Live stream viewing page"""
    return render_template('live_stream.html')

@app.route('/api/logs')
def api_logs():
    """Enhanced API endpoint for getting logs"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    name_filter = request.args.get('name', '').strip()
    date_filter = request.args.get('date', '').strip()
    include_deleted = request.args.get('include_deleted', False, type=bool)
    
    logs_data = dashboard.get_logs_with_pagination(
        page=page,
        status_filter=status_filter,
        name_filter=name_filter,
        date_filter=date_filter,
        include_deleted=include_deleted
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
    """Enhanced API endpoint for getting dashboard statistics"""
    stats = dashboard.get_enhanced_statistics()
    return jsonify(stats)

@app.route('/api/delete_log/<int:log_id>', methods=['DELETE'])
def api_delete_log(log_id):
    """Delete a single activity log"""
    try:
        soft_delete = request.args.get('soft', 'true').lower() == 'true'
        success = delete_activity_log(log_id, soft_delete=soft_delete)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Log {log_id} {"soft" if soft_delete else "permanently"} deleted'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to delete log {log_id}'
            }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting log: {str(e)}'
        }), 500

@app.route('/api/delete_logs', methods=['DELETE'])
def api_delete_logs():
    """Bulk delete activity logs"""
    try:
        data = request.get_json()
        log_ids = data.get('log_ids', [])
        soft_delete = data.get('soft_delete', True)
        
        if not log_ids:
            return jsonify({
                'success': False,
                'message': 'No log IDs provided'
            }), 400
        
        deleted_count = bulk_delete_logs(log_ids, soft_delete=soft_delete)
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} logs {"soft" if soft_delete else "permanently"} deleted',
            'deleted_count': deleted_count
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting logs: {str(e)}'
        }), 500

@app.route('/api/capture', methods=['POST'])
def api_capture():
    """Handle in-browser camera captures"""
    try:
        data = request.get_json()
        image_data = data.get('image_data')
        notes = data.get('notes', '')
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image data provided'
            }), 400
        
        # Decode base64 image
        image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64,
        image_bytes = base64.b64decode(image_data)
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"manual_{timestamp}.jpg"
        image_path = os.path.join(UNKNOWN_IMAGES_DIR, filename)
        
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        # Log to database
        log_id = log_activity(
            image_path=image_path,
            status="manual",
            name="Manual Capture",
            camera_id="web_browser",
            file_size=len(image_bytes),
            capture_type="manual",
            notes=notes
        )
        
        return jsonify({
            'success': True,
            'message': 'Image captured and logged successfully',
            'log_id': log_id,
            'filename': filename
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error capturing image: {str(e)}'
        }), 500

@app.route('/video/<path:filename>')
def serve_video(filename):
    """Serve video files from unknown videos directory"""
    try:
        return send_from_directory(UNKNOWN_VIDEOS_DIR, filename)
    except FileNotFoundError:
        return "Video not found", 404

@app.route('/image/<path:filename>')
def serve_image(filename):
    """Serve images from unknown faces directory"""
    try:
        # Try videos directory first, then images directory
        if os.path.exists(os.path.join(UNKNOWN_IMAGES_DIR, filename)):
            return send_from_directory(UNKNOWN_IMAGES_DIR, filename)
        else:
            return send_from_directory(UNKNOWN_VIDEOS_DIR, filename)
    except FileNotFoundError:
        return "Image not found", 404

@app.route('/live_stream')
def live_stream():
    """Live stream endpoint"""
    def generate():
        while True:
            # Check for latest frame
            frame_path = os.path.join(LIVE_STREAM_DIR, "latest_frame.jpg")
            if os.path.exists(frame_path):
                with open(frame_path, 'rb') as f:
                    frame_data = f.read()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            else:
                # Return placeholder if no frame available
                time.sleep(0.1)
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/system/status')
def system_status():
    """Enhanced system status information"""
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
            'unknown_videos': os.path.exists(UNKNOWN_VIDEOS_DIR),
            'unknown_images': os.path.exists(UNKNOWN_IMAGES_DIR),
            'live_stream': os.path.exists(LIVE_STREAM_DIR),
            'templates': os.path.exists('templates'),
            'static': os.path.exists('static')
        }
        
        # Check if main.py is running
        import psutil
        main_running = any('main' in ' '.join(p.cmdline()) 
                          for p in psutil.process_iter(['cmdline']))
        
        # Check live stream status
        live_stream_active = os.path.exists(os.path.join(LIVE_STREAM_DIR, "latest_frame.jpg"))
        
        # Get storage stats
        storage_stats = get_storage_stats()
        
        return jsonify({
            'database': db_status,
            'directories': dirs_status,
            'recognition_system': 'Running' if main_running else 'Stopped',
            'live_stream': 'Active' if live_stream_active else 'Inactive',
            'storage_stats': storage_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'database': 'Error',
            'directories': {},
            'recognition_system': 'Unknown',
            'live_stream': 'Unknown',
            'storage_stats': {},
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404,
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error"), 500

def main():
    """Main function to run the enhanced Flask app"""
    print("🌐 Enhanced Face Recognition Security System - Web Dashboard")
    print("=" * 60)
    
    # Check if database exists
    if not os.path.exists(DATABASE_PATH):
        print("⚠️  Database not found! Please run database_setup_enhanced.py first.")
        return
    
    print(f"📊 Enhanced dashboard starting...")
    print(f"🗃️  Database: {DATABASE_PATH}")
    print(f"📹 Videos: {UNKNOWN_VIDEOS_DIR}")
    print(f"📷 Images: {UNKNOWN_IMAGES_DIR}")
    print(f"🔴 Live stream: {LIVE_STREAM_DIR}")
    print("=" * 60)
    
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'debug':
            print("🐛 Starting in debug mode...")
            app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
            return
    
    print("🚀 Starting enhanced web server...")
    print("📱 Phone access: http://[YOUR_IP]:5000")
    print("💻 PC access: http://localhost:5000")
    print("🎥 Live stream: http://localhost:5000/live")
    print("📷 Camera capture: http://localhost:5000/camera")
    print("⛔ Press Ctrl+C to stop")
    print()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n👋 Enhanced server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == '__main__':
    main()