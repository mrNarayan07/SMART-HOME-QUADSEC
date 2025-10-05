# main.py
# Face Recognition Home Security System - Enhanced Recognition Logic
# Real-time face recognition with video recording and live streaming

import cv2
import face_recognition
import numpy as np
import os
import time
import pyttsx3
import threading
from datetime import datetime
from pathlib import Path
import json

from database_setup_enhanced import log_activity, create_connection
from encodegenerator import load_encodings_from_database

# Enhanced Configuration
UNKNOWN_VIDEOS_DIR = "unknown/videos"
UNKNOWN_IMAGES_DIR = "unknown/images"
LIVE_STREAM_DIR = "live_stream"
CAMERA_RESOLUTION = (1280, 720)  # 720p resolution
RECOGNITION_TOLERANCE = 0.5
COOLDOWN_SECONDS = 10
TTS_ENABLED = True

# Video recording settings
VIDEO_CODEC = cv2.VideoWriter_fourcc(*'mp4v')
VIDEO_FPS = 30
VIDEO_QUALITY = 0.8  # 0.0 to 1.0

# Camera configuration for phone and live streaming
CAMERA_SOURCES = [
    0,  # Default webcam
    "http://192.168.1.100:8080/video",  # IP Webcam app
    "http://192.168.1.100:4747/video",  # DroidCam
    "http://192.168.1.100:8888/mjpeg",  # Another common format
]

class EnhancedFaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.last_recognition_time = {}
        self.tts_engine = None
        self.camera = None
        self.running = False
        
        # Video recording variables
        self.recording_unknown = False
        self.video_writer = None
        self.current_video_path = None
        self.recording_start_time = None
        self.unknown_face_tracker = {}  # Track unknown faces and their positions
        
        # Live streaming variables
        self.live_stream_enabled = True
        self.stream_frame = None
        self.stream_lock = threading.Lock()
        
        # Initialize components
        if TTS_ENABLED:
            self._initialize_tts()
        self._load_known_faces()
        self._ensure_directories()
    
    def _initialize_tts(self):
        """Initialize text-to-speech engine"""
        try:
            self.tts_engine = pyttsx3.init()
            
            voices = self.tts_engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'woman' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            self.tts_engine.setProperty('rate', 180)
            self.tts_engine.setProperty('volume', 0.8)
            
            print("🔊 TTS engine initialized successfully")
            
        except Exception as e:
            print(f"⚠️  TTS initialization failed: {e}")
            self.tts_engine = None
    
    def _load_known_faces(self):
        """Load face encodings from database"""
        print("📚 Loading known face encodings...")
        
        self.known_face_encodings, self.known_face_names = load_encodings_from_database()
        
        if self.known_face_encodings:
            unique_names = list(set(self.known_face_names))
            print(f"✅ Loaded {len(self.known_face_encodings)} face encodings for {len(unique_names)} people")
            print(f"👥 Known family members: {', '.join(unique_names)}")
        else:
            print("⚠️  No known faces loaded! Please run encodegenerator.py first.")
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [UNKNOWN_VIDEOS_DIR, UNKNOWN_IMAGES_DIR, LIVE_STREAM_DIR]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"📁 Created directory: {directory}")
    
    def _initialize_camera(self):
        """Initialize camera connection with enhanced settings"""
        print("📹 Initializing enhanced camera connection...")
        
        for i, source in enumerate(CAMERA_SOURCES):
            try:
                print(f"  Trying camera source {i + 1}: {source}")
                
                cap = cv2.VideoCapture(source)
                
                # Set enhanced camera properties
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RESOLUTION[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1])
                cap.set(cv2.CAP_PROP_FPS, VIDEO_FPS)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
                
                # Test camera
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    actual_fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    print(f"✅ Camera connected: {source}")
                    print(f"📐 Resolution: {actual_width}x{actual_height}")
                    print(f"🎬 FPS: {actual_fps}")
                    
                    self.camera = cap
                    return True
                else:
                    cap.release()
                    
            except Exception as e:
                print(f"  ❌ Failed to connect to {source}: {e}")
                continue
        
        print("❌ Could not connect to any camera source!")
        return False
    
    def _speak(self, text):
        """Speak text using TTS (non-blocking)"""
        if self.tts_engine and TTS_ENABLED:
            def speak_thread():
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception as e:
                    print(f"TTS error: {e}")
            
            thread = threading.Thread(target=speak_thread, daemon=True)
            thread.start()
    
    def _is_cooldown_active(self, name):
        """Check if person is still in cooldown period"""
        if name not in self.last_recognition_time:
            return False
        
        time_passed = time.time() - self.last_recognition_time[name]
        return time_passed < COOLDOWN_SECONDS
    
    def _update_cooldown(self, name):
        """Update last recognition time for cooldown"""
        self.last_recognition_time[name] = time.time()
    
    def _start_video_recording(self, frame):
        """Start recording video for unknown person"""
        if self.recording_unknown:
            return  # Already recording
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self.current_video_path = os.path.join(UNKNOWN_VIDEOS_DIR, f"unknown_{timestamp}.mp4")
        
        # Initialize video writer
        height, width = frame.shape[:2]
        self.video_writer = cv2.VideoWriter(
            self.current_video_path,
            VIDEO_CODEC,
            VIDEO_FPS,
            (width, height)
        )
        
        if self.video_writer.isOpened():
            self.recording_unknown = True
            self.recording_start_time = time.time()
            print(f"🎬 Started video recording: {os.path.basename(self.current_video_path)}")
        else:
            print("❌ Failed to initialize video writer")
            self.video_writer = None
    
    def _stop_video_recording(self):
        """Stop video recording and log to database"""
        if not self.recording_unknown or not self.video_writer:
            return None
        
        # Stop recording
        self.video_writer.release()
        self.recording_unknown = False
        
        # Calculate video duration and file size
        video_duration = time.time() - self.recording_start_time
        file_size = os.path.getsize(self.current_video_path) if os.path.exists(self.current_video_path) else 0
        
        print(f"🎬 Stopped video recording: {os.path.basename(self.current_video_path)}")
        print(f"⏱️  Duration: {video_duration:.2f} seconds")
        print(f"📦 File size: {file_size / 1024 / 1024:.2f} MB")
        
        # Log to database
        log_id = log_activity(
            video_path=self.current_video_path,
            status="unknown",
            camera_id="phone_camera",
            video_duration=video_duration,
            file_size=file_size,
            capture_type="auto"
        )
        
        video_path = self.current_video_path
        self.current_video_path = None
        self.video_writer = None
        self.recording_start_time = None
        
        return video_path
    
    def _write_video_frame(self, frame):
        """Write frame to video file during recording"""
        if self.recording_unknown and self.video_writer:
            self.video_writer.write(frame)
    
    def _update_live_stream(self, frame):
        """Update live stream frame for web interface"""
        if self.live_stream_enabled:
            with self.stream_lock:
                # Encode frame as JPEG for streaming
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    self.stream_frame = buffer.tobytes()
                    
                    # Save latest frame to disk for web access
                    stream_path = os.path.join(LIVE_STREAM_DIR, "latest_frame.jpg")
                    with open(stream_path, 'wb') as f:
                        f.write(self.stream_frame)
    
    def _detect_faces_advanced(self, frame):
        """Advanced face detection with tracking"""
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Find face locations and encodings
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")  # Use "cnn" for better accuracy
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        detected_faces = []
        unknown_faces_present = False
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(
                self.known_face_encodings, 
                face_encoding, 
                tolerance=RECOGNITION_TOLERANCE
            )
            
            face_distances = face_recognition.face_distance(
                self.known_face_encodings, 
                face_encoding
            )
            
            name = "Unknown"
            confidence = 0
            
            if matches and any(matches):
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    confidence = max(0, (1 - face_distances[best_match_index]) * 100)
            
            detected_faces.append({
                'name': name,
                'confidence': confidence,
                'location': (top, right, bottom, left),
                'encoding': face_encoding
            })
            
            if name == "Unknown":
                unknown_faces_present = True
        
        return detected_faces, unknown_faces_present
    
    def _process_frame(self, frame):
        """Enhanced frame processing with video recording"""
        detected_faces, unknown_faces_present = self._detect_faces_advanced(frame)
        
        # Handle video recording for unknown faces
        if unknown_faces_present and not self.recording_unknown:
            self._start_video_recording(frame)
        elif not unknown_faces_present and self.recording_unknown:
            # Stop recording after a delay to ensure person has left
            threading.Timer(2.0, self._stop_video_recording).start()
        
        # Write frame to video if recording
        if self.recording_unknown:
            self._write_video_frame(frame)
        
        # Process each detected face
        for face_data in detected_faces:
            if face_data['name'] != "Unknown":
                self._handle_known_person(
                    face_data['name'], 
                    face_data['confidence'], 
                    frame, 
                    face_data['location']
                )
            else:
                self._handle_unknown_person(frame, face_data['location'])
            
            # Draw face box and label
            self._draw_face_box(
                frame, 
                face_data['location'], 
                face_data['name'], 
                face_data['confidence']
            )
        
        # Update live stream
        self._update_live_stream(frame)
        
        # Add recording indicator
        if self.recording_unknown:
            self._draw_recording_indicator(frame)
        
        return frame
    
    def _handle_known_person(self, name, confidence, frame, face_location):
        """Handle detection of known family member"""
        if self._is_cooldown_active(name):
            return
        
        print(f"👥 Known person detected: {name} (Confidence: {confidence:.1f}%)")
        
        # Log to database (no video/image for known persons)
        log_activity(
            status="known",
            name=name,
            confidence_score=confidence,
            capture_type="auto"
        )
        
        # Greet with TTS
        greeting = f"Welcome home, {name}!"
        print(f"🔊 TTS: {greeting}")
        self._speak(greeting)
        
        self._update_cooldown(name)
    
    def _handle_unknown_person(self, frame, face_location):
        """Handle detection of unknown person"""
        if self._is_cooldown_active("unknown"):
            return
        
        print("🚨 Unknown person detected!")
        
        # Alert with TTS
        alert = "Unknown person detected. Recording in progress."
        print(f"🔊 TTS: {alert}")
        self._speak(alert)
        
        self._update_cooldown("unknown")
    
    def _draw_face_box(self, frame, face_location, name, confidence):
        """Draw enhanced face detection box"""
        top, right, bottom, left = face_location
        
        # Choose colors and styles
        if name == "Unknown":
            color = (0, 0, 255)  # Red
            bg_color = (0, 0, 200)
            label = "⚠️ UNKNOWN PERSON"
        else:
            color = (0, 255, 0)  # Green
            bg_color = (0, 200, 0)
            label = f"✅ {name} ({confidence:.1f}%)"
        
        # Draw main rectangle
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Draw label background
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1)[0]
        cv2.rectangle(
            frame, 
            (left, bottom - 35), 
            (left + label_size[0] + 10, bottom), 
            bg_color, 
            cv2.FILLED
        )
        
        # Draw label text
        cv2.putText(
            frame, 
            label, 
            (left + 5, bottom - 10), 
            cv2.FONT_HERSHEY_DUPLEX, 
            0.6, 
            (255, 255, 255), 
            1
        )
    
    def _draw_recording_indicator(self, frame):
        """Draw recording indicator on frame"""
        height, width = frame.shape[:2]
        
        # Draw red circle (recording indicator)
        cv2.circle(frame, (width - 30, 30), 10, (0, 0, 255), -1)
        
        # Draw "REC" text
        cv2.putText(
            frame, 
            "REC", 
            (width - 60, 35), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (0, 0, 255), 
            2
        )
        
        # Draw timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame, 
            timestamp, 
            (10, height - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (255, 255, 255), 
            1
        )
    
    def get_live_stream_frame(self):
        """Get latest frame for live streaming"""
        with self.stream_lock:
            return self.stream_frame
    
    def start_recognition(self):
        """Start the enhanced face recognition system"""
        print("🏠 Enhanced Face Recognition Home Security System")
        print("🚀 Starting real-time recognition with video recording...")
        print("=" * 60)
        
        if not self.known_face_encodings:
            print("❌ No known faces available. Please run encodegenerator.py first.")
            return False
        
        if not self._initialize_camera():
            return False
        
        self.running = True
        
        print("✅ System is running!")
        print("📹 Video recording: ON (720p)")
        print("🔴 Live streaming: ON")
        print("⏱️  Cooldown period: 10 seconds")
        print("🎯 Recognition tolerance: 0.5")
        print("Press 'q' to quit, 'r' to reload faces, 's' to toggle stream")
        print("=" * 60)
        
        try:
            frame_count = 0
            start_time = time.time()
            
            while self.running:
                ret, frame = self.camera.read()
                
                if not ret:
                    print("❌ Failed to read from camera")
                    break
                
                # Process every 3rd frame for performance (still record all frames)
                if frame_count % 3 == 0:
                    processed_frame = self._process_frame(frame)
                else:
                    processed_frame = frame
                    if self.recording_unknown:
                        self._write_video_frame(frame)
                    self._update_live_stream(frame)
                
                # Display frame
                cv2.imshow('Enhanced Security System', processed_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Quit command received")
                    break
                elif key == ord('r'):
                    print("\n🔄 Reloading known faces...")
                    self._load_known_faces()
                elif key == ord('s'):
                    self.live_stream_enabled = not self.live_stream_enabled
                    print(f"\n📺 Live streaming: {'ON' if self.live_stream_enabled else 'OFF'}")
                
                frame_count += 1
                
                # Performance monitoring
                if frame_count % 300 == 0:  # Every 10 seconds at 30 FPS
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"📊 Performance: {fps:.1f} FPS, Processed: {frame_count} frames")
        
        except KeyboardInterrupt:
            print("\n⛔ Interrupted by user")
        
        except Exception as e:
            print(f"\n❌ Error during recognition: {e}")
        
        finally:
            self._cleanup()
        
        return True
    
    def start_headless(self):
        """Start recognition without GUI (for server mode)"""
        print("🏠 Enhanced Face Recognition System (Headless Mode)")
        print("🚀 Starting recognition without display...")
        print("=" * 60)
        
        if not self.known_face_encodings:
            print("❌ No known faces available.")
            return False
        
        if not self._initialize_camera():
            return False
        
        self.running = True
        
        print("✅ System running in headless mode!")
        print("📹 Video recording: ON")
        print("🔴 Live streaming: ON")
        print("Press Ctrl+C to quit")
        print("=" * 60)
        
        try:
            while self.running:
                ret, frame = self.camera.read()
                
                if not ret:
                    print("❌ Failed to read from camera")
                    time.sleep(1)
                    continue
                
                self._process_frame(frame)
                time.sleep(0.033)  # ~30 FPS
        
        except KeyboardInterrupt:
            print("\n⛔ Interrupted by user")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        finally:
            self._cleanup()
        
        return True
    
    def _cleanup(self):
        """Clean up resources"""
        self.running = False
        
        # Stop any ongoing video recording
        if self.recording_unknown:
            self._stop_video_recording()
        
        if self.camera:
            self.camera.release()
        
        cv2.destroyAllWindows()
        
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except:
                pass
        
        print("🧹 Enhanced cleanup completed")

def main():
    """Main function with enhanced options"""
    import sys
    
    print("📖 Enhanced Usage:")
    print("  python main.py          - Start with GUI")
    print("  python main.py headless - Start without GUI (server)")
    print("  python main.py stream   - Stream only mode")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['help', '-h', '--help']:
        return
    
    headless_mode = len(sys.argv) > 1 and sys.argv[1].lower() == 'headless'
    stream_mode = len(sys.argv) > 1 and sys.argv[1].lower() == 'stream'
    
    system = EnhancedFaceRecognitionSystem()
    
    if headless_mode or stream_mode:
        success = system.start_headless()
    else:
        success = system.start_recognition()
    
    print("✅ Enhanced face recognition system ended")

if __name__ == "__main__":
    main()