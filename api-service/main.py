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

# In-memory storage (fallback when vector store is down)
memory_store = []


# Request models
class ImageUpload(BaseModel):
    image_base64: str
    session_id: Optional[str] = "default-session"


class StoreMemory(BaseModel):
    scene: str
    objects: list
    session_id: Optional[str] = "default-session"


class TextToJSON(BaseModel):
    text_summary: str
    session_id: Optional[str] = "default-session"


@app.get("/")
def read_root():
    return {"service": "memory-api", "status": "running"}


@app.get("/debug/memory")
def get_memory_store():
    """View in-memory storage (for debugging)"""
    return {
        "total_items": len(memory_store),
        "items": memory_store
    }


@app.get("/memories")
def get_all_memories(session_id: Optional[str] = None, limit: int = 100):
    """Get all memories, optionally filtered by session, sorted by timestamp (newest first)"""
    # Filter by session if specified
    if session_id:
        filtered = [m for m in memory_store if m.get("session_id") == session_id]
    else:
        filtered = memory_store
    
    # Sort by timestamp (newest first)
    sorted_memories = sorted(filtered, key=lambda x: x.get("timestamp", 0), reverse=True)
    
    # Limit results
    limited = sorted_memories[:limit]
    
    return {
        "ok": True,
        "total": len(limited),
        "memories": limited
    }


@app.post("/clear_storage")
async def clear_storage():
    """Clear all stored memories (in-memory and vector store)"""
    try:
        # Clear in-memory storage
        initial_count = len(memory_store)
        memory_store.clear()
        
        # Try to clear vector store
        vector_cleared = False
        try:
            # Clear all collections in vector store
            collections = ["frames_ephemeral_v1", "entities_stream_v1", "latest_entities_v1"]
            for collection in collections:
                response = await client.post(
                    f"{VECTOR_STORE_URL}/clear_collection",
                    json={"collection_name": collection},
                    timeout=5.0
                )
            vector_cleared = True
        except Exception as e:
            print(f"[WARNING] Could not clear vector store: {e}")
        
        return {
            "ok": True,
            "message": "Storage cleared successfully",
            "cleared_memory_items": initial_count,
            "vector_store_cleared": vector_cleared
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            vision_path = os.path.join(os.path.dirname(__file__), '..', 'vision-processor')
            if vision_path not in sys.path:
                sys.path.insert(0, vision_path)
            
            print(f"[DEBUG] Importing vision_reka from: {vision_path}")
            from vision_reka import analyze_image
            
            # Analyze image
            print(f"[DEBUG] Analyzing image: {tmp_path}")
            analysis_result = analyze_image(tmp_path)
            print(f"[DEBUG] Analysis result: {analysis_result}")
            
            # Check if result is dict with "ok" key or direct result
            if isinstance(analysis_result, dict):
                if "ok" in analysis_result and not analysis_result.get("ok"):
                    return {
                        "ok": False,
                        "error": "Image analysis failed",
                        "details": analysis_result
                    }
                # If it's a direct result (no "ok" wrapper), use it directly
                if "scene_summary" in analysis_result:
                    scene = analysis_result.get("scene_summary", "Unknown scene")
                    objects = analysis_result.get("objects", [])
                # If it has "result" wrapper, extract from there
                elif "result" in analysis_result:
                    scene = analysis_result["result"].get("scene_summary", "Unknown scene")
                    objects = analysis_result["result"].get("objects", [])
                else:
                    return {
                        "ok": False,
                        "error": "Unexpected analysis format",
                        "details": analysis_result
                    }
            else:
                return {
                    "ok": False,
                    "error": "Analysis returned non-dict",
                    "details": str(analysis_result)
                }
            
            # Store in memory (always works as fallback)
            memory_entry = {
                "session_id": data.session_id,
                "timestamp": int(time.time()),
                "scene": scene,
                "objects": objects,
                "full_result": analysis_result
            }
            memory_store.append(memory_entry)
            print(f"[DEBUG] Stored in memory. Total items: {len(memory_store)}")
            
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
                storage_result["mode"] = "vector_store"
            except Exception as storage_error:
                storage_result = {
                    "mode": "in_memory_only",
                    "warning": "Vector store unavailable, using in-memory fallback",
                    "stored_items": len(memory_store)
                }
            
            return {
                "ok": True,
                "analysis": {
                    "scene": scene,
                    "objects": objects,
                    "full_result": analysis_result
                },
                "storage": storage_result
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/store_text")
async def store_text(data: TextToJSON):
    """Convert text summary to JSON and store in vector database"""
    try:
        # Import vision processor
        import sys
        vision_path = os.path.join(os.path.dirname(__file__), '..', 'vision-processor')
        if vision_path not in sys.path:
            sys.path.insert(0, vision_path)
        
        from vision_reka import text_summary_to_json
        
        # Convert text to JSON
        print(f"[DEBUG] Converting text to JSON: {data.text_summary[:100]}...")
        json_result = text_summary_to_json(data.text_summary)
        print(f"[DEBUG] JSON result: {json_result}")
        
        scene = json_result.get("scene_summary", "Scene captured")
        objects = json_result.get("objects", [])
        
        # Store in memory (always works as fallback)
        memory_entry = {
            "session_id": data.session_id,
            "timestamp": int(time.time()),
            "scene": scene,
            "objects": objects,
            "text_summary": data.text_summary,
            "full_result": json_result
        }
        memory_store.append(memory_entry)
        print(f"[DEBUG] Stored in memory. Total items: {len(memory_store)}")
        
        # Try to store in vector database
        storage_result = None
        try:
            response = await client.post(
                f"{VECTOR_STORE_URL}/add_frame",
                json={
                    "tenant_id": "user_123",
                    "device_id": "text_input",
                    "session_id": data.session_id,
                    "frame_ts": int(time.time()),
                    "scene_summary": scene,
                    "objects": objects
                },
                timeout=5.0
            )
            response.raise_for_status()
            storage_result = response.json()
            storage_result["mode"] = "vector_store"
        except Exception as storage_error:
            storage_result = {
                "mode": "in_memory_only",
                "warning": "Vector store unavailable, using in-memory fallback",
                "stored_items": len(memory_store)
            }
        
        return {
            "ok": True,
            "text_summary": data.text_summary,
            "extracted_json": {
                "scene": scene,
                "objects": objects
            },
            "storage": storage_result
        }
        
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
    """Search memories and return natural language answer"""
    
    # Always use in-memory search with natural language generation
    # This works whether vector store is available or not
    query_lower = query.lower()
    
    # Extract keywords from natural language query
    stop_words = {'where', 'is', 'my', 'the', 'a', 'an', 'what', 'did', 'i', 'was', 'were', 'are', 'have', 'has', 'do', 'does', 's'}
    keywords = [word for word in query_lower.split() if word not in stop_words and len(word) > 2]
    
    # If no keywords extracted, use full query
    if not keywords:
        keywords = [query_lower]
    
    print(f"[DEBUG] Query: '{query}' -> Keywords: {keywords}")
    
    results = []
    
    for entry in memory_store:
        # Semantic keyword matching
        score = 0
        matched_objects = []
        
        # Check each keyword
        for keyword in keywords:
            # Match in scene description
            if keyword in entry["scene"].lower():
                score += 10
            
            # Match in text summary if available
            if "text_summary" in entry and keyword in entry["text_summary"].lower():
                score += 5
            
            # Match in objects
            for obj in entry["objects"]:
                obj_label = obj.get("label", obj.get("name", ""))
                obj_color = obj.get("color", "")
                
                # Match object name
                if keyword in obj_label.lower() or obj_label.lower() in keyword:
                    score += 20
                    if obj_label not in matched_objects:
                        matched_objects.append(obj_label)
                
                # Match color
                if obj_color and keyword in obj_color.lower():
                    score += 15
                    if obj_label not in matched_objects:
                        matched_objects.append(obj_label)
        
        if score > 0:
            results.append({
                "entry": entry,
                "score": score,
                "matched_objects": matched_objects
            })
    
    # Sort by score and get best match
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
    
    # Generate natural language answer
    if not results:
        if memory_store:
            recent = max(memory_store, key=lambda x: x["timestamp"])
            obj_list = [o.get("label", "") for o in recent["objects"]]
            if obj_list:
                answer = f"I couldn't find anything about '{query}', but I recently saw: {', '.join(obj_list)}"
            else:
                answer = f"I couldn't find anything about '{query}' in your memories."
        else:
            answer = "No memories stored yet. Add some text descriptions first!"
    else:
        top = results[0]
        entry = top["entry"]
        
        # Calculate time ago
        seconds_ago = int(time.time()) - entry["timestamp"]
        if seconds_ago < 60:
            time_str = "just now"
        elif seconds_ago < 3600:
            mins = seconds_ago // 60
            time_str = f"{mins} minute{'s' if mins != 1 else ''} ago"
        else:
            hours = seconds_ago // 3600
            time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
        
        # Build contextual answer based on query intent
        if top["matched_objects"]:
            obj_name = top["matched_objects"][0]
            
            # Find the object details
            obj_details = None
            for obj in entry["objects"]:
                if obj.get("label", obj.get("name", "")) == obj_name:
                    obj_details = obj
                    break
            
            # Check query intent
            asking_color = any(word in query_lower for word in ["color", "colour"])
            asking_where = any(word in query_lower for word in ["where", "location"])
            
            if asking_color and obj_details:
                color = obj_details.get("color")
                if color:
                    answer = f"The {obj_name} was {color}."
                else:
                    answer = f"I saw a {obj_name}, but I couldn't determine its color."
            elif asking_where and obj_details:
                location = obj_details.get("rel_pos", "")
                if location and location != "unknown":
                    answer = f"The {obj_name} was {location}, seen {time_str}."
                else:
                    answer = f"I saw a {obj_name} {time_str}."
            else:
                # General query - provide comprehensive info
                details = []
                if obj_details:
                    if obj_details.get("color"):
                        details.append(obj_details["color"])
                    if obj_details.get("rel_pos") and obj_details["rel_pos"] != "unknown":
                        details.append(obj_details["rel_pos"])
                
                if details:
                    detail_str = ", ".join(details)
                    answer = f"I saw a {obj_name} ({detail_str}) {time_str}."
                else:
                    answer = f"I saw a {obj_name} {time_str}."
        else:
            # Scene match
            obj_list = [o.get("label", "") for o in entry["objects"]]
            if obj_list:
                items = ", ".join(obj_list[:3])
                answer = f"{time_str.capitalize()}, I saw: {items}"
            else:
                answer = f"I saw something {time_str}: {entry['scene']}"
    
    return {
        "ok": True,
        "answer": answer,
        "query": query,
        "mode": "in_memory",
        "matches": len(results)
    }


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

