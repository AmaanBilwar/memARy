# Capture Scheduler Guide

## Overview

The capture scheduler implements **30-second automatic intervals + trigger-based capture** for optimal storage savings while maintaining responsiveness.

## Key Features

✅ **Automatic Capture** - Every 30 seconds (6x less than 5s)  
✅ **Manual Triggers** - User button, motion detection, voice commands  
✅ **Debouncing** - Prevents accidental rapid captures (3s minimum gap)  
✅ **Thread-safe** - Can be triggered from multiple sources  
✅ **Configurable** - Change intervals without code changes  

## Storage Savings

| Interval | Captures/Day | Monthly Storage |
|----------|--------------|-----------------|
| 5 seconds | 17,280 | ~52 GB |
| **30 seconds** | **2,880** | **~8.6 GB** |
| **Savings** | **6x less** | **83% reduction** |

## Quick Start

### 1. Test the Scheduler

```bash
cd vision-processor
source venv/bin/activate
python capture_scheduler.py
```

**Interactive commands:**
- `t` - Trigger manual capture
- `s` - Show statistics  
- `q` - Quit

### 2. Configuration

Edit `.env` file (optional, uses defaults if not set):

```bash
CAPTURE_INTERVAL_SECONDS=30   # Change to 60 for 1-minute intervals
MIN_TRIGGER_GAP_SECONDS=3     # Change to 5 for 5-second debounce
```

### 3. Integration Example

```python
from capture_scheduler import CaptureScheduler

# Define your camera capture function
def capture_from_glasses() -> str:
    """Capture image and return path"""
    image_bytes = camera.capture()
    path = f"/tmp/capture_{int(time.time())}.jpg"
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path

# Create scheduler
scheduler = CaptureScheduler(
    capture_func=capture_from_glasses,
    interval=30,  # seconds
    min_trigger_gap=3  # seconds
)

# Start automatic captures
scheduler.start()

# Manually trigger when needed
scheduler.trigger_capture(reason="user_button")
scheduler.trigger_capture(reason="motion_detected")
scheduler.trigger_capture(reason="voice_command")

# Get statistics
stats = scheduler.get_stats()
print(f"Captures: {stats['capture_count']}")

# Stop when done
scheduler.stop()
```

## Trigger Events

The scheduler supports any trigger reason you define:

### Built-in Trigger Examples

```python
# User presses button on glasses
scheduler.trigger_capture(reason="user_button")

# Motion detection threshold exceeded
if motion_magnitude > THRESHOLD:
    scheduler.trigger_capture(reason="motion_detected")

# Voice command recognized
if voice_command == "remember this":
    scheduler.trigger_capture(reason="voice_command")

# Important object detected
if "keys" in detected_objects:
    scheduler.trigger_capture(reason="object_detected:keys")

# Location changed to important place
if location in IMPORTANT_PLACES:
    scheduler.trigger_capture(reason=f"location:{location}")
```

## How It Works

### Automatic Capture Loop

1. Background thread sleeps for configured interval (30s)
2. Wakes up and acquires lock
3. Executes capture: calls your camera function
4. Processes image through Reka vision pipeline
5. Stores in vector database
6. Updates timestamp and counter
7. Repeats

### Manual Trigger Flow

1. Trigger function called with reason
2. Acquires lock (thread-safe)
3. Checks time since last capture
4. If < 3 seconds → debounced, returns "wait"
5. If ≥ 3 seconds → executes capture
6. Returns result with capture number

## Architecture

```
CaptureScheduler
├── Background Thread (automatic 30s loop)
│   └── _execute_capture() → integration_reka.py → vector store
│
└── trigger_capture() (manual triggers)
    └── _execute_capture() → integration_reka.py → vector store
```

## API Reference

### `CaptureScheduler(capture_func, interval=30, min_trigger_gap=3)`

**Parameters:**
- `capture_func: Callable` - Function that captures image and returns path
- `interval: int` - Seconds between automatic captures (default: 30)
- `min_trigger_gap: int` - Minimum seconds between triggers (default: 3)

### Methods

**`start()`** - Start automatic capture loop

**`stop()`** - Stop capture loop (blocks until thread exits)

**`trigger_capture(reason: str) -> dict`** - Manually trigger a capture

Returns:
```python
{
    "ok": True,
    "reason": "user_button",
    "capture_number": 42,
    "result": {...}
}
# or if debounced:
{
    "ok": False,
    "reason": "debounced",
    "wait_seconds": 1.5
}
```

**`get_stats() -> dict`** - Get capture statistics

Returns:
```python
{
    "running": True,
    "session_id": "session_1761381234",
    "capture_count": 120,
    "last_capture_ago": 5.3,  # seconds
    "interval_seconds": 30
}
```

## Testing

The default test mode uses a dummy camera that returns the test image:

```bash
python capture_scheduler.py
```

This will:
- Capture every 30 seconds automatically
- Allow manual triggers with `t` command
- Show stats with `s` command
- Process through full Reka → vector store pipeline

## Production Deployment

Replace `dummy_camera_capture()` with your actual camera:

```python
def capture_from_ar_glasses() -> str:
    """Real camera capture implementation"""
    # Your AR glasses SDK here
    frame = glasses_sdk.capture_frame()
    
    # Save to temporary file
    timestamp = int(time.time())
    path = f"/tmp/ar_capture_{timestamp}.jpg"
    
    with open(path, "wb") as f:
        f.write(frame)
    
    return path

# Use in production
scheduler = CaptureScheduler(
    capture_func=capture_from_ar_glasses,
    interval=30
)
scheduler.start()
```

## Environment Variables

All configuration can be set via `.env`:

```bash
# Capture timing
CAPTURE_INTERVAL_SECONDS=30
MIN_TRIGGER_GAP_SECONDS=3

# Vision API
REKA_API_KEY=your-actual-api-key

# Vector store
VECTOR_STORE_URL=http://localhost:8001
TENANT_ID=user_123
DEVICE_ID=glasses_01
```

## Files

- `capture_scheduler.py` - Main scheduler implementation
- `.env` - Configuration (not in git)
- `.env.example` - Configuration template
- `README.md` - General documentation

## Troubleshooting

**Problem:** Captures not happening

**Solution:** Check that vector store is running on port 8001:
```bash
curl http://localhost:8001/healthz
```

**Problem:** "Debounced" errors on triggers

**Solution:** This is expected behavior. Wait 3 seconds between triggers or adjust `MIN_TRIGGER_GAP_SECONDS`

**Problem:** Capture function failing

**Solution:** Ensure your camera function returns a valid file path and the file exists

## Next Steps

1. ✅ Test scheduler with dummy camera
2. ⏳ Replace with real AR glasses camera
3. ⏳ Define your specific trigger events
4. ⏳ Deploy to production hardware

---

**Created:** October 25, 2025  
**Status:** ✅ Implemented and ready for testing

