# app_fixed.py
# Fixed Flask Web Interface with proper video serving and phone camera integration

from flask import Flask, render_template, request, jsonify, send_from_directory, Response, send_file
import sqlite3
import os
from datetime import datetime, timedelta
import json
from pathlib import Path
import mimetypes

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
app.secret_key = 'fixed_face_recognition_security_system_2024'

# Configuration
UNKNOWN_VIDEOS_DIR = "unknown/videos"
UNKNOWN_IMAGES_DIR = "unknown/images"
LIVE_STREAM_DIR = "live_stream"
ITEMS_PER_PAGE = 20

class FixedSecurityDashboard:
    def __init__(self):
        self.ensure_directories()
    
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
            
            # Build query with proper column handling
            query = """
                SELECT id, timestamp, image_path, video_path, status, name, 
                       camera_id, confidence_score, 
                       COALESCE(video_duration, 0) as video_duration, 
                       COALESCE(file_size, 0) as file_size, 
                       COALESCE(capture_type, 'auto') as capture_type, 
                       notes, deleted_at
                FROM activity_logs 
                WHERE 1=1
            """
            params = []
            
            # Include/exclude deleted logs
            if not include_deleted:
                query += " AND (deleted_at IS NULL OR deleted_at = '')"
            
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
                "SELECT id, timestamp, image_path, video_path, status, name, camera_id, confidence_score, COALESCE(video_duration, 0) as video_duration, COALESCE(file_size, 0) as file_size, COALESCE(capture_type, 'auto') as capture_type, notes, deleted_at FROM activity_logs", 
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
        """Get enhanced dashboard statistics with error handling"""
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # Basic counts with error handling
            try:
                cursor.execute("SELECT COUNT(*) FROM activity_logs WHERE (deleted_at IS NULL OR deleted_at = '')")
                total_logs = cursor.fetchone()[0]
            except:
                total_logs = 0
            
            # Status breakdown
            try:
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM activity_logs 
                    WHERE (deleted_at IS NULL OR deleted_at = '')
                    GROUP BY status
                """)
                status_counts = dict(cursor.fetchall())
            except:
                status_counts = {}
            
            # Recent activity (last 24 hours)
            try:
                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM activity_logs 
                    WHERE timestamp >= ? AND (deleted_at IS NULL OR deleted_at = '')
                """, (yesterday,))
                recent_activity = cursor.fetchone()[0]
            except:
                recent_activity = 0
            
            # Video statistics with error handling
            try:
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN video_path IS NOT NULL AND video_path != '' THEN 1 END) as video_count,
                        AVG(CASE WHEN video_duration IS NOT NULL THEN video_duration END) as avg_duration,
                        SUM(CASE WHEN file_size IS NOT NULL THEN file_size END) as total_size
                    FROM activity_logs 
                    WHERE (deleted_at IS NULL OR deleted_at = '')
                """)
                video_stats = cursor.fetchone()
            except:
                video_stats = (0, 0, 0)
            
            # Family members count
            try:
                cursor.execute("SELECT COUNT(*) FROM family_members WHERE is_active = 1")
                family_count = cursor.fetchone()[0]
            except:
                family_count = 0
            
            conn.close()
            
            return {
                'total_logs': total_logs,
                'known_count': status_counts.get('known', 0),
                'unknown_count': status_counts.get('unknown', 0),
                'manual_count': status_counts.get('manual', 0),
                'recent_activity': recent_activity,
                'family_count': family_count,
                'most_active_member': "N/A",
                'video_count': video_stats[0] if video_stats else 0,
                'avg_video_duration': round(video_stats[1] or 0, 2),
                'total_storage_mb': round((video_stats[2] or 0) / 1024 / 1024, 2)
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
                'total_storage_mb': 0
            }

    def format_log_for_display(self, log):
        """Format log entry for enhanced display with error handling"""
        try:
            (log_id, timestamp, image_path, video_path, status, name, camera_id, 
             confidence_score, video_duration, file_size, capture_type, notes, deleted_at) = log
        except ValueError:
            # Handle missing columns
            log_id, timestamp, image_path, status, name, camera_id, confidence_score = log[:7]
            video_path = log[3] if len(log) > 3 else None
            video_duration = log[8] if len(log) > 8 else 0
            file_size = log[9] if len(log) > 9 else 0
            capture_type = log[10] if len(log) > 10 else 'auto'
            notes = log[11] if len(log) > 11 else None
            deleted_at = log[12] if len(log) > 12 else None
        
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

# Initialize dashboard
dashboard = FixedSecurityDashboard()

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

# FIXED: Proper video serving with correct MIME types and range support
@app.route('/video/<path:filename>')
def serve_video(filename):
    """Serve video files with proper MIME types and range support for browser playback"""
    try:
        video_path = os.path.join(UNKNOWN_VIDEOS_DIR, filename)
        
        if not os.path.exists(video_path):
            print(f"Video not found: {video_path}")
            return "Video not found", 404
        
        # Get file info
        file_size = os.path.getsize(video_path)
        
        # Handle range requests for video streaming
        range_header = request.headers.get('Range', None)
        if range_header:
            byte_start, byte_end = 0, file_size - 1
            
            # Parse range header
            if range_header:
                match = range_header.replace('bytes=', '').split('-')
                byte_start = int(match[0]) if match[0] else 0
                byte_end = int(match[1]) if match[1] else file_size - 1
            
            # Ensure valid range
            byte_start = max(0, byte_start)
            byte_end = min(byte_end, file_size - 1)
            content_length = byte_end - byte_start + 1
            
            def generate():
                with open(video_path, 'rb') as f:
                    f.seek(byte_start)
                    remaining = content_length
                    while remaining:
                        chunk_size = min(8192, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data
            
            response = Response(
                generate(),
                206,  # Partial Content
                {
                    'Content-Type': 'video/mp4',
                    'Accept-Ranges': 'bytes',
                    'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                    'Content-Length': str(content_length),
                    'Cache-Control': 'no-cache',
                }
            )
            return response
        else:
            # Serve full file
            return send_file(
                video_path,
                mimetype='video/mp4',
                as_attachment=False,
                conditional=True
            )
            
    except Exception as e:
        print(f"Error serving video {filename}: {e}")
        return f"Error serving video: {str(e)}", 500

@app.route('/image/<path:filename>')
def serve_image(filename):
    """Serve images with proper handling"""
    try:
        # Try images directory first, then videos directory
        image_path = None
        
        if os.path.exists(os.path.join(UNKNOWN_IMAGES_DIR, filename)):
            image_path = os.path.join(UNKNOWN_IMAGES_DIR, filename)
        elif os.path.exists(os.path.join(UNKNOWN_VIDEOS_DIR, filename)):
            image_path = os.path.join(UNKNOWN_VIDEOS_DIR, filename)
        
        if image_path:
            return send_file(image_path, conditional=True)
        else:
            return "Image not found", 404
            
    except Exception as e:
        print(f"Error serving image {filename}: {e}")
        return f"Error serving image: {str(e)}", 500

@app.route('/live_stream')
def live_stream():
    """Live stream endpoint with better error handling"""
    def generate():
        import time
        while True:
            try:
                frame_path = os.path.join(LIVE_STREAM_DIR, "latest_frame.jpg")
                if os.path.exists(frame_path):
                    with open(frame_path, 'rb') as f:
                        frame_data = f.read()
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                else:
                    # Placeholder image if no stream
                    time.sleep(0.5)
                    placeholder = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\xc8\x01\x90\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1c\x00\x00\x02\x03\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\xff\xc4\x00\x1a\x10\x00\x03\x01\x00\x03\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x11\x06!\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\x9d\xf29wU5Q\x96\xfd\x06\xd7\x1b\xbb-\x83\x18\xda\x05X\x9a\x9d"r\x93\xdci%\x14\x7f\x9c\xdc\x8a(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00\xff\xd9'
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n')
            except Exception as e:
                print(f"Stream error: {e}")
                time.sleep(1)
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

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
                'message': f'Log {log_id} {"archived" if soft_delete else "permanently deleted"}'
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

@app.route('/api/system/status')
def system_status():
    """Enhanced system status information"""
    try:
        # Check database connection
        conn = create_connection()
        db_status = "Connected" if conn else "Error"
        if conn:
            conn.close()
        
        # Check directories
        dirs_status = {
            'known': os.path.exists('known'),
            'unknown_videos': os.path.exists(UNKNOWN_VIDEOS_DIR),
            'unknown_images': os.path.exists(UNKNOWN_IMAGES_DIR),
            'live_stream': os.path.exists(LIVE_STREAM_DIR)
        }
        
        # Check if main recognition is running
        import psutil
        main_running = any('main' in ' '.join(p.cmdline()) 
                          for p in psutil.process_iter(['cmdline']))
        
        # Check live stream status
        live_stream_active = os.path.exists(os.path.join(LIVE_STREAM_DIR, "latest_frame.jpg"))
        
        return jsonify({
            'database': db_status,
            'directories': dirs_status,
            'recognition_system': 'Running' if main_running else 'Stopped',
            'live_stream': 'Active' if live_stream_active else 'Inactive',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'database': 'Error',
            'directories': {},
            'recognition_system': 'Unknown',
            'live_stream': 'Unknown',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

def main():
    """Main function to run the fixed Flask app"""
    print("🌐 Fixed Face Recognition Security System - Web Dashboard")
    print("=" * 60)
    
    if not os.path.exists(DATABASE_PATH):
        print("⚠️  Database not found! Please run migrate_database.py first.")
        return
    
    print(f"📊 Fixed dashboard starting...")
    print(f"🗃️  Database: {DATABASE_PATH}")
    print(f"📹 Videos: {UNKNOWN_VIDEOS_DIR}")
    print(f"🎥 Video playback: Fixed with proper MIME types and range support")
    print("=" * 60)
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        print("🐛 Debug mode")
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
        return
    
    print("🚀 Starting fixed web server...")
    print("📱 Phone Dashboard: http://[YOUR_PHONE_IP]:5000")
    print("💻 PC Dashboard: http://localhost:5000")
    print("🎥 Videos now properly play in browser!")
    print("📷 Phone camera integration ready!")
    print("⛔ Press Ctrl+C to stop")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n👋 Fixed server stopped")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == '__main__':
    main()