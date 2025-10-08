# 🏠 Home Survelliance System[![Python](https://img.shields.io/badge/Python-ense](https://img.shields.io/badge/License-MSource](https://img.shields.io/badge/Open%20Source-%E2%9C%93-brightgreen.svg## 🎯 OverviewTransform your smartphone into an intelligent security camera that automatically detects and distinguishes between family members and unknown visitors. This system uses advanced face recognition to provide real-time security monitoring with video recording, voice alerts, and a professional web dashboard.## 🚀 Key Features### 🔍 **Smart Face Recognition**- **Family Recognition**: Automatically identifies registered family members
- **Unknown Detection**: Alerts when unfamiliar faces are detected
- **Confidence Scoring**: AI-powered confidence levels for accurate recognition

### 📹 **Automated Video Recording**- **24 FPS Recording**: High-quality 720p video capture
- **Automatic Trigger**: Records only when unknown persons are detected
- **Audio Support**: Captures audio along with video
- **Continuous Recording**: Records until person leaves the frame

### 🔔 **Real-time Alerts**- **Text-to-Speech**: Voice alerts with personalized greetings
  - "Welcome home, [Name]!" for family members
  - "Unknown person detected!" for visitors
- **Visual Indicators**: Real-time status on dashboard

### 🌐 **Web Dashboard**#### 📊 **Professional Interface**
- **Live Feed**: Real-time camera view
- **Activity Log**: Complete history of all detections
- **Video Playback**: Watch recordings directly in browser
- **Advanced Controls**: Play, pause, seek, zoom, speed control

#### 📱 **Multi-device Access**
- **PC Access**: Full dashboard on desktop
- **Mobile Access**: Responsive design for phones/tablets
- **Remote Viewing**: Access from any device on your network

## 🔧 **Technical Architecture**### **Core Components**- **Python 3.7+**: Backend processing
- **OpenCV**: Computer vision and camera handling
- **face-recognition**: Deep learning face recognition
- **Flask**: Web interface and API server
- **SQLite**: Local database storage
- **pyttsx3**: Text-to-speech engine

### **File Structure**```
security_system/
├── main.py                    # Face recognition engine
├── app.py                     # Web dashboard server
├── database_setup.py          # Database initialization
├── encodegenerator.py         # Family face encoding
├── known/                     # Family member photos
├── unknown/                   # Unknown person recordings
│   └── videos/                # Video recordings (24 FPS, 720p)
├── static/                    # Web assets
│   ├── css/                   # Stylesheets
│   └── js/                    # JavaScript
├── templates/                 # HTML templates
└── README.md                  # This documentation
```

## 🛠️ **Setup Guide**### 1. **Prerequisites**```bash
pip install opencv-python face-recognition flask pyttsx3 numpy
```

### 2. **Initial Setup**```bash
# Create database and directories
python database_setup.py

# Add family photos to 'known/' folder
# (e.g., dad.jpg, mom.jpg, child.jpg)

# Generate face encodings
python encodegenerator.py
```

### 3. **Phone Camera Setup**1. Install **IP Webcam** app on your Android phone
2. Open app and tap **"Start Server"**
3. Note the IP address (e.g., `http://192.168.1.100:8080`)
4. Place phone to monitor your entrance

### 4. **Start the System**```bash
# Terminal 1: Start face recognition
python main.py

# Terminal 2: Start web dashboard  
python app.py
```

### 5. **Access Dashboard**- **On PC**: Open browser → `http://localhost:5000`
- **On Phone**: Open browser → `http://[PC_IP_ADDRESS]:5000`

## 🎮 **Usage**### **For Family Members**- Walk into view of the camera
- System recognizes you and says: "Welcome home, [Your Name]!"
- Entry logged in system (no video recorded)

### **For Unknown Persons**- When visitor approaches:
  - System detects unknown face
  - Says: "Unknown person detected!"
  - Automatically starts 720p video recording
  - Saves video clip with timestamp
  - Logs event in database

### **Web Dashboard Features**| Feature | Description |
|--------|-------------|
| **Live Feed** | Real-time camera view |
| **Activity Log** | Complete history with timestamps |
| **Video Playback** | Watch recordings with full controls |
| **Search & Filter** | Find specific events by date/name |
| **System Status** | Real-time health monitoring |

## ⚙️ **Configuration**Edit `main.py` to customize:
```python
# Camera settings
CAMERA_RESOLUTION = (1280, 720)  # 720p
VIDEO_FPS = 24                   # Recording frame rate

# Recognition settings  
RECOGNITION_TOLERANCE = 0.6      # Accuracy threshold
COOLDOWN_SECONDS = 10            # Anti-spam delay

# Camera sources (phone first, PC as fallback)
CAMERA_SOURCES = [
    "http://192.168.1.100:8080/video",  # Your phone IP
    0                                  # PC webcam fallback
]
```

## 🔒 **Privacy & Security**- **100% Local Processing**: No data leaves your network
- **No Cloud Storage**: All videos stored locally
- **On-device AI**: Face recognition happens on your PC
- **Password Protection**: Web dashboard can be secured

## 📊 **Performance Tips**- **WiFi Quality**: Ensure strong connection between phone and PC
- **Camera Position**: Place phone at eye-level for best recognition
- **Lighting**: Adequate lighting improves accuracy
- **Database Size**: System scales efficiently with more family members

## 🤝 **Contributing**Contributions are welcome! Please open an issue or submit a pull request for:
- New features
- Bug fixes
- Documentation improvements
- UI enhancements

## 📄 **License**MIT License - See [LICENSE](LICENSE) for details.

***

**Your home security, powered by AI and your smartphone.** 🏠✨
