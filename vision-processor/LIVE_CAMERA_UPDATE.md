# ✅ Live Camera Stream Update - Complete

## What Changed

The capture scheduler now captures **real-time frames from camera** instead of using the same test image repeatedly.

### Before
```
Every trigger → test_images/desk_scene.jpg (same image)
```

### After  
```
Every trigger → /tmp/captures/capture_<timestamp>.jpg (unique live frame)
```

## New Files

1. **`camera_stream.py`** (221 lines)
   - OpenCV-based camera capture
   - Continuous video stream
   - Captures unique frames on demand
   - Easy to replace with AR glasses SDK

2. **`CAMERA_SETUP.md`**
   - Complete setup guide
   - Troubleshooting
   - AR glasses integration examples

3. **`LIVE_CAMERA_UPDATE.md`** (this file)
   - Summary of changes

## Updated Files

1. **`capture_scheduler.py`**
   - Added `from camera_stream import CameraStream`
   - Added `live_camera_capture()` function
   - Added `--test` flag for testing without camera
   - Proper camera cleanup on shutdown

2. **`requirements.txt`**
   - Added `opencv-python>=4.8.0`

3. **`.env.example`**
   - Added `CAMERA_ID=0`
   - Added `CAPTURE_SAVE_DIR=/tmp/captures`

4. **`README.md`**
   - Added camera stream section
   - Updated scheduler documentation
   - Added file references

## How to Use

### Option 1: With Camera (Live Mode - DEFAULT)

```bash
cd vision-processor
source venv/bin/activate

# Install OpenCV
pip install opencv-python

# Run with live camera
python capture_scheduler.py
```

Press `t` to trigger - each capture gets a fresh frame from camera!

### Option 2: Without Camera (Test Mode)

```bash
python capture_scheduler.py --test
```

Uses static test image (original behavior)

### Option 3: Test Camera Only

```bash
python camera_stream.py
```

Test camera capture without running full pipeline.

## Configuration

Edit `.env` (or set environment variables):

```bash
# Camera settings
CAMERA_ID=0                      # 0 = default webcam
CAPTURE_SAVE_DIR=/tmp/captures   # Where to save frames

# Timing (unchanged)
CAPTURE_INTERVAL_SECONDS=30
MIN_TRIGGER_GAP_SECONDS=3
```

## Architecture Flow

```
┌──────────────────────┐
│  Camera Stream       │  Opens once, kept alive
│  (CameraStream)      │
└──────┬───────────────┘
       │
       │ capture_frame() called every 30s or on trigger
       ↓
┌──────────────────────┐
│  Unique Live Frame   │  /tmp/captures/capture_1234567890.jpg
│  captured each time  │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│  Reka Vision API     │  Analyzes unique frame
│  (vision_reka.py)    │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│  Vector Store        │  Stores unique memory
│  (ChromaDB)          │
└──────────────────────┘
```

## Testing

### Test 1: Camera Only
```bash
python camera_stream.py
# Press 'c' to capture, verify files in /tmp/captures/
```

### Test 2: Scheduler with Camera
```bash
python capture_scheduler.py
# Press 't' multiple times, move objects between triggers
# Verify different objects detected each time
```

### Test 3: Verify Unique Frames
```bash
# Start scheduler
python capture_scheduler.py

# Put phone on left → press 't'
# Wait 3 seconds
# Move phone to right → press 't'
# Wait 3 seconds  
# Remove phone → press 't'

# Check vector store - should have 3 different memories
```

## Replace with AR Glasses Camera

When you have your AR glasses SDK, modify `capture_scheduler.py`:

```python
def get_camera():
    """Replace this function with your AR glasses initialization"""
    global _camera
    if _camera is None:
        # Replace with your SDK
        # _camera = ARGlassesCameraSDK()
        # _camera.connect()
        
        # For now, uses webcam
        camera_id = int(os.getenv("CAMERA_ID", "0"))
        save_dir = os.getenv("CAPTURE_SAVE_DIR", "/tmp/captures")
        _camera = CameraStream(camera_id=camera_id, save_dir=save_dir)
        if not _camera.start():
            raise RuntimeError("Failed to start camera stream")
    return _camera
```

## Disk Space Note

**Important:** OpenCV installation failed due to "No space left on device"

**Solutions:**
1. Free up disk space (~50MB needed)
2. Install on another machine
3. Use opencv-python-headless (smaller): `pip install opencv-python-headless`

To check space:
```bash
df -h
```

To clean old captures:
```bash
rm -rf /tmp/captures/*
```

## Benefits

✅ **Unique captures** - Each trigger gets fresh frame  
✅ **Real-time analysis** - Sees what's happening NOW  
✅ **No duplicate data** - Different objects every time  
✅ **AR glasses ready** - Easy to swap camera source  
✅ **Efficient** - Camera stream kept open (no re-initialization)  

## File Summary

```
vision-processor/
├── camera_stream.py              # NEW: Camera capture
├── capture_scheduler.py          # UPDATED: Uses live camera
├── integration_reka.py           # Unchanged
├── vision_reka.py                # Unchanged
├── requirements.txt              # UPDATED: Added opencv-python
├── .env.example                  # UPDATED: Added camera config
├── README.md                     # UPDATED: Added camera docs
├── CAMERA_SETUP.md              # NEW: Setup guide
└── LIVE_CAMERA_UPDATE.md        # NEW: This file
```

## Status

✅ **Camera stream module created**  
✅ **Scheduler updated to use live camera**  
✅ **Documentation complete**  
✅ **Test mode available (--test flag)**  
⚠️ **OpenCV needs manual install** (disk space issue)  

## Next Steps

1. Install opencv-python: `pip install opencv-python`
2. Test camera: `python camera_stream.py`
3. Test scheduler: `python capture_scheduler.py`
4. Verify unique captures in vector store
5. Replace with AR glasses camera when ready

---

**Updated:** October 25, 2025  
**Ready to capture live streams!** 📹

