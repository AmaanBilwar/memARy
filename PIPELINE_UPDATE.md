# Pipeline Update: 2-Stage Vision Processing

## Overview

The vision processing pipeline has been updated from **direct image-to-JSON** to a **2-stage pipeline** that produces better results for memory recall.

## What Changed

### Before (Single-Stage)
```
📸 Image → 🤖 Reka Vision → 📊 JSON (objects + scene)
```

### After (2-Stage)
```
📸 Image → 🤖 Stage 1: Text Summary → 📝 Stage 2: JSON Extraction → 💾 Storage
```

## Why This Approach?

1. **Better Context**: Natural language descriptions capture nuances that pure object detection misses
2. **More Accurate**: Text-based extraction can reason about relationships and spatial context
3. **Flexible**: Can process the text summary separately or use it for additional features
4. **Debugging**: Easier to understand what the AI "sees" via human-readable text

## Implementation Details

### Stage 1: Image → Text Summary

**Function**: `image_to_text_summary(image_path: str) -> str`

- Takes an image file path
- Sends to Reka Vision API with a natural language description prompt
- Returns rich text description of the scene and all visible objects
- Includes colors, positions, and spatial relationships

Example output:
```
"The image shows an office desk with a silver laptop in the 
center, a red coffee mug on the left side, and a black phone 
on the right side of the desk."
```

### Stage 2: Text Summary → JSON

**Function**: `text_summary_to_json(text_summary: str) -> dict`

- Takes the text description from Stage 1
- Sends to Reka API with structured extraction prompt
- Parses text to extract objects with attributes
- Returns standardized JSON format

Example output:
```json
{
  "scene_summary": "Office desk with laptop and coffee mug",
  "text_summary": "The image shows an office desk...",
  "objects": [
    {
      "label": "laptop",
      "confidence": 0.95,
      "color": "silver",
      "rel_pos": "center",
      "bbox": null,
      "is_person": false
    },
    {
      "label": "mug",
      "confidence": 0.92,
      "color": "red",
      "rel_pos": "left side",
      "bbox": null,
      "is_person": false
    }
  ]
}
```

### Complete Pipeline

**Function**: `analyze_image(image_path: str) -> dict`

- Orchestrates both stages
- Returns combined result with both text summary and structured JSON
- Adds debug output showing progress through each stage

## Detection & Fetching Methods

The existing detection and fetching methods remain **unchanged**:

### Search Methods (api-service/main.py)
- ✅ `/search` - Semantic search with natural language answers
- ✅ `/find/{object_name}` - Find where object was last seen
- ✅ In-memory fallback with keyword matching
- ✅ Temporal filtering and session-based queries

### Vector Store Methods (vector-store/app.py)
- ✅ `/search_semantic` - Vector similarity search
- ✅ `/search_last_seen` - O(1) last-seen queries
- ✅ `/add_frame` - Store frame with embeddings
- ✅ Collections: frames, entities, latest_entities, user_notes

All these methods continue to work with the new pipeline because the **output format remains the same** - only the extraction method changed.

## Files Updated

### Core Implementation
- ✅ `vision-processor/vision_reka.py` - New 2-stage pipeline implementation
- ✅ `vision-processor/integration_reka.py` - Updated comments and descriptions

### Documentation
- ✅ `vision-processor/README.md` - Updated architecture and examples
- ✅ `web-test/README.md` - Documented new pipeline flow

## Testing

### Test Individual Stages

```bash
# Stage 1: Get text summary (new)
cd vision-processor
source venv/bin/activate
python -c "from vision_reka import image_to_text_summary; print(image_to_text_summary('test_images/desk_scene.jpg'))"

# Stage 2: Convert text to JSON (new)
python -c "from vision_reka import text_summary_to_json; print(text_summary_to_json('A desk with a laptop and mug'))"

# Complete pipeline
python vision_reka.py test_images/desk_scene.jpg
```

### Test Full Integration

```bash
# Vision + Vector Store
python integration_reka.py test_images/desk_scene.jpg
```

### Test via Web Interface

```bash
# Start API service
cd api-service
python main.py

# Open web-test/index.html in browser
# Upload an image and see the 2-stage processing
```

## Benefits

1. **Richer Context**: Text summaries capture scene context better than pure object lists
2. **Better Recall**: Natural language helps with semantic search accuracy
3. **Debugging**: Can inspect intermediate text to understand what AI sees
4. **Flexibility**: Can use text summary for other features (captions, descriptions, etc.)
5. **Backward Compatible**: Output format unchanged, existing search methods work as-is

## Performance Notes

- **API Calls**: Now makes 2 Reka API calls instead of 1 (slight latency increase)
- **Accuracy**: Generally better object detection and spatial reasoning
- **Token Usage**: Text summary adds ~100-300 tokens per image
- **Cost**: Approximately 2x API costs (but better quality)

## Migration Guide

No migration needed! The changes are **backward compatible**:

1. API endpoints remain the same
2. Request/response formats unchanged
3. Vector store schema unchanged
4. Existing stored memories work fine
5. Search methods work as before

Simply pull the latest code and restart your services.

## Future Enhancements

Potential improvements to the 2-stage pipeline:

1. **Caching**: Store text summaries for later review
2. **Multi-modal search**: Search by both text and object keywords
3. **Summary refinement**: User can edit/enhance text descriptions
4. **Batch processing**: Process multiple images with shared context
5. **Language models**: Use text summaries for conversation/Q&A

---

**Status**: ✅ Implemented and tested  
**Breaking Changes**: None  
**Migration Required**: No  
**Date**: October 25, 2025


