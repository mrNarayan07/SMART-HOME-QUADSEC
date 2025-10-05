# main.py
# Face Recognition Home Security System - Main Recognition Logic
# Real-time face recognition with phone camera integration

import cv2
import face_recognition
import numpy as np
import os
import time
import pyttsx3
import threading
from datetime import datetime
from pathlib import Path

from database_setup import log_activity, create_connection
from encodegenerator import load_encodings_from_database

# Configuration
UNKNOWN_FACES_DIR = "unknown"
CAMERA_RESOLUTION = (640, 480)
RECOGNITION_TOLERANCE = 0.5  # Lower = more strict
COOLDOWN_SECONDS = 10
TTS_ENABLED = True

# Camera configuration for phone
# Common IP camera URLs - user can modify as needed
CAMERA_SOURCES = [
    0,  # Default webcam
    "http://192.168.1.100:8080/video",  # IP Webcam app
    "http://192.168.1.100:4747/video",  # DroidCam
    "http://192.168.1.100:8888/mjpeg",  # Another common format
]

class FaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.last_recognition_time = {}  # Track cooldown per person
        self.tts_engine = None
        self.camera = None
        self.running = False
        
        # Initialize TTS
        if TTS_ENABLED:
            self._initialize_tts()
        
        # Load face encodings
        self._load_known_faces()
        
        # Create unknown faces directory
        self._ensure_directories()
    
    def _initialize_tts(self):
        """Initialize text-to-speech engine"""
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configure TTS settings
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Try to use a female voice if available
                for voice in voices:
                    if 'female' in voice.name.lower() or 'woman' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            # Set speech rate and volume
            self.tts_engine.setProperty('rate', 180)  # Words per minute
            self.tts_engine.setProperty('volume', 0.8)  # Volume level (0.0 to 1.0)
            
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
        if not os.path.exists(UNKNOWN_FACES_DIR):
            os.makedirs(UNKNOWN_FACES_DIR)
            print(f"📁 Created directory: {UNKNOWN_FACES_DIR}")
    
    def _initialize_camera(self):
        """Initialize camera connection"""
        print("📹 Initializing camera connection...")
        
        for i, source in enumerate(CAMERA_SOURCES):
            try:
                print(f"  Trying camera source {i + 1}: {source}")
                
                cap = cv2.VideoCapture(source)
                
                # Set camera properties
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RESOLUTION[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1])
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Test if camera works
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    print(f"✅ Camera connected successfully: {source}")
                    self.camera = cap
                    return True
                else:
                    cap.release()
                    
            except Exception as e:
                print(f"  ❌ Failed to connect to {source}: {e}")
                continue
        
        print("❌ Could not connect to any camera source!")
        print("📝 Phone camera setup:")
        print("  1. Install 'IP Webcam' or 'DroidCam' app on your phone")
        print("  2. Start streaming and note the IP address")
        print("  3. Update CAMERA_SOURCES in this file with your phone's IP")
        return False
    
    def _speak(self, text):
        """Speak text using TTS (in separate thread to avoid blocking)"""
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
    
    def _save_unknown_face(self, face_image):
        """Save unknown face to unknown directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"unknown_{timestamp}.jpg"
        filepath = os.path.join(UNKNOWN_FACES_DIR, filename)
        
        # Save the cropped face image
        success = cv2.imwrite(filepath, face_image)
        
        if success:
            print(f"📸 Unknown face saved: {filename}")
            return filepath
        else:
            print(f"❌ Failed to save unknown face: {filename}")
            return None
    
    def _process_frame(self, frame):
        """Process a single frame for face recognition"""
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Find face locations and encodings
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        # Process each face found
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            
            # Try to match with known faces
            matches = face_recognition.compare_faces(
                self.known_face_encodings, 
                face_encoding, 
                tolerance=RECOGNITION_TOLERANCE
            )
            
            # Calculate face distances for confidence
            face_distances = face_recognition.face_distance(
                self.known_face_encodings, 
                face_encoding
            )
            
            name = "Unknown"
            confidence = 0
            
            if matches and any(matches):
                # Find best match
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    # Convert distance to confidence percentage
                    confidence = max(0, (1 - face_distances[best_match_index]) * 100)
            
            # Handle recognized person
            if name != "Unknown":
                self._handle_known_person(name, confidence, frame, (top, right, bottom, left))
            else:
                self._handle_unknown_person(frame, (top, right, bottom, left))
            
            # Draw rectangle and label on frame
            self._draw_face_box(frame, (top, right, bottom, left), name, confidence)
        
        return frame
    
    def _handle_known_person(self, name, confidence, frame, face_location):
        """Handle detection of known family member"""
        if self._is_cooldown_active(name):
            return  # Skip if in cooldown period
        
        print(f"👥 Known person detected: {name} (Confidence: {confidence:.1f}%)")
        
        # Log to database
        log_activity(
            image_path="",  # We're not saving images for known faces
            status="known",
            name=name,
            confidence_score=confidence
        )
        
        # Greet with TTS
        greeting = f"Welcome home, {name}!"
        print(f"🔊 TTS: {greeting}")
        self._speak(greeting)
        
        # Update cooldown
        self._update_cooldown(name)
    
    def _handle_unknown_person(self, frame, face_location):
        """Handle detection of unknown person"""
        if self._is_cooldown_active("unknown"):
            return  # Skip if in cooldown period
        
        print("🚨 Unknown person detected!")
        
        # Extract face region
        top, right, bottom, left = face_location
        face_image = frame[top:bottom, left:right]
        
        # Save unknown face
        saved_path = self._save_unknown_face(face_image)
        
        if saved_path:
            # Log to database
            log_activity(
                image_path=saved_path,
                status="unknown",
                name=None
            )
            
            # Alert with TTS
            alert = "Unknown person detected. Security alert!"
            print(f"🔊 TTS: {alert}")
            self._speak(alert)
        
        # Update cooldown for unknown detections
        self._update_cooldown("unknown")
    
    def _draw_face_box(self, frame, face_location, name, confidence):
        """Draw rectangle and label around detected face"""
        top, right, bottom, left = face_location
        
        # Choose color based on recognition
        if name == "Unknown":
            color = (0, 0, 255)  # Red for unknown
            label = "Unknown Person"
        else:
            color = (0, 255, 0)  # Green for known
            label = f"{name} ({confidence:.1f}%)"
        
        # Draw rectangle
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Draw label background
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        
        # Draw label text
        cv2.putText(frame, label, (left + 6, bottom - 6), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
    
    def start_recognition(self):
        """Start the face recognition system"""
        print("🏠 Face Recognition Home Security System")
        print("🚀 Starting real-time recognition...")
        print("=" * 50)
        
        # Check if we have known faces
        if not self.known_face_encodings:
            print("❌ No known faces available. Please run encodegenerator.py first.")
            return False
        
        # Initialize camera
        if not self._initialize_camera():
            return False
        
        self.running = True
        
        print("✅ System is running! Press 'q' to quit.")
        print(f"⏱️  Cooldown period: {COOLDOWN_SECONDS} seconds")
        print(f"🎯 Recognition tolerance: {RECOGNITION_TOLERANCE}")
        print("=" * 50)
        
        try:
            while self.running:
                ret, frame = self.camera.read()
                
                if not ret:
                    print("❌ Failed to read from camera")
                    break
                
                # Process frame for face recognition
                processed_frame = self._process_frame(frame)
                
                # Display frame (optional - can be disabled for headless mode)
                cv2.imshow('Face Recognition Security System', processed_frame)
                
                # Check for quit command
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Quit command received")
                    break
                elif key == ord('r'):
                    print("\n🔄 Reloading known faces...")
                    self._load_known_faces()
        
        except KeyboardInterrupt:
            print("\n⛔ Interrupted by user")
        
        except Exception as e:
            print(f"\n❌ Error during recognition: {e}")
        
        finally:
            self._cleanup()
        
        return True
    
    def start_headless(self):
        """Start recognition without GUI (for server/headless mode)"""
        print("🏠 Face Recognition Home Security System (Headless Mode)")
        print("🚀 Starting recognition without display...")
        print("=" * 50)
        
        # Check if we have known faces
        if not self.known_face_encodings:
            print("❌ No known faces available. Please run encodegenerator.py first.")
            return False
        
        # Initialize camera
        if not self._initialize_camera():
            return False
        
        self.running = True
        
        print("✅ System is running in headless mode! Press Ctrl+C to quit.")
        print(f"⏱️  Cooldown period: {COOLDOWN_SECONDS} seconds")
        print("=" * 50)
        
        try:
            while self.running:
                ret, frame = self.camera.read()
                
                if not ret:
                    print("❌ Failed to read from camera")
                    time.sleep(1)
                    continue
                
                # Process frame for face recognition
                self._process_frame(frame)
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n⛔ Interrupted by user")
        
        except Exception as e:
            print(f"\n❌ Error during recognition: {e}")
        
        finally:
            self._cleanup()
        
        return True
    
    def _cleanup(self):
        """Clean up resources"""
        self.running = False
        
        if self.camera:
            self.camera.release()
        
        cv2.destroyAllWindows()
        
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except:
                pass
        
        print("🧹 Cleanup completed")

def print_usage():
    """Print usage instructions"""
    print("📖 Usage:")
    print("  python main.py          - Start with GUI (default)")
    print("  python main.py headless - Start without GUI (server mode)")
    print()
    print("📝 Phone Camera Setup:")
    print("  1. Install IP Webcam app on your phone")
    print("  2. Start streaming and note the IP address")
    print("  3. Update CAMERA_SOURCES in main.py if needed")
    print()
    print("⌨️  Controls (GUI mode):")
    print("  'q' - Quit application")
    print("  'r' - Reload known faces")

def main():
    """Main function"""
    import sys
    
    # Check command line arguments
    headless_mode = len(sys.argv) > 1 and sys.argv[1].lower() == 'headless'
    
    # Print usage if help requested
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['help', '-h', '--help']:
        print_usage()
        return
    
    # Initialize and start system
    system = FaceRecognitionSystem()
    
    if headless_mode:
        success = system.start_headless()
    else:
        success = system.start_recognition()
    
    if success:
        print("✅ Face recognition system ended successfully")
    else:
        print("❌ Face recognition system ended with errors")

if __name__ == "__main__":
    main()