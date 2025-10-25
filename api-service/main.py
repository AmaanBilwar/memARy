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
    try:
        response = await client.post(
            f"{VECTOR_STORE_URL}/search_semantic",
            json={
                "tenant_id": "user_123",
                "query_text": query,
                "collections": ["entities_stream_v1", "user_notes_v1", "frames_ephemeral_v1"],
                "n_results": limit
            },
            timeout=5.0
        )
        response.raise_for_status()
        result = response.json()
        # TODO: Generate natural language from vector store results
        return {
            "ok": True,
            "answer": "Vector store integration pending",
            "mode": "vector_store"
        }
    except httpx.ConnectError:
        # Fallback to in-memory search with natural language response
        query_lower = query.lower()
        
        # Extract keywords from natural language query
        # Remove common words and extract meaningful terms
        stop_words = {'where', 'is', 'my', 'the', 'a', 'an', 'what', 'did', 'i', 'was', 'were', 'are', 'have', 'has', 'do', 'does'}
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
                
                # Match in objects
                for obj in entry["objects"]:
                    obj_label = obj.get("label", obj.get("name", ""))
                    if keyword in obj_label.lower() or obj_label.lower() in keyword:
                        score += 20
                        if obj_label not in matched_objects:
                            matched_objects.append(obj_label)
                    
                    # Match in attributes
                    for attr in obj.get("attributes", []):
                        if keyword in attr.lower():
                            score += 5
            
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
            # If no keyword matches, show most recent memory for general queries
            general_queries = ['everything', 'anything', 'recent', 'latest', 'last', 'see', 'saw', 'seen', 'show']
            is_general = any(word in query_lower for word in general_queries) or not keywords
            
            if is_general and memory_store:
                # Show most recent memory
                recent = max(memory_store, key=lambda x: x["timestamp"])
                obj_list = [o.get("label", o.get("name", "")) for o in recent["objects"]]
                
                seconds_ago = int(time.time()) - recent["timestamp"]
                if seconds_ago < 60:
                    time_str = "just now"
                else:
                    mins = seconds_ago // 60
                    time_str = f"{mins} minute{'s' if mins != 1 else ''} ago"
                
                if len(obj_list) > 2:
                    items = f"{obj_list[0]}, {obj_list[1]}, and {obj_list[2]}"
                elif len(obj_list) == 2:
                    items = f"{obj_list[0]} and {obj_list[1]}"
                else:
                    items = obj_list[0] if obj_list else "items"
                
                answer = f"Most recently, {time_str}, I saw {items}: {recent['scene'].lower()}"
            else:
                answer = f"I couldn't find anything about '{query}' in your memories."
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
            elif seconds_ago < 86400:
                hours = seconds_ago // 3600
                time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = seconds_ago // 86400
                time_str = f"{days} day{'s' if days != 1 else ''} ago"
            
            # Build contextual answer
            if top["matched_objects"]:
                # Direct object match - check what user is asking about
                obj_name = top["matched_objects"][0]
                
                # Find the object details
                obj_details = None
                for obj in entry["objects"]:
                    if obj.get("label", obj.get("name", "")) == obj_name:
                        obj_details = obj
                        break
                
                # Check if query is about specific attributes
                query_intent = None
                if "color" in query_lower or "colour" in query_lower:
                    query_intent = "color"
                elif "where" in query_lower or "location" in query_lower:
                    query_intent = "location"
                
                # Build answer based on intent
                if query_intent == "color" and obj_details:
                    color = obj_details.get("color")
                    if color:
                        answer = f"Your {obj_name} was {color}."
                    else:
                        answer = f"I saw your {obj_name}, but I couldn't determine its color."
                elif query_intent == "location" or "where" in query_lower:
                    other_objs = [o.get("label", o.get("name", "")) 
                                 for o in entry["objects"] 
                                 if o.get("label", o.get("name", "")) != obj_name]
                    
                    location = obj_details.get("rel_pos", "") if obj_details else ""
                    
                    if location and location != "unknown":
                        answer = f"Your {obj_name} was {location}, {time_str}."
                    elif other_objs:
                        context = f"near {other_objs[0]}"
                        if len(other_objs) > 1:
                            context += f" and {other_objs[1]}"
                        answer = f"Your {obj_name} was {context}, {time_str}."
                    else:
                        answer = f"I saw your {obj_name} {time_str}."
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
                        answer = f"I saw your {obj_name} ({detail_str}) {time_str}."
                    else:
                        answer = f"I saw your {obj_name} {time_str}."
            else:
                # Scene match - general query
                obj_list = [o.get("label", o.get("name", "")) for o in entry["objects"]]
                if len(obj_list) > 2:
                    items = f"{obj_list[0]}, {obj_list[1]}, and {obj_list[2]}"
                elif len(obj_list) == 2:
                    items = f"{obj_list[0]} and {obj_list[1]}"
                elif len(obj_list) == 1:
                    items = obj_list[0]
                else:
                    items = "items"
                
                answer = f"{time_str.capitalize()}, I saw {items} - {entry['scene'].lower()}"
        
        return {
            "ok": True,
            "answer": answer,
            "query": query,
            "mode": "in_memory_fallback",
            "raw_results": results if results else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


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

