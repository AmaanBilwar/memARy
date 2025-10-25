"""
Simple FastAPI service to store and fetch from vector database
"""
from typing import Union, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import time
import os
import base64
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS - Allow requests from any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vector store URL - use env var for Heroku
VECTOR_STORE_URL = os.getenv("VECTOR_STORE_URL", "http://localhost:8001")

# Async HTTP client
client = httpx.AsyncClient(timeout=30.0)


# Request models
class ImageUpload(BaseModel):
    image_base64: str
    session_id: Optional[str] = "default-session"


class StoreMemory(BaseModel):
    scene: str
    objects: list
    session_id: Optional[str] = "default-session"


@app.get("/")
def read_root():
    return {"service": "memory-api", "status": "running"}


@app.post("/store")
async def store_memory(data: ImageUpload):
    """Upload and process an image, then store the results"""
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(data.image_base64)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(image_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Import vision processor (make sure vision-processor is in path)
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'vision-processor'))
            from vision_reka import analyze_image
            
            # Analyze image
            analysis_result = analyze_image(tmp_path)
            
            if not analysis_result.get("ok"):
                return {
                    "ok": False,
                    "error": "Image analysis failed",
                    "details": analysis_result
                }
            
            # Extract results
            scene = analysis_result["result"].get("scene_summary", "Unknown scene")
            objects = analysis_result["result"].get("objects", [])
            
            # Try to store in vector database (gracefully handle if down)
            storage_result = None
            try:
                response = await client.post(
                    f"{VECTOR_STORE_URL}/add_frame",
                    json={
                        "tenant_id": "user_123",
                        "device_id": "web_upload",
                        "session_id": data.session_id,
                        "frame_ts": int(time.time()),
                        "scene_summary": scene,
                        "objects": objects
                    },
                    timeout=5.0
                )
                response.raise_for_status()
                storage_result = response.json()
            except Exception as storage_error:
                storage_result = {
                    "warning": "Vector store unavailable",
                    "error": str(storage_error)
                }
            
            return {
                "ok": True,
                "analysis": {
                    "scene": scene,
                    "objects": objects,
                    "full_result": analysis_result["result"]
                },
                "storage": storage_result
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/store_direct")
async def store_direct(data: StoreMemory):
    """Store pre-analyzed data directly (no image processing)"""
    try:
        response = await client.post(
            f"{VECTOR_STORE_URL}/add_frame",
            json={
                "tenant_id": "user_123",
                "device_id": "direct_upload",
                "session_id": data.session_id,
                "frame_ts": int(time.time()),
                "scene_summary": data.scene,
                "objects": data.objects
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
async def search_memories(query: str, session_id: Optional[str] = None, limit: int = 5):
    """Search all memories"""
    try:
        response = await client.post(
            f"{VECTOR_STORE_URL}/search_semantic",
            json={
                "tenant_id": "user_123",
                "query_text": query,
                "collections": ["entities_stream_v1", "user_notes_v1", "frames_ephemeral_v1"],
                "n_results": limit
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup():
    print("✓ Memory API starting...")
    print(f"✓ Vector store: {VECTOR_STORE_URL}")

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()
    print("✓ Memory API shutdown complete")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))  # Heroku sets PORT env var
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload for production
        workers=1,      # Single worker (increase for high traffic)
        log_level="info"
    )

