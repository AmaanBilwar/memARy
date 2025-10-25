# Example Client Service

This is an example microservice that demonstrates how to call your vector store API from another service.

## What This Does

This `query-service` is a **separate microservice** that:
1. Exposes its own REST API on port 8002
2. Calls the vector store API (port 8001) internally
3. Demonstrates proper microservice-to-microservice communication

## Architecture

```
User/Frontend
      ↓ HTTP Request
┌─────────────────────────┐
│  Query Service          │  Port 8002
│  (This example)         │
└──────────┬──────────────┘
           │ HTTP Request
           ↓
┌─────────────────────────┐
│  Vector Store API       │  Port 8001
│  (Your service)         │
└──────────┬──────────────┘
           │
           ↓
      ChromaDB
```

## Setup

### 1. Install Dependencies

```bash
cd example-client-service
pip install fastapi uvicorn requests pydantic
```

### 2. Start Vector Store (Terminal 1)

```bash
cd ../vector-store
source venv/bin/activate
python app.py
```

Should be running on http://localhost:8001

### 3. Start Query Service (Terminal 2)

```bash
cd example-client-service
python query_service.py
```

Should be running on http://localhost:8002

## API Endpoints

### 1. Health Check

```bash
curl http://localhost:8002/health
```

Response:
```json
{
  "service": "query-service",
  "status": "healthy",
  "vector_store": "connected"
}
```

### 2. Where Is Query

**Ask:** "Where are my keys?"

```bash
curl -X POST http://localhost:8002/where-is \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "object_name": "keys"
  }'
```

Response:
```json
{
  "found": true,
  "object_name": "keys",
  "location": "kitchen table",
  "last_seen_time": 1730000000,
  "confidence": 0.95
}
```

**Internally, this calls:**
```
POST http://localhost:8001/search_last_seen
{
  "tenant_id": "user_123",
  "canonical_key": "keys@home"
}
```

### 3. Semantic Search

**Ask:** "Show me red objects"

```bash
curl -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "query": "red mug",
    "limit": 5
  }'
```

Response:
```json
{
  "query": "red mug",
  "results": [
    {
      "text": "red mug on desk",
      "relevance_score": 0.92,
      "timestamp": 1730000000
    }
  ]
}
```

**Internally, this calls:**
```
POST http://localhost:8001/search_semantic
{
  "tenant_id": "user_123",
  "query_text": "red mug",
  "collections": ["entities_stream_v1", "user_notes_v1"],
  "n_results": 5
}
```

### 4. Recent Memories

```bash
curl http://localhost:8002/user/user_123/recent?limit=10
```

Returns last 24 hours of memories.

## Interactive API Documentation

Visit http://localhost:8002/docs for interactive Swagger UI

## Code Walkthrough

### Vector Store Client

```python
class VectorStoreClient:
    """Client for communicating with vector store microservice"""
    
    def search_last_seen(self, tenant_id: str, canonical_key: str):
        """Call vector store API"""
        response = requests.post(
            f"{self.base_url}/search_last_seen",
            json={"tenant_id": tenant_id, "canonical_key": canonical_key},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
```

### Using the Client

```python
# Initialize once
vector_store = VectorStoreClient("http://localhost:8001")

# Call from your endpoint
@app.post("/where-is")
async def where_is(request: WhereIsRequest):
    # Call vector store microservice
    result = vector_store.search_last_seen(
        tenant_id=request.user_id,
        canonical_key=f"{request.object_name}@home"
    )
    
    # Transform and return
    return WhereIsResponse(
        found=result["found"],
        location=result.get("metadata", {}).get("scene_anchor")
    )
```

## Key Concepts

### 1. Service-to-Service Communication

- **Query Service** (port 8002) is a client
- **Vector Store** (port 8001) is the server
- Communication via HTTP REST API

### 2. Abstraction Layer

The query service provides:
- Simpler API for frontend
- Business logic layer
- Error handling
- Response transformation

### 3. Health Checks

Both services should:
- Expose `/health` or `/healthz`
- Check dependencies (database, other services)
- Return clear status

### 4. Error Handling

```python
try:
    response = requests.post(...)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    raise HTTPException(status_code=503, detail="Service unavailable")
```

## Environment Variables

```bash
# Vector store location
export VECTOR_STORE_URL=http://localhost:8001

# In production
export VECTOR_STORE_URL=http://vector-store-service:8001
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  vector-store:
    build: ./vector-store
    ports:
      - "8001:8001"
  
  query-service:
    build: ./example-client-service
    ports:
      - "8002:8002"
    environment:
      - VECTOR_STORE_URL=http://vector-store:8001
    depends_on:
      - vector-store
```

## Testing

```python
# Test the integration
def test_where_is():
    response = requests.post(
        "http://localhost:8002/where-is",
        json={"user_id": "user_123", "object_name": "keys"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "found" in data
```

## Extending This Example

You can add:
- Authentication/authorization
- Caching layer (Redis)
- Request rate limiting
- Logging and monitoring
- Circuit breaker pattern
- gRPC instead of REST
- Message queue (RabbitMQ, Kafka)

## Summary

This example shows:
1. ✅ How to call vector store API from another service
2. ✅ Proper error handling and timeouts
3. ✅ Health check integration
4. ✅ Request/response transformation
5. ✅ Service-to-service communication patterns

**Your microservice architecture is working!** 🚀

