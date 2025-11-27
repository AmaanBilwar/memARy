"""
Example Query Service - Microservice that calls Vector Store API
This demonstrates how another microservice would integrate with your vector store
"""
import requests
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

# Configuration
VECTOR_STORE_URL = os.getenv("VECTOR_STORE_URL", "http://localhost:8001")

app = FastAPI(title="Query Service Example", version="1.0.0")


# === Vector Store Client ===

class VectorStoreClient:
    """Client for communicating with vector store microservice"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def search_last_seen(self, tenant_id: str, canonical_key: str) -> dict:
        """Call vector store to find last seen location"""
        try:
            response = requests.post(
                f"{self.base_url}/search_last_seen",
                json={
                    "tenant_id": tenant_id,
                    "canonical_key": canonical_key
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=503, detail=f"Vector store unavailable: {str(e)}")
    
    def search_semantic(self, tenant_id: str, query: str, n_results: int = 5) -> dict:
        """Call vector store for semantic search"""
        try:
            response = requests.post(
                f"{self.base_url}/search_semantic",
                json={
                    "tenant_id": tenant_id,
                    "query_text": query,
                    "collections": ["entities_stream_v1", "user_notes_v1", "frames_ephemeral_v1"],
                    "n_results": n_results
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=503, detail=f"Vector store unavailable: {str(e)}")
    
    def health_check(self) -> bool:
        """Check if vector store is healthy"""
        try:
            response = requests.get(f"{self.base_url}/healthz", timeout=5)
            return response.status_code == 200
        except:
            return False


# Initialize client
vector_store = VectorStoreClient(VECTOR_STORE_URL)


# === Request/Response Models ===

class WhereIsRequest(BaseModel):
    """Natural language query: 'Where are my keys?'"""
    user_id: str
    object_name: str  # e.g., "keys", "wallet", "phone"


class WhereIsResponse(BaseModel):
    """Response with location information"""
    found: bool
    object_name: str
    location: Optional[str] = None
    last_seen_time: Optional[int] = None
    confidence: Optional[float] = None


class SearchRequest(BaseModel):
    """Semantic search request"""
    user_id: str
    query: str
    limit: int = 5


class SearchResult(BaseModel):
    """Individual search result"""
    text: str
    relevance_score: float
    timestamp: Optional[int] = None


class SearchResponse(BaseModel):
    """Search results"""
    query: str
    results: list[SearchResult]


# === API Endpoints ===

@app.get("/health")
async def health():
    """Health check that also verifies vector store connection"""
    vector_store_healthy = vector_store.health_check()
    
    return {
        "service": "query-service",
        "status": "healthy",
        "vector_store": "connected" if vector_store_healthy else "disconnected"
    }


@app.post("/where-is", response_model=WhereIsResponse)
async def where_is(request: WhereIsRequest):
    """
    Natural language query: 'Where are my keys?'
    Calls vector store's last_seen endpoint
    """
    # Build canonical key (you might want more sophisticated logic here)
    canonical_key = f"{request.object_name}@home"
    
    # Call vector store microservice
    result = vector_store.search_last_seen(
        tenant_id=request.user_id,
        canonical_key=canonical_key
    )
    
    if not result["found"]:
        return WhereIsResponse(
            found=False,
            object_name=request.object_name
        )
    
    # Parse vector store response
    metadata = result.get("metadata", {})
    
    return WhereIsResponse(
        found=True,
        object_name=request.object_name,
        location=metadata.get("scene_anchor", result.get("document", "")),
        last_seen_time=metadata.get("last_frame_ts"),
        confidence=metadata.get("confidence")
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Semantic search across all memories
    Calls vector store's semantic search endpoint
    """
    # Call vector store microservice
    result = vector_store.search_semantic(
        tenant_id=request.user_id,
        query=request.query,
        n_results=request.limit
    )
    
    # Transform vector store results to our format
    search_results = []
    for item in result.get("results", []):
        search_results.append(SearchResult(
            text=item.get("document", ""),
            relevance_score=1.0 - item.get("distance", 0.5),  # Convert distance to similarity
            timestamp=item.get("metadata", {}).get("frame_ts")
        ))
    
    return SearchResponse(
        query=request.query,
        results=search_results
    )


@app.get("/user/{user_id}/recent")
async def get_recent_memories(user_id: str, limit: int = 10):
    """
    Get recent memories for a user
    Example of calling search_time_window on vector store
    """
    import time
    
    # Last 24 hours
    end_ts = int(time.time())
    start_ts = end_ts - (24 * 60 * 60)
    
    try:
        response = requests.post(
            f"{VECTOR_STORE_URL}/search_time_window",
            json={
                "tenant_id": user_id,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "n_results": limit
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Vector store unavailable: {str(e)}")


# === Startup Event ===

@app.on_event("startup")
async def startup():
    """Check vector store connection on startup"""
    print(f"Query Service starting...")
    print(f"Vector Store URL: {VECTOR_STORE_URL}")
    
    if vector_store.health_check():
        print("✓ Connected to vector store")
    else:
        print("⚠️  WARNING: Cannot connect to vector store")
        print("   Make sure vector store is running on", VECTOR_STORE_URL)


if __name__ == "__main__":
    import uvicorn
    
    print("="*60)
    print("QUERY SERVICE - Example Microservice")
    print("="*60)
    print(f"This service calls Vector Store API at: {VECTOR_STORE_URL}")
    print()
    print("Starting server on http://localhost:8002")
    print("Docs: http://localhost:8002/docs")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8002)

