# 🏠 Home Surveillance System

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9C%93-brightgreen.svg)

---

## 🎯 Overview

Transform your smartphone into an **intelligent security camera** that automatically detects and distinguishes between **family members** and **unknown visitors**.  
This system uses **advanced face recognition** to provide real-time monitoring with **video recording**, **voice alerts**, and a **professional web dashboard**.

---

## 🚀 Key Features

### 🔍 Smart Face Recognition
- **Family Recognition**: Automatically identifies registered family members.  
- **Unknown Detection**: Triggers alerts when unfamiliar faces are detected.  
- **Confidence Scoring**: AI-powered accuracy scoring for better reliability.

### 📹 Automated Video Recording
- **24 FPS, 720p Recording**  
- **Auto Trigger**: Starts recording when an unknown person is detected.  
- **Audio Capture**: Includes sound recording.  
- **Continuous Recording**: Continues until the subject leaves the frame.

### 🔔 Real-time Alerts
- **Text-to-Speech**:  
  - “Welcome home, [Name]!” for family members  
  - “Unknown person detected!” for visitors  
- **Visual Indicators**: Instant status updates on the dashboard.

---

## 🌐 Web Dashboard

### 📊 Professional Interface
- **Live Feed**: Real-time camera view.  
- **Activity Log**: Detailed history of detections.  
- **Video Playback**: Watch and manage recordings in-browser.  
- **Advanced Controls**: Play, pause, seek, zoom, and speed control.

### 📱 Multi-Device Access
- **Desktop Access**: Full-feature dashboard.  
- **Mobile Access**: Responsive interface for phones and tablets.  
- **Remote Viewing**: Access dashboard from any device on your local network.

---

## 🔧 Technical Architecture

### Core Components
- **Python 3.7+** – Backend processing  
- **OpenCV** – Computer vision and camera handling  
- **face_recognition** – Deep learning-based facial recognition  
- **Flask** – Web interface and API server  
- **SQLite** – Local database storage  
- **pyttsx3** – Text-to-speech alerts  

### File Structure
```
security_system/
├── main.py                    # Face recognition engine
├── app.py                     # Web dashboard server
├── database_setup.py          # Database initialization
├── encodegenerator.py         # Family face encoding
├── known/                     # Family member photos
├── unknown/                   # Unknown person recordings
│   └── videos/                # Video recordings (24 FPS, 720p)
├── static/                    # Web assets (CSS, JS)
├── templates/                 # HTML templates
└── README.md                  # Documentation
```

---

## 🛠️ Setup Guide

### 1. Install Dependencies
```bash
pip install opencv-python face-recognition flask pyttsx3 numpy
```

### 2. Initial Setup
```bash
# Create database and directories
python database_setup.py

# Add family photos to 'known/' folder
# (e.g., dad.jpg, mom.jpg, child.jpg)

# Generate encodings
python encodegenerator.py
```

### 3. Phone Camera Setup
1. Install **IP Webcam** on your Android phone.  
2. Tap **"Start Server"** in the app.  
3. Note your IP (e.g., `http://192.168.1.100:8080`).  
4. Position your phone at your home entrance.

### 4. Start the System
```bash
# Terminal 1: Start face recognition
python main.py

# Terminal 2: Start web dashboard
python app.py
```

### 5. Access Dashboard
- **On PC** → `http://localhost:5000`  
- **On Phone** → `http://[PC_IP_ADDRESS]:5000`

---

## 🎮 Usage

### For Family Members
- Walk into the camera view.  
- System greets: “Welcome home, [Your Name]!”  
- Event logged; no video recorded.

### For Unknown Persons
- System detects unfamiliar face.  
- Alerts: “Unknown person detected!”  
- Automatically records 720p video with timestamp.  
- Logs event in database.

---

## 🖥️ Web Dashboard Features

| Feature | Description |
|----------|-------------|
| **Live Feed** | Real-time camera streaming |
| **Activity Log** | Full event history with timestamps |
| **Video Playback** | Play, pause, and seek recordings |
| **Search & Filter** | Filter events by date or person |
| **System Status** | Displays performance and connectivity |

---

## ⚙️ Configuration

Edit `main.py` to customize system behavior:
```python
# Camera settings
CAMERA_RESOLUTION = (1280, 720)  # 720p
VIDEO_FPS = 24                   # Frame rate

# Recognition settings
RECOGNITION_TOLERANCE = 0.6      # Match accuracy
COOLDOWN_SECONDS = 10            # Anti-spam delay

# Camera sources (phone first, PC webcam fallback)
CAMERA_SOURCES = [
    "http://192.168.1.100:8080/video",
    0
]
```

---

## 🔒 Privacy & Security

- ✅ **100% Local Processing** – No data leaves your network.  
- 🚫 **No Cloud Storage** – Videos saved locally only.  
- 💡 **On-Device AI** – All recognition runs on your PC.  
- 🔐 **Dashboard Protection** – Can be secured with credentials.

---

## 📊 Performance Tips

- Ensure **strong Wi-Fi** connection between phone and PC.  
- Mount camera **at eye level** for optimal detection.  
- Maintain **good lighting** for better accuracy.  
- Scales well with multiple family members in database.

---

## 🤝 Contributing

Contributions are welcome!  
Submit pull requests or issues for:
- Feature additions  
- Bug fixes  
- UI/UX improvements  
- Documentation updates  

---

## 📄 License

**MIT License** – See [LICENSE](LICENSE) for full details.

---

### 🏠✨ *Your home security, powered by AI and your smartphone.*
