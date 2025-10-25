"""
Simple FastAPI service to store and fetch from vector database
"""
from typing import Union
from fastapi import FastAPI, HTTPException
import httpx
import time

app = FastAPI()

# Vector store URL
VECTOR_STORE_URL = "http://localhost:8001"

# Async HTTP client
client = httpx.AsyncClient(timeout=30.0)


@app.get("/")
def read_root():
    return {"service": "memory-api", "status": "running"}


@app.post("/store")
async def store_memory(scene: str, objects: list):
    """Store a memory (image analysis result)"""
    try:
        response = await client.post(
            f"{VECTOR_STORE_URL}/add_frame",
            json={
                "tenant_id": "user_123",
                "device_id": "glasses_01",
                "session_id": "session_001",
                "frame_ts": int(time.time()),
                "scene_summary": scene,
                "objects": objects
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/find/{object_name}")
async def find_object(object_name: str):
    """Find where an object was last seen"""
    try:
        response = await client.post(
            f"{VECTOR_STORE_URL}/search_last_seen",
            json={
                "tenant_id": "user_123",
                "canonical_key": f"{object_name}@home"
            }
        )
        response.raise_for_status()
        result = response.json()
        
        if not result.get("found"):
            raise HTTPException(status_code=404, detail=f"{object_name} not found")
        
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search_memories(q: str, limit: int = 5):
    """Search all memories"""
    try:
        response = await client.post(
            f"{VECTOR_STORE_URL}/search_semantic",
            json={
                "tenant_id": "user_123",
                "query_text": q,
                "collections": ["entities_stream_v1", "user_notes_v1", "frames_ephemeral_v1"],
                "n_results": limit
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()

