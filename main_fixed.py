# main_fixed.py
# Fixed Face Recognition System with proper phone camera integration and performance optimization

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

# Optimized Configuration
UNKNOWN_VIDEOS_DIR = "unknown/videos"
UNKNOWN_IMAGES_DIR = "unknown/images"
LIVE_STREAM_DIR = "live_stream"
CAMERA_RESOLUTION = (1280, 720)  # 720p
RECOGNITION_TOLERANCE = 0.6  # Slightly relaxed for better performance
COOLDOWN_SECONDS = 10
TTS_ENABLED = True

# Optimized Video Settings for better performance
VIDEO_CODEC = cv2.VideoWriter_fourcc(*'H264')  # Better compression
VIDEO_FPS = 15  # Reduced for better performance and smaller files
PROCESS_EVERY_N_FRAMES = 2  # Process every 2nd frame for recognition
MAX_RECORDING_DURATION = 30  # Max 30 seconds per recording

# Phone Camera Priority Sources (Updated for better phone detection)
CAMERA_SOURCES = [
    "http://192.168.29.64:8080",  # IP Webcam app (Most common)
    "http://192.168.0.100:8080/video",  # Alternative subnet
    "http://10.0.0.100:8080/video",     # Mobile hotspot range
    "http://192.168.43.100:8080/video", # Mobile hotspot (Samsung)
    "http://192.168.1.100:4747/video",  # DroidCam
    "http://192.168.1.100:8888/mjpeg",  # Alternative format
    0,  # PC webcam (fallback)
]

class OptimizedFaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.last_recognition_time = {}
        self.tts_engine = None
        self.camera = None
        self.running = False
        
        # Optimized video recording variables
        self.recording_unknown = False
        self.video_writer = None
        self.current_video_path = None
        self.recording_start_time = None
        self.frames_since_unknown = 0
        self.unknown_detected = False
        
        # Performance optimization
        self.frame_count = 0
        self.last_recognition_frame = 0
        self.detection_buffer = []  # Buffer for consistent detection
        
        # Live streaming optimized
        self.live_stream_enabled = True
        self.stream_frame = None
        self.stream_lock = threading.Lock()
        
        # Initialize components
        if TTS_ENABLED:
            self._initialize_tts()
        self._load_known_faces()
        self._ensure_directories()
        
        print("🔧 Optimized Face Recognition System initialized")
        print(f"📱 Priority: Phone camera sources")
        print(f"⚡ Performance: Process every {PROCESS_EVERY_N_FRAMES} frames")
        print(f"🎬 Video: {VIDEO_FPS} FPS, H.264 encoding")
    
    def _initialize_tts(self):
        """Initialize TTS with error handling"""
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 180)
            self.tts_engine.setProperty('volume', 0.8)
            print("🔊 TTS engine initialized")
        except Exception as e:
            print(f"⚠️  TTS initialization failed: {e}")
            self.tts_engine = None
    
    def _load_known_faces(self):
        """Load face encodings from database"""
        print("📚 Loading known face encodings...")
        
        self.known_face_encodings, self.known_face_names = load_encodings_from_database()
        
        if self.known_face_encodings:
            unique_names = list(set(self.known_face_names))
            print(f"✅ Loaded {len(self.known_face_encodings)} encodings for {len(unique_names)} people")
            print(f"👥 Known family: {', '.join(unique_names)}")
        else:
            print("⚠️  No known faces! Please run encodegenerator.py first.")
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [UNKNOWN_VIDEOS_DIR, UNKNOWN_IMAGES_DIR, LIVE_STREAM_DIR]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def _initialize_camera(self):
        """Initialize camera with phone priority"""
        print("📹 Initializing camera (Phone Priority)...")
        print("=" * 50)
        
        for i, source in enumerate(CAMERA_SOURCES):
            try:
                if isinstance(source, str):
                    print(f"  📱 Trying phone camera: {source}")
                else:
                    print(f"  💻 Trying PC webcam: Camera {source}")
                
                cap = cv2.VideoCapture(source)
                
                # Set properties for better performance
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RESOLUTION[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1])
                cap.set(cv2.CAP_PROP_FPS, 30)  # Request 30 FPS from camera
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
                
                # Test camera connection
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    camera_type = "📱 PHONE CAMERA" if isinstance(source, str) else "💻 PC WEBCAM"
                    print(f"✅ {camera_type} CONNECTED!")
                    print(f"📐 Resolution: {actual_width}x{actual_height}")
                    print(f"🔗 Source: {source}")
                    print("=" * 50)
                    
                    self.camera = cap
                    return True
                else:
                    cap.release()
                    
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                continue
        
        print("❌ No cameras available!")
        print("\n📱 Phone Camera Setup Instructions:")
        print("1. Install 'IP Webcam' app on your phone")
        print("2. Open app and tap 'Start Server'") 
        print("3. Note the IP address shown (e.g., 192.168.1.100)")
        print("4. Update CAMERA_SOURCES in this file with your phone's IP")
        print("5. Make sure phone and PC are on the same WiFi network")
        return False
    
    def _speak(self, text):
        """Non-blocking TTS"""
        if self.tts_engine and TTS_ENABLED:
            def speak_thread():
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except:
                    pass
            threading.Thread(target=speak_thread, daemon=True).start()
    
    def _start_video_recording(self, frame):
        """Start optimized video recording"""
        if self.recording_unknown:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self.current_video_path = os.path.join(UNKNOWN_VIDEOS_DIR, f"unknown_{timestamp}.mp4")
        
        # Get frame dimensions
        height, width = frame.shape[:2]
        
        # Initialize optimized video writer
        self.video_writer = cv2.VideoWriter(
            self.current_video_path,
            VIDEO_CODEC,
            VIDEO_FPS,
            (width, height)
        )
        
        if self.video_writer and self.video_writer.isOpened():
            self.recording_unknown = True
            self.recording_start_time = time.time()
            print(f"🎬 Recording started: {os.path.basename(self.current_video_path)}")
            return True
        else:
            print("❌ Failed to start video recording")
            if self.video_writer:
                self.video_writer.release()
            self.video_writer = None
            return False
    
    def _stop_video_recording(self):
        """Stop video recording and log to database"""
        if not self.recording_unknown or not self.video_writer:
            return None
        
        try:
            # Stop recording
            self.video_writer.release()
            self.recording_unknown = False
            
            # Calculate stats
            duration = time.time() - self.recording_start_time
            file_size = os.path.getsize(self.current_video_path) if os.path.exists(self.current_video_path) else 0
            
            print(f"🎬 Recording stopped: {os.path.basename(self.current_video_path)}")
            print(f"⏱️  Duration: {duration:.1f}s, Size: {file_size/1024/1024:.1f}MB")
            
            # Log to database
            log_activity(
                video_path=self.current_video_path,
                status="unknown",
                camera_id="phone_camera",
                video_duration=duration,
                file_size=file_size,
                capture_type="auto"
            )
            
            video_path = self.current_video_path
            self.current_video_path = None
            self.video_writer = None
            
            return video_path
            
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
            self.recording_unknown = False
            self.video_writer = None
            return None
    
    def _should_process_frame(self):
        """Determine if frame should be processed for face recognition"""
        return self.frame_count % PROCESS_EVERY_N_FRAMES == 0
    
    def _detect_faces_optimized(self, frame):
        """Optimized face detection"""
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find faces in small frame
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        # Scale back face locations
        face_locations = [(top*2, right*2, bottom*2, left*2) for (top, right, bottom, left) in face_locations]
        
        detected_faces = []
        unknown_detected = False
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(
                self.known_face_encodings, 
                face_encoding, 
                tolerance=RECOGNITION_TOLERANCE
            )
            
            name = "Unknown"
            confidence = 0
            
            if matches and any(matches):
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    confidence = max(0, (1 - face_distances[best_match_index]) * 100)
            
            detected_faces.append({
                'name': name,
                'confidence': confidence,
                'location': (top, right, bottom, left)
            })
            
            if name == "Unknown":
                unknown_detected = True
        
        return detected_faces, unknown_detected
    
    def _update_live_stream(self, frame):
        """Update live stream with thread safety"""
        if self.live_stream_enabled:
            try:
                with self.stream_lock:
                    # Resize for streaming
                    stream_frame = cv2.resize(frame, (640, 480))
                    ret, buffer = cv2.imencode('.jpg', stream_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    
                    if ret:
                        self.stream_frame = buffer.tobytes()
                        
                        # Save to file for web access
                        stream_path = os.path.join(LIVE_STREAM_DIR, "latest_frame.jpg")
                        with open(stream_path, 'wb') as f:
                            f.write(self.stream_frame)
            except Exception as e:
                print(f"Stream update error: {e}")
    
    def _process_frame(self, frame):
        """Optimized frame processing"""
        self.frame_count += 1
        
        # Process recognition only on specific frames
        if self._should_process_frame():
            detected_faces, unknown_detected_now = self._detect_faces_optimized(frame)
            
            # Add to detection buffer for stability
            self.detection_buffer.append(unknown_detected_now)
            if len(self.detection_buffer) > 3:
                self.detection_buffer.pop(0)
            
            # Require consistent detection
            consistent_unknown = sum(self.detection_buffer) >= 2
            
            # Handle recording logic
            if consistent_unknown and not self.recording_unknown:
                if self._start_video_recording(frame):
                    self.unknown_detected = True
                    self.frames_since_unknown = 0
            elif not consistent_unknown and self.recording_unknown:
                self.frames_since_unknown += 1
                # Stop recording after 60 frames (~2 seconds) without detection
                if self.frames_since_unknown > 60:
                    self._stop_video_recording()
                    self.unknown_detected = False
                    self.frames_since_unknown = 0
            
            # Handle recognition events
            for face_data in detected_faces:
                if face_data['name'] != "Unknown":
                    self._handle_known_person(face_data['name'], face_data['confidence'])
                else:
                    self._handle_unknown_person()
                
                # Draw face box
                self._draw_face_box(frame, face_data['location'], face_data['name'], face_data['confidence'])
        
        # Always write frame if recording
        if self.recording_unknown and self.video_writer:
            self.video_writer.write(frame)
        
        # Update live stream
        self._update_live_stream(frame)
        
        # Add recording indicator
        if self.recording_unknown:
            self._draw_recording_indicator(frame)
        
        # Check for max recording duration
        if self.recording_unknown and (time.time() - self.recording_start_time) > MAX_RECORDING_DURATION:
            print("⏱️  Max recording duration reached")
            self._stop_video_recording()
        
        return frame
    
    def _handle_known_person(self, name, confidence):
        """Handle known person detection"""
        if self._is_cooldown_active(name):
            return
        
        print(f"👥 Known: {name} ({confidence:.1f}%)")
        
        log_activity(
            status="known",
            name=name,
            confidence_score=confidence
        )
        
        self._speak(f"Welcome home, {name}!")
        self._update_cooldown(name)
    
    def _handle_unknown_person(self):
        """Handle unknown person detection"""
        if not self._is_cooldown_active("unknown"):
            print("🚨 Unknown person detected!")
            self._speak("Unknown person detected. Recording in progress.")
            self._update_cooldown("unknown")
    
    def _is_cooldown_active(self, name):
        """Check cooldown status"""
        if name not in self.last_recognition_time:
            return False
        return time.time() - self.last_recognition_time[name] < COOLDOWN_SECONDS
    
    def _update_cooldown(self, name):
        """Update cooldown timer"""
        self.last_recognition_time[name] = time.time()
    
    def _draw_face_box(self, frame, location, name, confidence):
        """Draw face detection box"""
        top, right, bottom, left = location
        
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
        label = f"{name}" if name != "Unknown" else "UNKNOWN"
        if confidence > 0:
            label += f" ({confidence:.0f}%)"
        
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, label, (left + 5, bottom - 5), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
    
    def _draw_recording_indicator(self, frame):
        """Draw recording indicator"""
        height, width = frame.shape[:2]
        
        # Pulsing red dot
        pulse = int(255 * (0.5 + 0.5 * np.sin(time.time() * 4)))
        cv2.circle(frame, (width - 30, 30), 8, (0, 0, pulse), -1)
        cv2.putText(frame, "REC", (width - 55, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def start_recognition(self, headless=False):
        """Start optimized recognition system"""
        print("🏠 Optimized Face Recognition System Starting...")
        print("=" * 60)
        
        if not self.known_face_encodings:
            print("⚠️  No known faces! System will only detect unknown persons.")
        
        if not self._initialize_camera():
            return False
        
        self.running = True
        
        print("✅ System running with optimizations:")
        print(f"📱 Camera: Phone priority, 720p")
        print(f"⚡ Performance: Process every {PROCESS_EVERY_N_FRAMES} frames")
        print(f"🎬 Recording: {VIDEO_FPS} FPS, H.264")
        print(f"🔴 Live stream: Active")
        print(f"💾 Max duration: {MAX_RECORDING_DURATION}s per recording")
        
        if not headless:
            print("🖥️  GUI Mode: Press 'q' to quit, 'r' to reload faces")
        else:
            print("🖥️  Headless Mode: Press Ctrl+C to quit")
        
        print("=" * 60)
        
        try:
            fps_start_time = time.time()
            fps_frame_count = 0
            
            while self.running:
                ret, frame = self.camera.read()
                
                if not ret:
                    print("❌ Camera disconnected!")
                    time.sleep(1)
                    continue
                
                # Process frame
                processed_frame = self._process_frame(frame)
                
                # Display if not headless
                if not headless:
                    cv2.imshow('📱 Phone Security System', processed_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('r'):
                        print("🔄 Reloading faces...")
                        self._load_known_faces()
                
                # FPS calculation
                fps_frame_count += 1
                if fps_frame_count % 150 == 0:  # Every 5 seconds at 30fps
                    elapsed = time.time() - fps_start_time
                    fps = fps_frame_count / elapsed
                    print(f"📊 Performance: {fps:.1f} FPS")
                
                # Small delay for headless mode
                if headless:
                    time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n⛔ Interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            self._cleanup()
        
        return True
    
    def _cleanup(self):
        """Clean up resources"""
        print("\n🧹 Cleaning up...")
        
        self.running = False
        
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
        
        print("✅ Cleanup completed")

def main():
    """Main function"""
    import sys
    
    print("📖 Usage:")
    print("  python main_fixed.py          - Phone camera with GUI")
    print("  python main_fixed.py headless - Phone camera headless mode")
    
    headless = len(sys.argv) > 1 and sys.argv[1].lower() == 'headless'
    
    system = OptimizedFaceRecognitionSystem()
    system.start_recognition(headless=headless)

if __name__ == "__main__":
    main()