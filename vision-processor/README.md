# Vision Processor - Reka AI

2-Stage Pipeline: Image → Text → JSON + Vectors for AR glasses memory system.

## Architecture

```
📸 Image (from AR glasses)
    ↓
🤖 Stage 1: Reka Vision API
    ↓ Generates:
    • Rich natural language text description
    • Detailed object descriptions with context
    ↓
📝 Stage 2: Reka Text Processing
    ↓ Extracts from text:
    • Scene summary (condensed)
    • Objects (structured keywords)
    • Attributes (color, position, confidence)
    ↓
💾 Vector Store (ChromaDB)
    ↓ Stores as:
    • Text embeddings (R^384)
    • Per-object vectors
    • Searchable memory
```

### Why 2-Stage Pipeline?

- **Stage 1 (Image→Text)**: Rich descriptive text captures more nuance
- **Stage 2 (Text→JSON)**: Structured extraction for precise object tracking
- **Better recall**: Text summaries provide context that pure object detection misses

## Setup

### 1. Install dependencies

```bash
cd vision-processor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Note:** If you get "No space left on device" error when installing opencv-python, free up disk space first or install on another machine.

### 2. Set API key in .env file

Create a `.env` file with your Reka API key (get from Reka dashboard)

### 3. Start vector store

```bash
cd ../vector-store
source venv/bin/activate
python app.py
```

Runs on http://localhost:8001

## Usage

### Test vision only (2-stage pipeline)

```bash
python vision_reka.py path/to/image.jpg
```

Output:
```
📸 Stage 1: Converting image to text summary...
✓ Text summary generated (234 chars)
📝 Stage 2: Extracting structured data from text...
✓ Extracted 3 objects

📄 Text Summary:
------------------------------------------------------------
The image shows an office desk with a silver laptop in the
center, a red coffee mug on the left side, and a black phone
on the right side of the desk.
------------------------------------------------------------

📝 Scene: Office desk with laptop and coffee mug

🎯 Keywords/Objects (3):
   • laptop (color: silver, at: center) [95%]
   • mug (color: red, at: left side) [92%]
   • phone (color: black, at: right) [88%]
```

### Full pipeline (2-stage vision + storage)

```bash
python integration_reka.py path/to/image.jpg
```

Output:
```
IMAGE → TEXT → JSON → VECTOR STORE PIPELINE

📸 Processing: path/to/image.jpg
🤖 Analyzing with Reka (2-stage)...
📸 Stage 1: Converting image to text summary...
✓ Text summary generated (234 chars)
📝 Stage 2: Extracting structured data from text...
✓ Extracted 3 objects
💾 Storing in vector database...
✓ Stored: user_123:session_123:1761378900
✓ Objects: 3
✓ Tracked: ['user_123:mug@home', 'user_123:phone@home']

✅ COMPLETE PIPELINE SUCCESS!
```

## What Gets Stored

For each image:

1. **Scene embedding** - Text vector in R^384
2. **Object embeddings** - Per-object vectors
3. **Metadata** - Color, position, confidence
4. **Last-seen tracking** - For "Where is my X?" queries

Example stored data:
```json
{
  "frame_id": "user_123:session_001:1761378900",
  "scene_summary": "Office desk with laptop and mug",
  "objects": [
    {
      "label": "laptop",
      "confidence": 0.95,
      "color": "silver",
      "rel_pos": "center"
    }
  ]
}
```

## Integration with AR Glasses

### Automatic Capture (30-second intervals + triggers)

```python
from capture_scheduler import CaptureScheduler

def capture_from_glasses() -> str:
    """Your camera capture function"""
    image_bytes = glasses_camera.capture_frame()
    path = f"/tmp/capture_{int(time.time())}.jpg"
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path

# Create and start scheduler
scheduler = CaptureScheduler(
    capture_func=capture_from_glasses,
    interval=30,  # Every 30 seconds
    min_trigger_gap=3  # Debounce triggers
)
scheduler.start()

# Trigger on demand (user button, motion, etc.)
scheduler.trigger_capture(reason="user_button")
```

### Manual Single Capture

```python
from integration_reka import process_image_to_memory

# Process single image
def on_frame_capture(image_bytes):
    # Save image temporarily
    with open("/tmp/frame.jpg", "wb") as f:
        f.write(image_bytes)
    
    # Process through pipeline
    result = process_image_to_memory("/tmp/frame.jpg")
    
    if result["ok"]:
        print(f"Stored: {result['stored']['frame_id']}")
```

## Query Examples

After storing images, query the vector store:

```bash
# "Where are my keys?"
curl -X POST http://localhost:8001/search_last_seen \
  -d '{"tenant_id":"user_123","canonical_key":"keys@home"}'

# Semantic search: "When did I see the red mug?"
curl -X POST http://localhost:8001/search_semantic \
  -d '{"tenant_id":"user_123","query_text":"red mug","n_results":5}'
```

## Live Camera Stream

**NEW:** The system now captures **live camera feed** instead of static test images!

### Test Camera Stream

```bash
python camera_stream.py
```

Commands:
- `c` - Capture frame from camera
- `i` - Show camera info  
- `q` - Quit

Each capture is saved to `/tmp/captures/capture_<timestamp>.jpg`

### Camera Configuration

Edit `.env` file:
```bash
CAMERA_ID=0                    # 0 = default webcam, 1 = external camera
CAPTURE_SAVE_DIR=/tmp/captures # Where to save frames
```

See `CAMERA_SETUP.md` for detailed camera configuration and troubleshooting.

## Capture Scheduler

The `capture_scheduler.py` module provides smart timing control:

### Features

- ⏰ **Automatic capture** every 30 seconds (configurable)
- 🎯 **Trigger-based capture** for important moments
- 🛡️ **Debouncing** prevents rapid-fire captures (3s minimum gap)
- 🧵 **Thread-safe** for concurrent triggers
- 📊 **Statistics tracking** for monitoring

### Configuration

Edit `.env` file:
```bash
CAPTURE_INTERVAL_SECONDS=30   # Automatic interval
MIN_TRIGGER_GAP_SECONDS=3     # Minimum time between captures
```

### Test the Scheduler

```bash
# Live mode (captures from camera)
python capture_scheduler.py

# Test mode (uses static test image)
python capture_scheduler.py --test
```

Commands:
- `t` - Trigger manual capture (gets LIVE frame from camera)
- `s` - Show statistics
- `q` - Quit

**Each trigger now captures whatever is in front of the camera at that moment!**

## Files

- `vision_reka.py` - Reka vision API integration
- `integration_reka.py` - Complete pipeline (vision + storage)
- `capture_scheduler.py` - Smart capture timing (30s + triggers)
- `camera_stream.py` - **NEW:** Live camera capture (OpenCV-based)
- `requirements.txt` - Python dependencies
- `CAMERA_SETUP.md` - **NEW:** Camera setup and troubleshooting guide

## API

### `image_to_text_summary(image_path: str) -> str`

Stage 1: Converts image to natural language text description.

**Returns:** Rich text description of scene and objects.

### `text_summary_to_json(text_summary: str) -> dict`

Stage 2: Extracts structured data from text summary.

**Returns:**
```python
{
    "scene_summary": str,
    "objects": [
        {
            "label": str,
            "confidence": float,
            "color": str | None,
            "rel_pos": str | None
        }
    ]
}
```

### `analyze_image(image_path: str) -> dict`

Complete 2-stage pipeline: image → text → JSON.

**Returns:**
```python
{
    "scene_summary": str,
    "text_summary": str,  # The intermediate text description
    "objects": [
        {
            "label": str,
            "confidence": float,
            "color": str | None,
            "rel_pos": str | None
        }
    ]
}
```

### `process_image_to_memory(image_path: str) -> dict`

Full pipeline: analyze + store in vector database.

**Returns:**
```python
{
    "ok": bool,
    "vision": {...},      # Vision analysis result
    "stored": {...}       # Vector store confirmation
}
```

## Status

✅ **Reka Vision** - Working  
✅ **Vector Store** - Production-ready  
✅ **Pipeline** - Functional  
✅ **Ready for** - AR glasses integration

## Next Steps

1. ✅ Test with your images
2. ⏳ Integrate with AR glasses camera
3. ⏳ Build session review UI
4. ⏳ Deploy to production