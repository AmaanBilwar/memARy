

# AR Glasses Vector Memory Store

Production-ready FastAPI microservice implementing a 5-tier ChromaDB architecture for AR glasses with devil's-advocate safeguards.

## Architecture Overview

### 5-Tier Memory Model

```
1. frames_ephemeral_v1      → Fast recall, TTL 24-72h (all 5-sec captures)
2. entities_stream_v1       → Per-object mentions across time
3. latest_entities_v1       → Working memory (last-seen objects)
4. user_notes_v1            → Durable user-authored memories
5. long_term_memory_v1      → Curated subset (post-session)
```

### Workflow

```
Every 5 seconds:
  Glasses → Vision → LLM → /add_frame
    ↓
    Stores in:
    - frames_ephemeral_v1 (scene summary)
    - entities_stream_v1 (per object)
    - latest_entities_v1 (if high confidence + whitelisted)

User says "remember this":
  Voice/Text → /add_note → user_notes_v1

Session ends:
  User reviews → selects keepers → /curate_to_ltm → long_term_memory_v1

Nightly:
  Cron → /compact → removes old ephemeral data (TTL)
```

## Devil's-Advocate Safeguards ✅

| Safeguard | Implementation |
|-----------|----------------|
| **TTL & Cost** | Ephemeral data auto-expires after 72h (configurable) |
| **Hallucination Guard** | Only upsert to `latest` if confidence ≥ 0.8 AND object in whitelist |
| **Drift Tracking** | Every row stores `model_scene_ver`, `model_det_ver`, `emb_model_ver` |
| **Privacy** | No biometric data; people = `person_N (relationship_hint)` |
| **Multi-tenant** | Every query filters by `tenant_id` |
| **Migrations** | Collections versioned `*_v1`, `*_v2` for model changes |
| **Meaningful IDs** | Time-sortable: `tenant:session:timestamp` |

## Installation

### 1. Create virtual environment

```bash
cd vector-store
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:
```env
PORT=8001
CHROMA_DIR=./.chroma
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CONFIDENCE_THRESHOLD=0.8
TTL_HOURS=72
```

## Usage

### Start server

```bash
python app.py
```

Server runs on http://localhost:8001  
Docs: http://localhost:8001/docs

### Run tests

```bash
python test_api.py
```

## API Endpoints

### 1. POST `/add_frame` - Ingest frame (every ~5s)

```python
import requests
import time

response = requests.post("http://localhost:8001/add_frame", json={
    "tenant_id": "user_123",
    "device_id": "glasses_01",
    "session_id": "session_001",
    "frame_ts": int(time.time()),
    "tz": "America/Los_Angeles",
    "lat_lon_hash": "9q8yy",  # geohash for privacy
    "scene_summary": "Kitchen table. Red mug left, silver keys near edge.",
    "objects": [
        {
            "label": "mug",
            "confidence": 0.88,
            "bbox": [0.12, 0.34, 0.08, 0.12],
            "color": "red",
            "rel_pos": "left side"
        },
        {
            "label": "keys",
            "confidence": 0.93,
            "bbox": [0.42, 0.61, 0.13, 0.08],
            "color": "silver",
            "rel_pos": "near edge"
        }
    ]
})

print(response.json())
# {"ok": true, "frame_id": "...", "entity_ids": [...], "latest_upserted": [...]}
```

**Stores in 3 places:**
- `frames_ephemeral_v1` - full scene (TTL)
- `entities_stream_v1` - per object
- `latest_entities_v1` - if tracked + high confidence

### 2. POST `/add_note` - User note ("remember this")

```python
response = requests.post("http://localhost:8001/add_note", json={
    "tenant_id": "user_123",
    "text": "Mom's pills are in the left kitchen cabinet.",
    "modality": "voice",  # or "typed"
    "priority": "high",
    "tags": ["medication"],
    "linked_entity": "pills@home"
})

print(response.json())
# {"ok": true, "note_id": "67156a51"}
```

### 3. POST `/search_last_seen` - "Where are my keys?"

```python
response = requests.post("http://localhost:8001/search_last_seen", json={
    "tenant_id": "user_123",
    "canonical_key": "keys@home"
})

print(response.json())
# {
#   "ok": true,
#   "found": true,
#   "document": "keys last seen at 1730150465 near edge",
#   "metadata": {"last_frame_ts": 1730150465, "confidence": 0.93, ...}
# }
```

### 4. POST `/search_semantic` - Semantic search

```python
response = requests.post("http://localhost:8001/search_semantic", json={
    "tenant_id": "user_123",
    "query_text": "red mug",
    "collections": ["entities_stream_v1", "user_notes_v1"],
    "n_results": 5
})

print(response.json())
# {"ok": true, "results": [...]}
```

### 5. POST `/search_time_window` - "What happened at 10:40?"

```python
response = requests.post("http://localhost:8001/search_time_window", json={
    "tenant_id": "user_123",
    "start_ts": 1730150400,
    "end_ts": 1730150500,
    "n_results": 10
})

print(response.json())
# {"ok": true, "results": [...]}
```

### 6. POST `/curate_to_ltm` - Session review (user selects keepers)

```python
response = requests.post("http://localhost:8001/curate_to_ltm", json={
    "tenant_id": "user_123",
    "session_id": "session_001",
    "items": [
        {
            "origin": "note",
            "origin_id": "user_123:note:67156a51",
            "text": "Spare keys are in the blue bowl by the door."
        }
    ],
    "tags": ["curated", "important"]
})

print(response.json())
# {"ok": true, "curated": 1}
```

### 7. POST `/compact` - TTL enforcement (housekeeping)

```python
response = requests.post("http://localhost:8001/compact", json={
    "tenant_id": "user_123",
    "ttl_hours": 72
})

print(response.json())
# {"ok": true, "cutoff_ts": 1730063865}
```

## Collections Detail

### 1. `frames_ephemeral_v1` - Scene summaries

**Purpose:** Fast recall of recent context  
**Document:** LLM scene summary text  
**Retention:** TTL 24-72h (configurable)  
**Query:** Time window search, session review  

**Metadata:**
```python
{
    "tenant_id": "user_123",
    "device_id": "glasses_01",
    "session_id": "session_001",
    "frame_ts": 1730150465,
    "tz": "America/Los_Angeles",
    "lat_lon_hash": "9q8yy",
    "objects": [{...}],
    "has_keys": True,
    "has_pills": False,
    "model_scene_ver": "scene_v0.3",
    "emb_model_ver": "minilm-l6-v2"
}
```

**ID:** `{tenant}:{session}:{frame_ts}`

### 2. `entities_stream_v1` - Per-object mentions

**Purpose:** Precise object queries across time  
**Document:** Canonical object string (e.g., "keys | silver | near edge")  
**Query:** Semantic search for specific objects  

**Metadata:**
```python
{
    "tenant_id": "user_123",
    "session_id": "session_001",
    "frame_ts": 1730150465,
    "obj_label": "keys",
    "obj_attrs": {"color": "silver", "rel_pos": "near edge"},
    "bbox": [0.42, 0.61, 0.13, 0.08],
    "scene_anchor": "kitchen table",
    "confidence": 0.93,
    "model_det_ver": "det_v1.1",
    "emb_model_ver": "minilm-l6-v2"
}
```

**ID:** `{tenant}:{session}:{frame_ts}:{label}#{idx}`

### 3. `latest_entities_v1` - Last-seen ("working memory")

**Purpose:** O(1) answer to "Where are my keys?"  
**Document:** Short sentence (e.g., "keys last seen at X near Y")  
**Upsert rule:** Only if confidence ≥ threshold AND object in whitelist  

**Metadata:**
```python
{
    "tenant_id": "user_123",
    "canonical_key": "keys@home",
    "last_frame_ts": 1730150465,
    "scene_anchor": "kitchen",
    "confidence": 0.93,
    "source_frame_id": "user_123:session_001:1730150465",
    "session_id": "session_001",
    "emb_model_ver": "minilm-l6-v2"
}
```

**ID:** `{tenant}:{canonical_key}`

### 4. `user_notes_v1` - User-authored memories

**Purpose:** Most trusted, durable memory  
**Document:** User text/transcript  
**Retention:** Permanent  

**Metadata:**
```python
{
    "tenant_id": "user_123",
    "note_id": "67156a51",
    "created_ts": 1730150502,
    "modality": "voice",  # or "typed"
    "priority": "high",
    "tags": ["medication"],
    "linked_entity": "pills@home",
    "emb_model_ver": "minilm-l6-v2"
}
```

**ID:** `{tenant}:note:{note_id}`

### 5. `long_term_memory_v1` - Curated facts

**Purpose:** Cost control - only what user keeps  
**Document:** Human-readable fact  
**Retention:** Permanent  

**Metadata:**
```python
{
    "tenant_id": "user_123",
    "origin": "note",
    "origin_id": "user_123:note:67156a51",
    "curated_by": "user",
    "curated_ts": 1730154000,
    "session_id": "session_001",
    "reviewed": True,
    "tags": ["keys", "home"],
    "emb_model_ver": "minilm-l6-v2"
}
```

**ID:** `{tenant}:ltm:{hash}`

## Tracked Objects (Whitelist)

Objects that get upserted to `latest_entities_v1`:

```python
TRACKED_OBJECTS = {
    "keys", "wallet", "phone", "glasses",
    "mug", "bottle", "pill_bottle", "pills",
    "medication", "tablet_box"
}
```

## Housekeeping

### Nightly compaction (cron)

```bash
# Add to crontab (crontab -e)
0 3 * * * curl -X POST http://localhost:8001/compact \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"user_123","ttl_hours":72}'
```

### Re-embed on model change

```python
# When changing embedding model, create *_v2 collections
# and re-process data from user_notes_v1 and long_term_memory_v1
```

## Integration Example

```python
# Your glasses capture loop
import requests
import time

BASE_URL = "http://localhost:8001"

def on_frame_capture(vision_data):
    """Called every 5 seconds from glasses"""
    # 1. Run vision → LLM to get summary + objects
    summary, objects = your_llm_pipeline(vision_data)
    
    # 2. Send to vector store
    response = requests.post(f"{BASE_URL}/add_frame", json={
        "tenant_id": "user_123",
        "device_id": "glasses_01",
        "session_id": f"session_{int(time.time())}",
        "frame_ts": int(time.time()),
        "scene_summary": summary,
        "objects": objects
    })
    
    return response.json()

def on_user_says_remember(text):
    """User says 'remember this'"""
    response = requests.post(f"{BASE_URL}/add_note", json={
        "tenant_id": "user_123",
        "text": text,
        "modality": "voice",
        "priority": "high"
    })
    return response.json()

def on_session_end(selected_items):
    """User reviews session and selects what to keep"""
    response = requests.post(f"{BASE_URL}/curate_to_ltm", json={
        "tenant_id": "user_123",
        "session_id": "current_session",
        "items": selected_items
    })
    return response.json()
```

## Project Structure

```
vector-store/
├── app.py                  # FastAPI endpoints
├── chroma_client.py        # ChromaDB client & collections
├── embeddings.py           # Embedding model (text only)
├── schema.py               # Pydantic models + safeguards
├── test_api.py             # Comprehensive test suite
├── requirements.txt        # Dependencies
├── .env.example           # Config template
└── README.md              # This file
```

## Performance Tips

1. **Batch frames** - Send multiple frames in one request if network is slow
2. **Async processing** - Queue frames, don't block glasses capture
3. **Local embeddings** - Use sentence-transformers (included) for privacy + speed
4. **Compact regularly** - Run `/compact` nightly to prevent DB bloat
5. **Index by time** - All IDs include timestamps for fast range queries

## Migration Strategy

When changing models or schema:

1. Create new collection `*_v2`
2. Keep `*_v1` running (read-only)
3. Re-embed important data (from `user_notes_v1`, `long_term_memory_v1`)
4. Gradually switch queries to `*_v2`
5. Delete `*_v1` after validation

## License

MIT

---

**Built with devil's-advocate safeguards:**  
TTL, confidence filtering, drift tracking, privacy-first, multi-tenant, versioned collections, meaningful IDs.
