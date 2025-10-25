# Camera Stream Setup Guide

## Overview

The capture scheduler now uses **live camera stream** instead of static test images. Each trigger captures a real-time frame from your webcam or AR glasses camera.

## Changes Made

### ✅ New Features

1. **Live Camera Stream** (`camera_stream.py`)
   - Captures real-time frames from video source
   - OpenCV-based implementation
   - Easy to replace with AR glasses SDK

2. **Updated Scheduler** (`capture_scheduler.py`)
   - Uses live camera by default
   - Falls back to test image if camera fails
   - Supports both live mode and test mode

3. **New Dependencies**
   - Added `opencv-python>=4.8.0` to requirements.txt

## Quick Start

### 1. Install OpenCV

```bash
cd vision-processor
source venv/bin/activate
pip install opencv-python
```

**Note:** If disk space is limited, you can install on another machine or free up space first.

### 2. Test Camera Stream (Standalone)

```bash
python camera_stream.py
```

Commands:
- `c` - Capture frame
- `i` - Show camera info
- `q` - Quit

This will test your camera and save frames to `/tmp/captures/`

### 3. Run Scheduler with Live Camera

```bash
# Live mode (default) - uses webcam
python capture_scheduler.py

# Test mode - uses static test image
python capture_scheduler.py --test
```

## Configuration

Edit `.env` file:

```bash
# Camera settings
CAMERA_ID=0                      # 0 = default webcam, 1 = second camera, etc.
CAPTURE_SAVE_DIR=/tmp/captures   # Where to save captured frames

# Capture timing
CAPTURE_INTERVAL_SECONDS=30
MIN_TRIGGER_GAP_SECONDS=3

# Vision API
REKA_API_KEY=your-reka-api-key-here

# Vector store
VECTOR_STORE_URL=http://localhost:8001
TENANT_ID=user_123
DEVICE_ID=glasses_01
```

## How It Works

### Camera Stream Flow

```
┌─────────────────────────────────────┐
│  Camera Stream (CameraStream)       │
│  - Opens video device (webcam)      │
│  - Maintains continuous connection  │
│  - Captures frames on demand        │
└──────────────┬──────────────────────┘
               │
               │ capture_frame()
               ↓
┌─────────────────────────────────────┐
│  Capture Scheduler                   │
│  - Every 30s: capture_frame()       │
│  - On trigger: capture_frame()      │
└──────────────┬──────────────────────┘
               │
               ↓
         /tmp/captures/
      capture_1234567890.jpg
               │
               ↓
┌─────────────────────────────────────┐
│  Vision Pipeline (Reka AI)          │
│  - Analyze unique frame             │
│  - Extract objects                  │
│  - Store in vector DB               │
└─────────────────────────────────────┘
```

### Before vs After

**Before (static test):**
```python
def dummy_camera_capture():
    return "test_images/desk_scene.jpg"  # Same image every time
```

**After (live stream):**
```python
def live_camera_capture():
    camera = get_camera()
    return camera.capture_frame()  # Fresh frame each time
```

## Usage Examples

### Example 1: Automatic Capture (30s intervals)

```python
from capture_scheduler import CaptureScheduler, live_camera_capture

scheduler = CaptureScheduler(
    capture_func=live_camera_capture,
    interval=30
)
scheduler.start()

# Captures live frame every 30 seconds automatically
# Each capture is unique!
```

### Example 2: Manual Triggers

```python
from capture_scheduler import CaptureScheduler, live_camera_capture

scheduler = CaptureScheduler(
    capture_func=live_camera_capture,
    interval=30
)
scheduler.start()

# User presses button → capture live frame
scheduler.trigger_capture(reason="user_button")

# Motion detected → capture live frame
scheduler.trigger_capture(reason="motion_detected")

# Each trigger captures whatever is in front of camera RIGHT NOW
```

### Example 3: Replace with AR Glasses Camera

When you have your AR glasses SDK:

```python
# In capture_scheduler.py, replace get_camera():

def get_camera():
    """Initialize AR glasses camera"""
    global _camera
    if _camera is None:
        # Your AR glasses SDK here
        _camera = ARGlassesCameraSDK()
        _camera.initialize()
    return _camera

def live_camera_capture() -> str:
    """Capture from AR glasses"""
    try:
        camera = get_camera()
        
        # Get frame from AR glasses
        frame_data = camera.capture_current_view()
        
        # Save to file
        timestamp = int(time.time() * 1000)
        filepath = f"/tmp/captures/ar_capture_{timestamp}.jpg"
        
        with open(filepath, "wb") as f:
            f.write(frame_data)
        
        return filepath
        
    except Exception as e:
        print(f"AR glasses error: {e}")
        return None
```

## Camera IDs

| CAMERA_ID | Device |
|-----------|--------|
| 0 | Default webcam (built-in laptop camera) |
| 1 | Second camera (external USB webcam) |
| 2 | Third camera |
| ... | Additional cameras |

**Finding your camera:**
```bash
# Test different IDs
CAMERA_ID=0 python camera_stream.py  # Try ID 0
CAMERA_ID=1 python camera_stream.py  # Try ID 1
CAMERA_ID=2 python camera_stream.py  # Try ID 2
```

## Testing

### Test 1: Camera Stream Only

```bash
python camera_stream.py
```

Expected output:
```
============================================================
CAMERA STREAM CAPTURE TEST
============================================================
✓ Camera 0 opened successfully

📷 Camera Info:
   Resolution: 1280x720
   FPS: 30
   Save directory: /tmp/captures

🎬 Camera is live! Commands:
   'c' - Capture frame
   'i' - Show camera info
   'q' - Quit
```

### Test 2: Scheduler with Live Camera

```bash
python capture_scheduler.py
```

Expected output:
```
============================================================
CAPTURE SCHEDULER - 30s Intervals + Triggers
============================================================

📷 LIVE MODE: Using camera stream
✓ Camera stream initialized: {...}
✓ Capture scheduler started (interval: 30s)
🔄 Starting automatic capture every 30s

Scheduler running. Commands:
  't' - Trigger manual capture
  's' - Show statistics
  'q' - Quit
```

Press `t` to trigger captures - each one will be a fresh frame!

### Test 3: Verify Different Frames

```bash
# Start scheduler
python capture_scheduler.py

# Trigger 3 times with different objects in view
# Move objects between triggers
> t  # Capture with object on left
> t  # Capture with object on right
> t  # Capture with object in center

# Check that each capture analyzed different scenes
```

## Troubleshooting

### Problem: "Failed to open camera"

**Solutions:**
1. Check if camera is connected: `ls /dev/video*`
2. Close other apps using camera (Zoom, Skype, etc.)
3. Try different CAMERA_ID: `CAMERA_ID=1 python camera_stream.py`
4. Check camera permissions (System Preferences → Security & Privacy → Camera)

### Problem: "No space left on device"

**Solutions:**
1. Free up disk space
2. Change save directory: `CAPTURE_SAVE_DIR=/path/with/space`
3. Clean old captures: `rm -rf /tmp/captures/*`

### Problem: Camera lag or freeze

**Solutions:**
1. Reduce resolution in `camera_stream.py`:
   ```python
   self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Lower resolution
   self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
   ```
2. Increase interval: `CAPTURE_INTERVAL_SECONDS=60`

### Problem: OpenCV not installed

**Solution:**
```bash
pip install opencv-python
```

If still failing, try:
```bash
pip install opencv-python-headless  # Minimal version without GUI
```

## Architecture

### File Structure

```
vision-processor/
├── camera_stream.py         # NEW: Camera capture module
├── capture_scheduler.py     # UPDATED: Now uses live camera
├── integration_reka.py      # Vision pipeline (unchanged)
├── vision_reka.py          # Reka API (unchanged)
├── requirements.txt        # UPDATED: Added opencv-python
└── .env.example           # UPDATED: Added camera config
```

### Camera Class (CameraStream)

**Methods:**
- `start()` - Open camera stream
- `stop()` - Close camera and release resources
- `capture_frame()` - Capture and save current frame
- `get_info()` - Get camera properties

### Scheduler Integration

The scheduler now:
1. Initializes camera once (lazy loading)
2. Reuses same camera stream for all captures
3. Each capture gets fresh frame from live stream
4. Properly cleans up camera on shutdown

## Performance

**Memory:** Camera stream kept open (efficient for repeated captures)  
**Latency:** ~50-100ms per capture (camera → save → process)  
**Storage:** Each frame ~300KB (JPEG quality 90)  

## Next Steps

1. ✅ Test camera stream standalone
2. ✅ Test scheduler with live mode
3. ⏳ Replace with AR glasses camera SDK
4. ⏳ Add motion detection triggers
5. ⏳ Add voice command triggers

---

**Status:** ✅ Live camera capture implemented  
**Updated:** October 25, 2025

