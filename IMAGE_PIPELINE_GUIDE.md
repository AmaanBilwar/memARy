# Image Upload Pipeline Guide

## Overview

The image upload pipeline allows you to upload pictures, which are then:
1. Analyzed by Reka AI to generate a text summary
2. Extracted into structured JSON with objects, colors, and positions
3. Stored in ChromaDB as vector embeddings
4. Made searchable through semantic queries

This is the same pipeline as the text → JSON process, but starting from an image.

## Architecture

```
Image Upload → Reka Vision API → Text Summary → JSON Extraction → ChromaDB Storage
     ↓              ↓                 ↓              ↓                ↓
  Base64        Natural Lang     Structured     Vector DB      Searchable
  Encoding      Description        JSON        Embeddings       Memory
```

## Quick Start

### 1. Start All Services

```bash
# Terminal 1: Start Vector Store (port 8001)
cd vector-store
python app.py

# Terminal 2: Start API Service (port 8000)
cd api-service
python main.py

# Terminal 3: Serve Web Interface (port 8080)
cd web-test
python3 -m http.server 8080
```

### 2. Set Up Environment Variables

Make sure you have a `.env` file with your Reka API key:

```bash
# In the project root or vision-processor directory
REKA_API_KEY=your_reka_api_key_here
```

### 3. Open the Web Interface

Open your browser and go to: **http://localhost:8080**

### 4. Upload an Image

1. Click on the **📸 Image Upload** tab (first tab)
2. Click the upload area or drag-and-drop an image
3. Click **"🔄 Analyze & Store"**
4. Wait for Reka to analyze (takes 5-15 seconds)
5. View the results!

## API Endpoints

### POST `/store` - Upload and Analyze Image

**Request:**
```json
{
  "image_base64": "base64_encoded_image_data",
  "session_id": "test-session"
}
```

**Response:**
```json
{
  "ok": true,
  "analysis": {
    "scene": "A desk with laptop and coffee mug",
    "objects": [
      {
        "label": "laptop",
        "confidence": 0.95,
        "color": "silver",
        "rel_pos": "center of desk",
        "bbox": null,
        "is_person": false
      }
    ],
    "text_summary": "The image shows an office desk..."
  },
  "storage": {
    "mode": "vector_store",
    "frame_id": "user_123:test-session:1234567890"
  }
}
```

### POST `/store_text` - Text Summary to JSON

**Request:**
```json
{
  "text_summary": "I see a red coffee mug on the left side of my desk",
  "session_id": "test-session"
}
```

## How It Works

### Stage 1: Image → Text Summary (Reka Vision)

The `vision_reka.py` module uses Reka's vision API to convert images to natural language:

```python
from vision_reka import analyze_image

result = analyze_image("path/to/image.jpg")
# Returns: {
#   "scene_summary": "...",
#   "objects": [...],
#   "text_summary": "..."
# }
```

**Prompt used:**
- Describe the overall scene and setting
- List ALL visible objects with colors and positions
- Focus on common items (keys, wallet, phone, etc.)
- Be specific about spatial relationships

### Stage 2: Text → JSON Extraction (Reka Core)

The text summary is then parsed into structured JSON:

```python
from vision_reka import text_summary_to_json

json_result = text_summary_to_json(text_description)
# Returns: {
#   "scene_summary": "Brief description",
#   "objects": [
#     {"label": "keys", "color": "silver", "rel_pos": "on table", "confidence": 0.9}
#   ]
# }
```

### Stage 3: Vector Storage (ChromaDB)

The structured data is stored in ChromaDB across 3 collections:

1. **frames_ephemeral_v1** - Full scene summaries (TTL: 24-72h)
2. **entities_stream_v1** - Individual object mentions
3. **latest_entities_v1** - Latest location of tracked objects

## File Structure

```
memary/
├── api-service/
│   └── main.py                 # FastAPI service with /store endpoint
├── vision-processor/
│   └── vision_reka.py          # Reka AI integration
├── vector-store/
│   ├── app.py                  # ChromaDB service
│   ├── embeddings.py           # Text embedding functions
│   └── schema.py               # Data models
└── web-test/
    └── index.html              # Web UI with image upload
```

## Features in the Web UI

### 📸 Image Upload Tab
- Drag-and-drop or click to upload
- Image preview
- Real-time analysis with Reka
- Shows extracted objects with colors and positions

### 📝 Text to JSON Tab
- Direct text input (without image)
- Converts descriptions to structured data
- Same storage pipeline as images

### 🔍 Search Memories
- Natural language queries: "Where are my keys?"
- Semantic search across all stored memories
- Returns contextual answers

### 📅 Timeline
- Visual timeline of all memories
- Grouped by time (today, yesterday, last week)
- Click to expand details

### 📊 Statistics
- Memory counts and object frequency
- Timeline charts
- Session statistics

### 📌 Tracked Items
- Track important items (keys, wallet, medication)
- Get alerts when items haven't been seen
- View object relationships (items seen together)

### 🎴 Flashcards
- Memory recall training
- Interactive Q&A about stored memories
- Shuffle and review

## Troubleshooting

### "No module named 'vision_reka'" Error

**Solution:** The import path has been fixed. Restart the API service:
```bash
cd api-service
pkill -f "python main.py"
python main.py
```

### Reka API Rate Limits

Reka has rate limits on their API. If you hit limits:
- Wait a few seconds between uploads
- Check your Reka dashboard for quota
- Consider caching results for testing

### Vector Store Connection Failed

If storage shows "in_memory_only" mode:
- Check vector store is running on port 8001
- Verify ChromaDB is installed: `pip install chromadb`
- Check logs in vector store terminal

### Image Too Large

- Max recommended size: 5MB
- Reka supports common formats: JPG, PNG, GIF
- Consider resizing large images before upload

## Next Steps

1. **Add More Images**: Build up your memory database
2. **Search Queries**: Try asking "Where is my [object]?"
3. **Track Items**: Use the tracked items feature for important objects
4. **Review Timeline**: See all your memories organized by time
5. **Export Data**: Consider adding export functionality for backup

## API Testing with curl

```bash
# Upload an image
curl -X POST http://localhost:8000/store \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'$(base64 -i test_image.jpg)'",
    "session_id": "test"
  }'

# Search memories
curl "http://localhost:8000/search?query=keys"

# Get all memories
curl "http://localhost:8000/memories"
```

## Performance Notes

- **Image Analysis**: 5-15 seconds (Reka API call)
- **Text to JSON**: 3-8 seconds (Reka API call)
- **Vector Storage**: < 100ms (local ChromaDB)
- **Search**: < 200ms (vector similarity search)

## Privacy & Data

- Images are NOT stored permanently (only temp files)
- Text summaries and objects are stored in ChromaDB
- No biometric data for people (privacy safeguard)
- Local ChromaDB instance (your data stays local)
- Can configure ChromaDB Cloud for remote storage

---

**Ready to test?** Upload your first image and watch the pipeline in action! 🚀

