# Vision Processor - Reka AI

Image → Keywords + Vectors pipeline for AR glasses memory system.

## Architecture

```
📸 Image (from AR glasses)
    ↓
🤖 Reka Vision API
    ↓ Extracts:
    • Scene summary (text)
    • Objects (keywords)
    • Attributes (color, position, confidence)
    ↓
💾 Vector Store (ChromaDB)
    ↓ Stores as:
    • Text embeddings (R^384)
    • Per-object vectors
    • Searchable memory
```

## Setup

### 1. Install dependencies

```bash
cd vision-processor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set API key

```bash
export REKA_API_KEY=your-reka-key-here
```

Get your key from Reka (hackathon sponsor!)

### 3. Start vector store

```bash
cd ../vector-store
source venv/bin/activate
python app.py
```

Runs on http://localhost:8001

## Usage

### Test vision only

```bash
python vision_reka.py path/to/image.jpg
```

Output:
```
📝 Scene: Office desk with laptop and coffee mug

🎯 Keywords/Objects (3):
   • laptop (color: silver, at: center) [95%]
   • mug (color: red, at: left side) [92%]
   • phone (color: black, at: right) [88%]
```

### Full pipeline (vision + storage)

```bash
python integration_reka.py path/to/image.jpg
```

Output:
```
📸 Processing: path/to/image.jpg
🤖 Analyzing with Reka...
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

```python
from integration_reka import process_image_to_memory

# Every 5 seconds or on trigger
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

## Files

- `vision_reka.py` - Reka vision API integration
- `integration_reka.py` - Complete pipeline (vision + storage)
- `requirements.txt` - Python dependencies

## API

### `analyze_image(image_path: str) -> dict`

Analyzes image and returns structured data.

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