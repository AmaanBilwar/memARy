# Microservice API Integration Guide

## Overview

Your vector store is a **standalone microservice** that other services can call via HTTP REST API. This guide shows how to integrate with it from any programming language or service.

## Architecture

```
┌─────────────────────────┐
│  Vision Service         │
│  (Python/Node/Go)       │
└──────────┬──────────────┘
           │ HTTP POST
           ↓
┌─────────────────────────┐       ┌──────────────────┐
│  Vector Store API       │←─────→│  ChromaDB        │
│  Port: 8001             │       │  (Persistence)   │
└──────────┬──────────────┘       └──────────────────┘
           │ HTTP POST
           ↓
┌─────────────────────────┐
│  Query Service          │
│  (Python/Node/Go)       │
└─────────────────────────┘
```

## Base URL

```
http://localhost:8001
```

**Production:** Replace with your deployed URL (e.g., `https://vector-store.yourdomain.com`)

---

## API Endpoints Summary

| Method | Endpoint | Purpose | Use Case |
|--------|----------|---------|----------|
| POST | `/add_frame` | Store captured frame | Vision service stores image analysis |
| POST | `/add_note` | Store user note | User says "remember this" |
| POST | `/search_last_seen` | Find last location | "Where are my keys?" |
| POST | `/search_semantic` | Semantic search | "Show me all red objects" |
| POST | `/search_time_window` | Time-based search | "What happened at 3pm?" |
| POST | `/curate_to_ltm` | Save to long-term | User selects memories to keep |
| POST | `/compact` | Cleanup old data | Nightly maintenance job |
| GET | `/healthz` | Health check | Service monitoring |

---

## 1. Store Data (Write Operations)

### A. Add Frame (Vision Analysis)

**Use Case:** Vision service analyzes an image and stores results

**Endpoint:** `POST /add_frame`

**Request Body:**
```json
{
  "tenant_id": "user_123",
  "device_id": "glasses_01",
  "session_id": "session_2024_10_25",
  "frame_ts": 1730000000,
  "scene_summary": "Office desk with laptop and red mug on the left",
  "objects": [
    {
      "label": "laptop",
      "confidence": 0.95,
      "bbox": [0.2, 0.3, 0.5, 0.6],
      "color": "silver",
      "rel_pos": "center of desk",
      "is_person": false
    },
    {
      "label": "mug",
      "confidence": 0.92,
      "bbox": [0.1, 0.4, 0.08, 0.12],
      "color": "red",
      "rel_pos": "left side",
      "is_person": false
    }
  ]
}
```

**Response:**
```json
{
  "ok": true,
  "frame_id": "user_123:session_2024_10_25:1730000000",
  "entity_ids": [
    "user_123:session_2024_10_25:1730000000:laptop#0",
    "user_123:session_2024_10_25:1730000000:mug#1"
  ],
  "latest_upserted": [
    "user_123:mug@home"
  ]
}
```

**What Happens:**
1. Scene stored in `frames_ephemeral_v1` (TTL: 72h)
2. Each object stored in `entities_stream_v1`
3. High-confidence tracked objects updated in `latest_entities_v1` (for "Where is X?" queries)

---

### B. Add Note (User Memory)

**Use Case:** User says "remember this" or types a note

**Endpoint:** `POST /add_note`

**Request Body:**
```json
{
  "tenant_id": "user_123",
  "text": "Mom's medication is in the left kitchen cabinet, top shelf",
  "modality": "voice",
  "priority": "high",
  "tags": ["medication", "kitchen"],
  "linked_entity": "pills@home"
}
```

**Response:**
```json
{
  "ok": true,
  "note_id": "67a3c2f1"
}
```

---

## 2. Fetch Data (Read Operations)

### A. Search Last Seen (Fast Lookup)

**Use Case:** Answer "Where are my keys?"

**Endpoint:** `POST /search_last_seen`

**Request Body:**
```json
{
  "tenant_id": "user_123",
  "canonical_key": "keys@home"
}
```

**Response:**
```json
{
  "ok": true,
  "found": true,
  "document": "keys last seen at 1730000000 on kitchen table near edge",
  "metadata": {
    "tenant_id": "user_123",
    "canonical_key": "keys@home",
    "last_frame_ts": 1730000000,
    "scene_anchor": "kitchen table",
    "confidence": 0.93,
    "session_id": "session_2024_10_25"
  }
}
```

**If Not Found:**
```json
{
  "ok": true,
  "found": false
}
```

---

### B. Semantic Search (Vector Similarity)

**Use Case:** Find related memories by meaning

**Endpoint:** `POST /search_semantic`

**Request Body:**
```json
{
  "tenant_id": "user_123",
  "query_text": "red coffee mug",
  "collections": ["entities_stream_v1", "user_notes_v1", "frames_ephemeral_v1"],
  "n_results": 5
}
```

**Response:**
```json
{
  "ok": true,
  "results": [
    {
      "collection": "entities_stream_v1",
      "id": "user_123:session_001:1730000000:mug#1",
      "document": "mug | red | left side of desk",
      "metadata": {
        "tenant_id": "user_123",
        "obj_label": "mug",
        "obj_attrs": "{\"color\": \"red\", \"rel_pos\": \"left side\"}",
        "confidence": 0.92,
        "frame_ts": 1730000000
      },
      "distance": 0.23
    }
  ]
}
```

**Note:** Lower distance = more similar

---

### C. Time Window Search

**Use Case:** "What was I doing around 3pm?"

**Endpoint:** `POST /search_time_window`

**Request Body:**
```json
{
  "tenant_id": "user_123",
  "start_ts": 1730000000,
  "end_ts": 1730003600,
  "n_results": 10
}
```

**Response:**
```json
{
  "ok": true,
  "results": [
    {
      "id": "user_123:session_001:1730000000",
      "document": "Office desk with laptop and red mug",
      "metadata": {
        "frame_ts": 1730000000,
        "session_id": "session_001"
      }
    }
  ]
}
```

---

## 3. FastAPI Client (Recommended)

### Simple FastAPI Client

```python
import httpx
from typing import Optional
from fastapi import HTTPException

class VectorStoreClient:
    """FastAPI-compatible async client for vector store"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def add_frame(self, tenant_id: str, session_id: str, scene_summary: str, 
                       objects: list, device_id: str = "glasses_01"):
        """Store frame analysis"""
        try:
            response = await self.client.post(
                f"{self.base_url}/add_frame",
                json={
                    "tenant_id": tenant_id,
                    "device_id": device_id,
                    "session_id": session_id,
                    "frame_ts": int(time.time()),
                    "scene_summary": scene_summary,
                    "objects": objects
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"Vector store error: {str(e)}")
    
    async def search_last_seen(self, tenant_id: str, canonical_key: str):
        """Find last seen location"""
        try:
            response = await self.client.post(
                f"{self.base_url}/search_last_seen",
                json={"tenant_id": tenant_id, "canonical_key": canonical_key}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"Vector store error: {str(e)}")
    
    async def search_semantic(self, tenant_id: str, query: str, 
                             collections: list = None, n_results: int = 5):
        """Semantic search"""
        try:
            response = await self.client.post(
                f"{self.base_url}/search_semantic",
                json={
                    "tenant_id": tenant_id,
                    "query_text": query,
                    "collections": collections or ["entities_stream_v1", "user_notes_v1"],
                    "n_results": n_results
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"Vector store error: {str(e)}")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Usage in FastAPI endpoint
from fastapi import FastAPI, Depends

app = FastAPI()

# Dependency injection
async def get_vector_client():
    client = VectorStoreClient("http://localhost:8001")
    try:
        yield client
    finally:
        await client.close()

@app.post("/store")
async def store_data(client: VectorStoreClient = Depends(get_vector_client)):
    """Your endpoint that calls vector store"""
    result = await client.add_frame(
        tenant_id="user_123",
        session_id="session_001",
        scene_summary="Kitchen with keys",
        objects=[{"label": "keys", "confidence": 0.95, "is_person": False}]
    )
    return result

@app.get("/search/{object_name}")
async def search_object(object_name: str, client: VectorStoreClient = Depends(get_vector_client)):
    """Search for object"""
    result = await client.search_last_seen("user_123", f"{object_name}@home")
    return result
```

### Simplified Synchronous Client (for scripts)

If you need synchronous calls for simple scripts:

```python
import httpx

class VectorStoreClient:
    """Synchronous client for scripts and non-FastAPI code"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
    
    def add_frame(self, tenant_id: str, session_id: str, scene_summary: str, objects: list):
        """Store frame"""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/add_frame",
                json={
                    "tenant_id": tenant_id,
                    "device_id": "glasses_01",
                    "session_id": session_id,
                    "frame_ts": int(time.time()),
                    "scene_summary": scene_summary,
                    "objects": objects
                }
            )
            response.raise_for_status()
            return response.json()
    
    def search_last_seen(self, tenant_id: str, canonical_key: str):
        """Find object"""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/search_last_seen",
                json={"tenant_id": tenant_id, "canonical_key": canonical_key}
            )
            response.raise_for_status()
            return response.json()

# Usage
client = VectorStoreClient()
result = client.add_frame("user_123", "session_001", "Keys on table", [...])
location = client.search_last_seen("user_123", "keys@home")
```

---

## 4. FastAPI Dependency Injection Pattern

### Reusable Client as Dependency

```python
from fastapi import FastAPI, Depends, HTTPException
import httpx
from typing import AsyncGenerator

app = FastAPI()

# Singleton client instance
class VectorStoreClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client = None
    
    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
    
    async def add_frame(self, data: dict):
        client = await self.get_client()
        response = await client.post(f"{self.base_url}/add_frame", json=data)
        response.raise_for_status()
        return response.json()
    
    async def search_last_seen(self, tenant_id: str, canonical_key: str):
        client = await self.get_client()
        response = await client.post(
            f"{self.base_url}/search_last_seen",
            json={"tenant_id": tenant_id, "canonical_key": canonical_key}
        )
        response.raise_for_status()
        return response.json()

# Global instance
vector_store = VectorStoreClient("http://localhost:8001")

# Dependency function
async def get_vector_store() -> VectorStoreClient:
    return vector_store

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown():
    await vector_store.close()

# Use in endpoints
@app.post("/api/store")
async def store_memory(
    scene: str,
    objects: list,
    vs: VectorStoreClient = Depends(get_vector_store)
):
    """Your API that calls vector store"""
    try:
        result = await vs.add_frame({
            "tenant_id": "user_123",
            "device_id": "glasses_01",
            "session_id": "session_001",
            "frame_ts": int(time.time()),
            "scene_summary": scene,
            "objects": objects
        })
        return {"success": True, "frame_id": result["frame_id"]}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail="Vector store unavailable")

@app.get("/api/find/{object_name}")
async def find_object(
    object_name: str,
    vs: VectorStoreClient = Depends(get_vector_store)
):
    """Search for object"""
    try:
        result = await vs.search_last_seen("user_123", f"{object_name}@home")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail="Vector store unavailable")
```

## 5. Error Handling

### HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check request format |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Fix request fields |
| 500 | Server Error | Retry with backoff |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### FastAPI Error Handling with Retries

```python
import httpx
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential

class VectorStoreClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def add_frame(self, data: dict):
        """Store frame with auto-retry on failure"""
        try:
            response = await self.client.post(f"{self.base_url}/add_frame", json=data)
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise HTTPException(status_code=400, detail="Invalid request format")
            elif e.response.status_code >= 500:
                raise  # Will be retried by tenacity
            else:
                raise HTTPException(status_code=e.response.status_code, detail=str(e))
        
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Vector store timeout")
        
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Vector store unavailable")
    
    async def close(self):
        await self.client.aclose()

# Install: pip install tenacity
```

---

## 6. Best Practices for FastAPI Microservices

### A. Service Discovery

**Development:**
```
VECTOR_STORE_URL=http://localhost:8001
```

**Production:**
```
VECTOR_STORE_URL=http://vector-store-service:8001  # Kubernetes service name
# or
VECTOR_STORE_URL=https://vector-store.yourdomain.com
```

### B. Health Checks in FastAPI

```python
import httpx
from fastapi import FastAPI

app = FastAPI()

async def check_vector_store_health(base_url: str) -> bool:
    """Check if vector store is healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/healthz")
            return response.status_code == 200
    except:
        return False

@app.on_event("startup")
async def startup():
    """Wait for vector store on startup"""
    import asyncio
    vector_store_url = "http://localhost:8001"
    
    for i in range(30):
        if await check_vector_store_health(vector_store_url):
            print("✓ Vector store is healthy")
            return
        print(f"⏳ Waiting for vector store... ({i+1}/30)")
        await asyncio.sleep(2)
    
    raise RuntimeError("Vector store unavailable")

@app.get("/health")
async def health():
    """Your service health check"""
    vector_healthy = await check_vector_store_health("http://localhost:8001")
    return {
        "service": "my-service",
        "status": "healthy",
        "dependencies": {
            "vector_store": "connected" if vector_healthy else "disconnected"
        }
    }
```

### C. Batch Operations with FastAPI

```python
import asyncio
import httpx
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()
client = httpx.AsyncClient(timeout=30.0)

async def store_frames_batch(frames: list[dict]):
    """Store multiple frames concurrently"""
    tasks = [
        client.post("http://localhost:8001/add_frame", json=frame)
        for frame in frames
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful = sum(1 for r in results if not isinstance(r, Exception))
    print(f"✓ Stored {successful}/{len(frames)} frames")
    return successful

@app.post("/batch-store")
async def batch_store(frames: list[dict], background_tasks: BackgroundTasks):
    """Store multiple frames at once"""
    # Process in background to not block response
    background_tasks.add_task(store_frames_batch, frames)
    return {"accepted": len(frames), "processing": "background"}
```

### D. Rate Limiting in FastAPI

```python
from fastapi import FastAPI, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/store")
@limiter.limit("10/minute")  # 10 requests per minute
async def store_data(request: Request):
    """Rate-limited endpoint"""
    # Call vector store
    pass

# Install: pip install slowapi
```

---

## 6. Docker Compose Example

If using Docker Compose for local development:

```yaml
version: '3.8'

services:
  vector-store:
    build: ./vector-store
    ports:
      - "8001:8001"
    environment:
      - CHROMA_DIR=/data/chroma
      - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    volumes:
      - vector-data:/data/chroma
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5

  vision-service:
    build: ./vision-processor
    depends_on:
      vector-store:
        condition: service_healthy
    environment:
      - VECTOR_STORE_URL=http://vector-store:8001
      - REKA_API_KEY=${REKA_API_KEY}

  query-service:
    build: ./query-service
    depends_on:
      - vector-store
    environment:
      - VECTOR_STORE_URL=http://vector-store:8001

volumes:
  vector-data:
```

---

## 7. Kubernetes Deployment

Example K8s service:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: vector-store
spec:
  selector:
    app: vector-store
  ports:
    - port: 8001
      targetPort: 8001
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vector-store
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vector-store
  template:
    metadata:
      labels:
        app: vector-store
    spec:
      containers:
      - name: vector-store
        image: your-registry/vector-store:latest
        ports:
        - containerPort: 8001
        env:
        - name: CHROMA_DIR
          value: "/data/chroma"
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 5
```

Other services connect to: `http://vector-store:8001`

---

## 8. Testing Your Integration

### Unit Test Example

```python
import pytest
from unittest.mock import Mock, patch
import requests

@patch('requests.post')
def test_add_frame(mock_post):
    """Test frame storage"""
    # Mock response
    mock_post.return_value.json.return_value = {
        "ok": True,
        "frame_id": "user_123:session_001:1730000000"
    }
    mock_post.return_value.raise_for_status = Mock()
    
    # Make call
    client = VectorStoreClient()
    result = client.add_frame("session_001", "test scene", [])
    
    # Assertions
    assert result["ok"] == True
    assert "frame_id" in result
    mock_post.assert_called_once()
```

### Integration Test

```python
def test_full_workflow():
    """Test complete store and retrieve flow"""
    client = VectorStoreClient("http://localhost:8001")
    
    # Store frame
    store_result = client.add_frame(
        session_id="test_session",
        scene_summary="Test scene with keys",
        objects=[{
            "label": "keys",
            "confidence": 0.95,
            "color": "silver",
            "rel_pos": "on table",
            "is_person": False
        }]
    )
    assert store_result["ok"] == True
    
    # Search for it
    search_result = client.search_last_seen("keys@home")
    assert search_result["found"] == True
    assert "keys" in search_result["document"].lower()
```

---

## Summary

### Quick Start Checklist

- [ ] Vector store running on port 8001
- [ ] Health check passes: `curl http://localhost:8001/healthz`
- [ ] Install client library (requests, axios, etc.)
- [ ] Set `VECTOR_STORE_URL` environment variable
- [ ] Implement error handling and retries
- [ ] Test with sample data

### Key Endpoints

**Write:**
- `/add_frame` - Store image analysis
- `/add_note` - Store user memory

**Read:**
- `/search_last_seen` - Fast "Where is X?" lookup
- `/search_semantic` - Fuzzy semantic search
- `/search_time_window` - Time-based retrieval

**Your microservice architecture is ready!** Any service can call these APIs to store or fetch data from the vector store. 🚀

