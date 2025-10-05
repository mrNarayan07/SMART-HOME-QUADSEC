# Phone Camera Setup Guide
# Step-by-step instructions to use your phone camera with the security system

## 📱 **STEP 1: Install IP Webcam App on Phone**

### Android:
1. Go to Google Play Store
2. Search for "IP Webcam" by Pavel Khlebovich
3. Install the app (it's free)

### Alternative: DroidCam
1. Search for "DroidCam" in Play Store
2. Install DroidCam (also works well)

## 📶 **STEP 2: Setup Phone Camera**

### Using IP Webcam (Recommended):
1. **Open IP Webcam app**
2. **Set Resolution**: 
   - Tap "Video Preferences"
   - Set "Video Resolution" to "720p" (1280x720)
   - Set "Quality" to "80%"
3. **Start Server**:
   - Tap "Start Server" at the bottom
   - The app will show an IP address like: `http://192.168.1.100:8080`
   - **WRITE DOWN THIS IP ADDRESS!**

### Using DroidCam:
1. Open DroidCam app
2. Note the IP address shown (e.g., 192.168.1.100)
3. Note the port (usually 4747)

## 🔧 **STEP 3: Update Camera Sources**

1. **Find your phone's IP address from the app**
2. **Edit `main_fixed.py`** and update the CAMERA_SOURCES list:

```python
CAMERA_SOURCES = [
    "http://192.168.29.64:8080/",  # Replace with YOUR phone IP
    "http://192.168.0.100:8080/video",  # Try this if different subnet
    "http://192.168.1.100:4747/video",  # DroidCam format
    0,  # PC webcam (fallback)
]
```

**Replace `192.168.1.100` with YOUR actual phone IP!**

## 🚀 **STEP 4: Run Fixed System**

### 1. First, migrate your database:
```bash
python migrate_database.py
```

### 2. Start face recognition with phone camera:
```bash
python main_fixed.py
```

### 3. Start web interface (in another terminal):
```bash
python app_fixed.py
```

## 📋 **STEP 5: Access Points**

- **📱 Phone Web Dashboard**: Open browser on phone → `http://[YOUR_PC_IP]:5000`
- **💻 PC Dashboard**: Open browser on PC → `http://localhost:5000`
- **🎥 Live Stream**: `http://localhost:5000/live`
- **📷 Manual Capture**: `http://localhost:5000/camera`

## 🔧 **FIXES IMPLEMENTED:**

### ✅ **Phone Camera Priority:**
- Phone cameras are tried FIRST (before PC webcam)
- Multiple IP ranges covered (192.168.1.x, 192.168.0.x, 10.0.0.x)
- Clear connection status messages

### ✅ **Performance Optimization:**
- **FPS Issue Fixed**: Now processes every 2nd frame (recognition)
- **Video FPS**: Reduced to 15 FPS for better performance and smaller files
- **Codec**: Changed to H.264 for better compression
- **Detection Buffer**: Prevents flickering recordings

### ✅ **Video Playback Fixed:**
- **Proper MIME Types**: Videos now serve as `video/mp4`
- **Range Requests**: Browser can seek through videos
- **Error Handling**: Better video serving with debugging

### ✅ **Recording Improvements:**
- **Continuous Recording**: Stops only 2 seconds after person leaves
- **Max Duration**: 30 seconds per recording to prevent huge files
- **Better Detection**: Requires consistent detection to start recording

## 🐛 **TROUBLESHOOTING:**

### Phone Camera Not Connecting:
1. **Check WiFi**: Phone and PC must be on same network
2. **Check IP Address**: Update CAMERA_SOURCES with correct phone IP
3. **Try Different Ports**: 8080, 4747, 8888
4. **Phone App**: Make sure IP Webcam server is running

### Video Not Playing:
1. **Check File**: Ensure video file exists in `unknown/videos/`
2. **Try Different Browser**: Chrome works best for video playback
3. **Check Console**: Press F12 → Console tab for error messages

### Low FPS:
1. **Phone Distance**: Keep phone closer to WiFi router
2. **Close Other Apps**: Close other apps using camera
3. **Lower Quality**: In IP Webcam app, reduce quality to 60%

### Recording Issues:
1. **Storage Space**: Check if you have disk space
2. **Permissions**: Ensure write permissions to `unknown/videos/`
3. **Codec Support**: Install OpenCV with H.264 support

## 📞 **Finding Your Phone's IP:**

### Method 1: From IP Webcam App
- The IP is displayed when you start the server

### Method 2: From Phone Settings
- Android: Settings → WiFi → Connected Network → Advanced → IP Address

### Method 3: From PC (Command Prompt)
```bash
# On Windows
arp -a

# Look for devices on your network
```

## 🎯 **Expected Results After Setup:**

- **Phone camera will be used instead of PC webcam**
- **Higher quality 720p video recordings**  
- **Smooth 15+ FPS performance**
- **Videos play properly in browser with controls**
- **Continuous recording until person leaves frame**
- **Web dashboard accessible from phone**

## 📝 **Usage Flow:**

1. **Phone**: Install IP Webcam → Start Server → Note IP
2. **PC**: Update main_fixed.py → Run migration → Start recognition
3. **Access**: Open web dashboard on phone or PC
4. **Monitor**: View live feed, recordings, and manage logs

The system now properly prioritizes phone camera and provides smooth performance with working video playback!