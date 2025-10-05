# encodegenerator.py
# Face Recognition Home Security System - Encoding Generator
# Processes known family member photos and generates face encodings for recognition

import cv2
import face_recognition
import numpy as np
import os
import sqlite3
from pathlib import Path
import pickle
from database_setup import (
    create_connection, 
    add_family_member, 
    add_face_encoding, 
    get_all_family_encodings
)

# Configuration
KNOWN_FACES_DIR = "known"
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']

class FaceEncodingGenerator:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.processed_count = 0
        self.failed_count = 0
        
    def load_and_encode_faces(self):
        """Load all images from known faces directory and generate encodings"""
        
        print("🚀 Starting Face Encoding Generation...")
        print("=" * 50)
        
        # Check if known directory exists
        if not os.path.exists(KNOWN_FACES_DIR):
            print(f"❌ Directory '{KNOWN_FACES_DIR}' not found!")
            print("📝 Please create the 'known' directory and add family member photos.")
            return False
        
        # Get all image files
        image_files = self._get_image_files()
        
        if not image_files:
            print(f"❌ No supported image files found in '{KNOWN_FACES_DIR}' directory!")
            print(f"📝 Supported formats: {', '.join(SUPPORTED_FORMATS)}")
            return False
        
        print(f"📁 Found {len(image_files)} image files to process...")
        print()
        
        # Process each image file
        for image_file in image_files:
            self._process_single_image(image_file)
        
        # Save encodings summary
        self._print_summary()
        
        return self.processed_count > 0
    
    def _get_image_files(self):
        """Get all supported image files from known directory"""
        image_files = []
        
        for file_path in Path(KNOWN_FACES_DIR).iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS:
                image_files.append(file_path)
        
        return sorted(image_files)
    
    def _process_single_image(self, image_path):
        """Process a single image and extract face encodings"""
        
        # Extract name from filename (without extension)
        person_name = image_path.stem
        
        print(f"🔍 Processing: {person_name} ({image_path.name})")
        
        try:
            # Load image
            image = cv2.imread(str(image_path))
            
            if image is None:
                print(f"  ❌ Could not load image: {image_path.name}")
                self.failed_count += 1
                return
            
            # Convert BGR to RGB (OpenCV loads as BGR, face_recognition expects RGB)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Find face locations
            face_locations = face_recognition.face_locations(rgb_image)
            
            if len(face_locations) == 0:
                print(f"  ⚠️  No faces detected in: {image_path.name}")
                self.failed_count += 1
                return
            
            if len(face_locations) > 1:
                print(f"  ⚠️  Multiple faces detected in: {image_path.name}, using the largest face")
                # Sort by face area and take the largest
                face_locations = [max(face_locations, key=lambda loc: (loc[2]-loc[0]) * (loc[1]-loc[3]))]
            
            # Generate face encoding
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            if len(face_encodings) == 0:
                print(f"  ❌ Could not generate encoding for: {image_path.name}")
                self.failed_count += 1
                return
            
            # Get the face encoding
            face_encoding = face_encodings[0]
            
            # Store in database
            success = self._store_in_database(person_name, str(image_path), face_encoding)
            
            if success:
                # Store in memory for immediate use
                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(person_name)
                
                print(f"  ✅ Successfully processed: {person_name}")
                self.processed_count += 1
            else:
                print(f"  ❌ Failed to store in database: {person_name}")
                self.failed_count += 1
                
        except Exception as e:
            print(f"  ❌ Error processing {image_path.name}: {str(e)}")
            self.failed_count += 1
    
    def _store_in_database(self, name, image_path, encoding):
        """Store family member and encoding in database"""
        try:
            # Add family member (will return None if already exists)
            family_member_id = add_family_member(name, image_path)
            
            if family_member_id is None:
                # Family member already exists, get their ID
                family_member_id = self._get_family_member_id(name)
                
                if family_member_id is None:
                    return False
            
            # Add face encoding
            success = add_face_encoding(family_member_id, encoding)
            
            return success
            
        except Exception as e:
            print(f"  ❌ Database error: {str(e)}")
            return False
    
    def _get_family_member_id(self, name):
        """Get family member ID by name"""
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM family_members WHERE name = ?', (name,))
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            print(f"Error getting family member ID: {e}")
            return None
    
    def _print_summary(self):
        """Print processing summary"""
        print()
        print("=" * 50)
        print("📊 ENCODING GENERATION SUMMARY")
        print("=" * 50)
        print(f"✅ Successfully processed: {self.processed_count} faces")
        print(f"❌ Failed to process: {self.failed_count} images")
        print(f"👥 Total known faces: {len(self.known_face_names)}")
        
        if self.known_face_names:
            print(f"📝 Recognized names: {', '.join(set(self.known_face_names))}")
        
        print()
        
        if self.processed_count > 0:
            print("🎉 Face encoding generation completed successfully!")
            print("📝 You can now run main.py to start face recognition.")
        else:
            print("⚠️  No face encodings were generated.")
            print("📝 Please check your images in the 'known' directory.")
    
    def save_encodings_backup(self, backup_file="face_encodings_backup.pkl"):
        """Save encodings to backup file (optional)"""
        if not self.known_face_encodings:
            print("⚠️  No encodings to backup.")
            return False
        
        try:
            backup_data = {
                'encodings': self.known_face_encodings,
                'names': self.known_face_names,
                'count': self.processed_count
            }
            
            with open(backup_file, 'wb') as f:
                pickle.dump(backup_data, f)
            
            print(f"💾 Backup saved: {backup_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save backup: {str(e)}")
            return False

def load_encodings_from_database():
    """Load all face encodings from database for use in main.py"""
    try:
        encodings_data = get_all_family_encodings()
        
        known_face_encodings = []
        known_face_names = []
        
        for name, encoding_bytes in encodings_data:
            # Convert bytes back to numpy array
            encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
            
            known_face_encodings.append(encoding)
            known_face_names.append(name)
        
        print(f"📚 Loaded {len(known_face_encodings)} face encodings from database")
        
        return known_face_encodings, known_face_names
        
    except Exception as e:
        print(f"❌ Error loading encodings from database: {str(e)}")
        return [], []

def verify_encodings():
    """Verify that encodings can be loaded correctly"""
    print("🔍 Verifying stored encodings...")
    
    encodings, names = load_encodings_from_database()
    
    if encodings:
        print("✅ Encodings verification successful!")
        print(f"👥 Found encodings for: {', '.join(set(names))}")
        
        # Test encoding shapes
        for i, encoding in enumerate(encodings):
            if encoding.shape != (128,):
                print(f"⚠️  Warning: Invalid encoding shape for {names[i]}: {encoding.shape}")
            else:
                print(f"  ✅ {names[i]}: Valid encoding (128 dimensions)")
    else:
        print("❌ No encodings found or error loading encodings")

def main():
    """Main function to run the encoding generation"""
    print("🏠 Face Recognition Home Security System")
    print("📸 Face Encoding Generator")
    print("=" * 60)
    
    # Initialize encoder
    encoder = FaceEncodingGenerator()
    
    # Process all faces
    success = encoder.load_and_encode_faces()
    
    if success:
        # Create backup (optional)
        encoder.save_encodings_backup()
        
        # Verify encodings
        print()
        verify_encodings()
        
        print()
        print("🚀 Next Steps:")
        print("  1. Run 'python main.py' to start face recognition")
        print("  2. Run 'python app.py' to start web interface")
    
    else:
        print("❌ Encoding generation failed. Please check your setup.")
        print()
        print("📝 Troubleshooting:")
        print("  • Ensure 'known' directory exists")
        print("  • Add clear, front-facing photos of family members")
        print("  • Use supported formats: JPG, PNG, BMP, TIFF")
        print("  • Each photo should contain exactly one face")

if __name__ == "__main__":
    main()