# OpenCV Installation Guide

## Status

⚠️ **OpenCV installation failed due to disk space** during initial setup.  
The corrupted installation has been cleaned up.

## Installation Steps

### Check Available Disk Space

```bash
df -h
```

You need at least **50-100 MB** free space for opencv-python.

### Free Up Space (if needed)

```bash
# Clean old captures
rm -rf /tmp/captures/*

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Clean pip cache
pip cache purge

# Check space again
df -h
```

### Install OpenCV

Once you have enough space:

```bash
cd /Users/arkanfadhilkautsar/Downloads/remembar/vision-processor
source venv/bin/activate
pip install opencv-python
```

### Alternative: Lightweight Version

If still having disk space issues, use the headless version (smaller):

```bash
pip install opencv-python-headless
```

This version doesn't include GUI components but works fine for camera capture.

### Verify Installation

```bash
python -c "import cv2; print(f'✓ OpenCV {cv2.__version__} installed')"
```

Expected output:
```
✓ OpenCV 4.x.x installed
```

## After Installation

### Test Camera Stream

```bash
python camera_stream.py
```

### Test Capture Scheduler

```bash
# Live mode (with camera)
python capture_scheduler.py

# Test mode (without camera)
python capture_scheduler.py --test
```

## Without OpenCV

If you can't install OpenCV right now, you can still use the system in test mode:

```bash
# Uses static test image (no camera required)
python capture_scheduler.py --test
```

## AR Glasses Integration

When you integrate with AR glasses, you won't need OpenCV at all - replace the camera module with your glasses SDK:

```python
# In capture_scheduler.py
def get_camera():
    """Replace with AR glasses SDK"""
    # return ARGlassesCamera()
    pass
```

## Disk Space Requirements

| Component | Size |
|-----------|------|
| opencv-python | ~90 MB |
| opencv-python-headless | ~40 MB |
| Captured frames (each) | ~300 KB |

## Troubleshooting

### Error: "No space left on device"
**Solution:** Free up disk space (see above)

### Error: "ImportError: dlopen failed"  
**Solution:** Corrupted install, run:
```bash
pip uninstall -y opencv-python
pip install opencv-python
```

### Error: "Camera not found"
**Solution:** Check `CAMERA_ID` in `.env` (try 0, 1, 2)

---

**Status:** Ready to install once disk space is available  
**Alternative:** Use `--test` mode without camera for now

