# API Quick Reference Card

## 🚀 Quick Start

Your vector store runs on **http://localhost:8001**

```bash
# Check if running
curl http://localhost:8001/healthz
```

---

## 📝 Store Data

### Store Image Analysis
```bash
curl -X POST http://localhost:8001/add_frame \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "user_123",
    "device_id": "glasses_01",
    "session_id": "session_001",
    "frame_ts": 1730000000,
    "scene_summary": "Kitchen with keys on counter",
    "objects": [{
      "label": "keys",
      "confidence": 0.95,
      "color": "silver",
      "rel_pos": "on counter",
      "is_person": false
    }]
  }'
```

### Store User Note
```bash
curl -X POST http://localhost:8001/add_note \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "user_123",
    "text": "Mom'\''s pills are in the left cabinet",
    "modality": "voice",
    "priority": "high"
  }'
```

---

## 🔍 Fetch Data

### "Where are my keys?"
```bash
curl -X POST http://localhost:8001/search_last_seen \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "user_123",
    "canonical_key": "keys@home"
  }'
```

### Semantic Search
```bash
curl -X POST http://localhost:8001/search_semantic \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "user_123",
    "query_text": "red mug",
    "n_results": 5
  }'
```

### Time-Based Search
```bash
curl -X POST http://localhost:8001/search_time_window \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "user_123",
    "start_ts": 1730000000,
    "end_ts": 1730003600,
    "n_results": 10
  }'
```

---

## 🐍 FastAPI Client (Recommended)

```python
import httpx
from fastapi import FastAPI, Depends

app = FastAPI()

# Async client
class VectorStoreClient:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def add_frame(self, data: dict):
        response = await self.client.post(f"{self.base_url}/add_frame", json=data)
        response.raise_for_status()
        return response.json()
    
    async def search_last_seen(self, tenant_id: str, canonical_key: str):
        response = await self.client.post(
            f"{self.base_url}/search_last_seen",
            json={"tenant_id": tenant_id, "canonical_key": canonical_key}
        )
        response.raise_for_status()
        return response.json()

# Dependency
vector_store = VectorStoreClient()

async def get_vs():
    return vector_store

# Use in endpoints
@app.post("/store")
async def store(vs: VectorStoreClient = Depends(get_vs)):
    result = await vs.add_frame({
        "tenant_id": "user_123",
        "device_id": "glasses_01",
        "session_id": "session_001",
        "frame_ts": 1730000000,
        "scene_summary": "Kitchen with keys",
        "objects": [{"label": "keys", "confidence": 0.95, "is_person": False}]
    })
    return result

@app.get("/find/{object}")
async def find(object: str, vs: VectorStoreClient = Depends(get_vs)):
    result = await vs.search_last_seen("user_123", f"{object}@home")
    return result
```

---

## 🔧 Dependencies

```bash
# For FastAPI microservices
pip install httpx fastapi uvicorn

# Optional: Retries, rate limiting
pip install tenacity slowapi
```

---

## 📊 All Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Health check |
| `/add_frame` | POST | Store image analysis |
| `/add_note` | POST | Store user note |
| `/search_last_seen` | POST | Fast "Where is X?" |
| `/search_semantic` | POST | Semantic search |
| `/search_time_window` | POST | Time-based search |
| `/curate_to_ltm` | POST | Save to long-term |
| `/compact` | POST | Cleanup old data |

---

## ⚙️ Environment Variables

```bash
# For other services calling this API
export VECTOR_STORE_URL=http://localhost:8001
export TENANT_ID=user_123
export DEVICE_ID=glasses_01
```

---

## 🐳 Docker

```yaml
services:
  vector-store:
    ports:
      - "8001:8001"
  
  your-service:
    environment:
      - VECTOR_STORE_URL=http://vector-store:8001
```

---

## 🔧 FastAPI Error Handling

```python
import httpx
from fastapi import HTTPException

async def call_vector_store():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=503, detail="Vector store error")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect")
```

---

## 📖 Full Documentation

- **API Guide:** See `MICROSERVICE_API_GUIDE.md`
- **Example Service:** See `example-client-service/`
- **Architecture:** See `ARCHITECTURE.md`

---

## ✅ Quick Test

```bash
# 1. Check health
curl http://localhost:8001/healthz

# 2. Store something
curl -X POST http://localhost:8001/add_frame \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"user_123","device_id":"test","session_id":"test","frame_ts":1730000000,"scene_summary":"test","objects":[]}'

# 3. Search for it
curl -X POST http://localhost:8001/search_semantic \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"user_123","query_text":"test","n_results":5}'
```

---

**Your microservice API is ready to use!** 🚀

