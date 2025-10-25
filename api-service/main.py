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

# Tracked items storage
tracked_items = {}  # {item_name: {alert_hours: 24, last_seen: timestamp, notes: ""}}

# Object relationships storage
object_relationships = {}  # {obj1: {obj2: count, obj3: count}}


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


class TrackItem(BaseModel):
    item_name: str
    alert_hours: Optional[int] = 24
    notes: Optional[str] = ""


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
    """
    Get all memories with entity IDs for each object.
    Now shows item-based IDs: tenant:ITEM_NAME:session:timestamp
    """
    # Filter by session if specified
    if session_id:
        filtered = [m for m in memory_store if m.get("session_id") == session_id]
    else:
        filtered = memory_store
    
    # Sort by timestamp (newest first)
    sorted_memories = sorted(filtered, key=lambda x: x.get("timestamp", 0), reverse=True)
    
    # Limit results
    limited = sorted_memories[:limit]
    
    # Add entity IDs to each object
    enhanced_memories = []
    for memory in limited:
        memory_copy = memory.copy()
        
        # Generate entity IDs for each object (item-name based format)
        if "objects" in memory_copy:
            enhanced_objects = []
            for obj in memory_copy["objects"]:
                obj_copy = obj.copy()
                item_name = obj.get("label", "unknown")
                session = memory_copy.get("session_id", "default")
                timestamp = memory_copy.get("timestamp", int(time.time()))
                
                # New format: tenant:ITEM_NAME:session:timestamp
                obj_copy["entity_id"] = f"user_123:{item_name}:{session}:{timestamp}"
                enhanced_objects.append(obj_copy)
            
            memory_copy["objects"] = enhanced_objects
        
        # Add frame ID for reference
        memory_copy["frame_id"] = f"user_123:{memory_copy.get('session_id', 'default')}:{memory_copy.get('timestamp', 0)}"
        
        enhanced_memories.append(memory_copy)
    
    return {
        "ok": True,
        "total": len(enhanced_memories),
        "memories": enhanced_memories
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
        current_timestamp = int(time.time())
        memory_entry = {
            "session_id": data.session_id,
            "timestamp": current_timestamp,
            "scene": scene,
            "objects": objects,
            "text_summary": data.text_summary,
            "full_result": json_result
        }
        memory_store.append(memory_entry)
        print(f"[DEBUG] Stored in memory. Total items: {len(memory_store)}")
        
        # Update tracked items last_seen timestamps
        for obj in objects:
            obj_label = obj.get("label", obj.get("name", "")).lower()
            if obj_label in tracked_items:
                tracked_items[obj_label]["last_seen"] = current_timestamp
                print(f"[DEBUG] Updated tracked item '{obj_label}' last_seen")
        
        # Update object relationships (objects seen together)
        if len(objects) > 1:
            for i, obj1 in enumerate(objects):
                label1 = obj1.get("label", obj1.get("name", "")).lower()
                if not label1:
                    continue
                if label1 not in object_relationships:
                    object_relationships[label1] = {}
                
                for j, obj2 in enumerate(objects):
                    if i == j:
                        continue
                    label2 = obj2.get("label", obj2.get("name", "")).lower()
                    if not label2:
                        continue
                    
                    if label2 not in object_relationships[label1]:
                        object_relationships[label1][label2] = 0
                    object_relationships[label1][label2] += 1
            print(f"[DEBUG] Updated object relationships")
        
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


@app.get("/item/{item_name}")
async def query_item_history(item_name: str, limit: int = 10, question: Optional[str] = None):
    """
    Get all mentions/history of a specific item by name.
    Uses new ID format: tenant:label:session:timestamp
    
    If 'question' parameter is provided, returns a natural language answer.
    Examples:
      /item/floor?question=what color is it
      /item/key?question=where is it
    """
    try:
        # First try vector store
        vector_results = None
        try:
            response = await client.get(
                f"{VECTOR_STORE_URL}/query_by_item/{item_name}",
                params={"tenant_id": "user_123", "limit": limit},
                timeout=5.0
            )
            response.raise_for_status()
            vector_results = response.json()
        except:
            pass
        
        # Fallback to in-memory search
        matches = []
        for entry in memory_store:
            for obj in entry.get("objects", []):
                obj_label = obj.get("label", obj.get("name", "")).lower()
                if obj_label == item_name.lower():
                    matches.append({
                        "timestamp": entry.get("timestamp"),
                        "session": entry.get("session_id"),
                        "scene": entry.get("scene"),
                        "object": obj
                    })
        
        matches.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        # If no question, return raw data
        if not question:
            if vector_results:
                return vector_results
            return {
                "ok": True,
                "item_name": item_name,
                "total_mentions": len(matches),
                "results": matches[:limit],
                "mode": "in_memory_fallback"
            }
        
        # Answer the question based on item data
        question_lower = question.lower()
        
        # Get most recent mention
        if not matches and not (vector_results and vector_results.get("results")):
            return {
                "ok": True,
                "item_name": item_name,
                "question": question,
                "answer": f"I haven't seen any {item_name} yet.",
                "confidence": "none"
            }
        
        # Use most recent data
        if matches:
            latest = matches[0]
            obj = latest["object"]
        elif vector_results and vector_results.get("results"):
            latest = vector_results["results"][0]
            obj = latest.get("metadata", {})
        
        # Answer different types of questions
        answer = None
        confidence = "high"
        
        if "color" in question_lower or "what color" in question_lower:
            color = obj.get("color") or obj.get("obj_attrs", {}).get("color")
            if color and color != "null":
                answer = f"The {item_name} is {color}."
            else:
                answer = f"I didn't record the color of the {item_name}."
                confidence = "low"
        
        elif "where" in question_lower or "location" in question_lower:
            rel_pos = obj.get("rel_pos") or obj.get("obj_attrs", {}).get("rel_pos")
            if rel_pos and rel_pos != "null":
                answer = f"The {item_name} is {rel_pos}."
            else:
                answer = f"I saw the {item_name} but didn't record its location."
                confidence = "low"
        
        elif "when" in question_lower or "time" in question_lower:
            timestamp = latest.get("timestamp") or obj.get("frame_ts")
            if timestamp:
                import datetime
                dt = datetime.datetime.fromtimestamp(timestamp)
                time_ago = int(time.time()) - timestamp
                if time_ago < 60:
                    time_str = "just now"
                elif time_ago < 3600:
                    time_str = f"{time_ago // 60} minutes ago"
                elif time_ago < 86400:
                    time_str = f"{time_ago // 3600} hours ago"
                else:
                    time_str = f"{time_ago // 86400} days ago"
                answer = f"I saw the {item_name} {time_str}."
            else:
                answer = f"I'm not sure when I saw the {item_name}."
                confidence = "low"
        
        else:
            # General question - provide all available info
            details = []
            color = obj.get("color") or obj.get("obj_attrs", {}).get("color")
            rel_pos = obj.get("rel_pos") or obj.get("obj_attrs", {}).get("rel_pos")
            
            if color and color != "null":
                details.append(f"color: {color}")
            if rel_pos and rel_pos != "null":
                details.append(f"location: {rel_pos}")
            
            if details:
                answer = f"The {item_name} - {', '.join(details)}."
            else:
                answer = f"I saw the {item_name} but don't have detailed information."
                confidence = "low"
        
        return {
            "ok": True,
            "item_name": item_name,
            "question": question,
            "answer": answer,
            "confidence": confidence,
            "total_mentions": len(matches) if matches else vector_results.get("total_mentions", 0)
        }
        
    except Exception as e:
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
        
    # Check for tracked items in query
    tracked_info = None
    relationships_info = []
    
    for keyword in keywords:
        # Check if this is a tracked item
        if keyword in tracked_items:
            item_data = tracked_items[keyword]
            last_seen = item_data["last_seen"]
            alert_hours = item_data["alert_hours"]
            
            if last_seen:
                hours_since = (int(time.time()) - last_seen) / 3600
                if hours_since >= alert_hours:
                    tracked_info = {
                        "item": keyword,
                        "status": "alert",
                        "message": f"⚠️ Haven't seen your {keyword} in {round(hours_since, 1)} hours (alert threshold: {alert_hours}h)",
                        "hours_since_seen": round(hours_since, 1)
                    }
            else:
                tracked_info = {
                    "item": keyword,
                    "status": "never_seen",
                    "message": f"📌 {keyword.capitalize()} is being tracked, but hasn't been seen yet"
                }
        
        # Check for related items
        if keyword in object_relationships and object_relationships[keyword]:
            related = sorted(object_relationships[keyword].items(), key=lambda x: x[1], reverse=True)[:3]
            if related:
                relationships_info.append({
                    "item": keyword,
                    "related_items": [{"item": r[0], "count": r[1]} for r in related],
                    "message": f"💡 {keyword.capitalize()} is often seen with: {', '.join([r[0] for r in related])}"
                })
    
    return {
        "ok": True,
        "answer": answer,
        "query": query,
        "mode": "in_memory",
        "matches": len(results),
        "tracked_item": tracked_info,
        "relationships": relationships_info
    }


@app.get("/statistics")
def get_statistics():
    """Get comprehensive statistics about stored memories"""
    from collections import Counter
    from datetime import datetime, timedelta
    
    if not memory_store:
        return {
            "ok": True,
            "total_memories": 0,
            "total_objects": 0,
            "unique_objects": 0,
            "sessions": 0,
            "most_common_objects": [],
            "session_stats": [],
            "timeline_data": [],
            "storage_info": {
                "mode": "empty",
                "message": "No memories stored yet"
            }
        }
    
    # Basic stats
    total_memories = len(memory_store)
    
    # Object analysis
    all_objects = []
    object_colors = {}
    for entry in memory_store:
        for obj in entry.get("objects", []):
            label = obj.get("label", obj.get("name", "unknown"))
            all_objects.append(label)
            
            # Track colors for each object type
            if label not in object_colors:
                object_colors[label] = []
            color = obj.get("color")
            if color:
                object_colors[label].append(color)
    
    total_objects = len(all_objects)
    unique_objects = len(set(all_objects))
    
    # Most common objects with their colors
    object_counter = Counter(all_objects)
    most_common = []
    for obj, count in object_counter.most_common(10):
        colors = object_colors.get(obj, [])
        color_counts = Counter(colors)
        most_common.append({
            "object": obj,
            "count": count,
            "percentage": round((count / total_objects) * 100, 1) if total_objects > 0 else 0,
            "common_colors": [{"color": c, "count": cnt} for c, cnt in color_counts.most_common(3)]
        })
    
    # Session analysis
    session_data = {}
    for entry in memory_store:
        sid = entry.get("session_id", "unknown")
        if sid not in session_data:
            session_data[sid] = {
                "count": 0,
                "first_seen": entry["timestamp"],
                "last_seen": entry["timestamp"],
                "objects": []
            }
        session_data[sid]["count"] += 1
        session_data[sid]["last_seen"] = max(session_data[sid]["last_seen"], entry["timestamp"])
        session_data[sid]["first_seen"] = min(session_data[sid]["first_seen"], entry["timestamp"])
        session_data[sid]["objects"].extend([o.get("label", o.get("name", "")) for o in entry.get("objects", [])])
    
    session_stats = []
    for sid, data in session_data.items():
        duration = data["last_seen"] - data["first_seen"]
        session_stats.append({
            "session_id": sid,
            "memory_count": data["count"],
            "duration_seconds": duration,
            "unique_objects": len(set(data["objects"])),
            "last_active": data["last_seen"]
        })
    
    # Sort by memory count
    session_stats = sorted(session_stats, key=lambda x: x["memory_count"], reverse=True)
    
    # Timeline data - group by day/hour
    now = int(time.time())
    timeline = []
    
    # Create time buckets (last 7 days by day, then by hour for today)
    today_start = now - (now % 86400)  # Start of today
    
    # Group memories by time period
    time_groups = {}
    for entry in memory_store:
        ts = entry["timestamp"]
        
        # Determine bucket
        if ts >= today_start:
            # Today - hourly buckets
            hour_bucket = ts - (ts % 3600)
            bucket_label = datetime.fromtimestamp(hour_bucket).strftime("%H:%M")
            bucket_type = "hour"
        elif ts >= today_start - 86400:
            # Yesterday
            bucket_label = "Yesterday"
            hour_bucket = today_start - 86400
            bucket_type = "day"
        elif ts >= today_start - (7 * 86400):
            # Last 7 days
            day_bucket = ts - (ts % 86400)
            bucket_label = datetime.fromtimestamp(day_bucket).strftime("%a, %b %d")
            hour_bucket = day_bucket
            bucket_type = "day"
        else:
            # Older - weekly buckets
            week_bucket = ts - (ts % (7 * 86400))
            bucket_label = datetime.fromtimestamp(week_bucket).strftime("Week of %b %d")
            hour_bucket = week_bucket
            bucket_type = "week"
        
        if hour_bucket not in time_groups:
            time_groups[hour_bucket] = {
                "timestamp": hour_bucket,
                "label": bucket_label,
                "count": 0,
                "type": bucket_type
            }
        time_groups[hour_bucket]["count"] += 1
    
    # Convert to sorted list
    timeline = sorted(time_groups.values(), key=lambda x: x["timestamp"])
    
    # Storage info
    storage_info = {
        "mode": "in_memory",
        "total_memories": total_memories,
        "estimated_size_kb": round(len(str(memory_store)) / 1024, 2)
    }
    
    return {
        "ok": True,
        "total_memories": total_memories,
        "total_objects": total_objects,
        "unique_objects": unique_objects,
        "sessions": len(session_data),
        "most_common_objects": most_common,
        "session_stats": session_stats[:5],  # Top 5 sessions
        "timeline_data": timeline,
        "storage_info": storage_info
    }


@app.post("/track_item")
def track_item(data: TrackItem):
    """Add an item to the tracked items list"""
    item_name = data.item_name.lower()
    
    # Initialize or update tracked item
    tracked_items[item_name] = {
        "alert_hours": data.alert_hours,
        "last_seen": None,  # Will be updated when item is seen
        "notes": data.notes,
        "tracked_since": int(time.time())
    }
    
    # Check if we've seen this item before
    for memory in memory_store:
        for obj in memory.get("objects", []):
            obj_label = obj.get("label", obj.get("name", "")).lower()
            if obj_label == item_name:
                if tracked_items[item_name]["last_seen"] is None or memory["timestamp"] > tracked_items[item_name]["last_seen"]:
                    tracked_items[item_name]["last_seen"] = memory["timestamp"]
    
    return {
        "ok": True,
        "message": f"Now tracking '{data.item_name}'",
        "item": {
            "name": item_name,
            **tracked_items[item_name]
        }
    }


@app.delete("/track_item/{item_name}")
def untrack_item(item_name: str):
    """Remove an item from the tracked items list"""
    item_name = item_name.lower()
    
    if item_name in tracked_items:
        del tracked_items[item_name]
        return {
            "ok": True,
            "message": f"Stopped tracking '{item_name}'"
        }
    else:
        raise HTTPException(status_code=404, detail=f"Item '{item_name}' is not being tracked")


@app.get("/tracked_items")
def get_tracked_items():
    """Get all tracked items and their status"""
    now = int(time.time())
    items_with_alerts = []
    
    for item_name, item_data in tracked_items.items():
        last_seen = item_data["last_seen"]
        alert_hours = item_data["alert_hours"]
        
        status = "never_seen"
        hours_since_seen = None
        needs_alert = False
        
        if last_seen is not None:
            hours_since_seen = (now - last_seen) / 3600
            if hours_since_seen < alert_hours:
                status = "ok"
            else:
                status = "alert"
                needs_alert = True
        
        items_with_alerts.append({
            "name": item_name,
            "last_seen": last_seen,
            "hours_since_seen": round(hours_since_seen, 1) if hours_since_seen else None,
            "alert_hours": alert_hours,
            "status": status,
            "needs_alert": needs_alert,
            "notes": item_data.get("notes", ""),
            "tracked_since": item_data.get("tracked_since")
        })
    
    # Sort by status (alerts first)
    items_with_alerts.sort(key=lambda x: (0 if x["needs_alert"] else 1, x["name"]))
    
    return {
        "ok": True,
        "tracked_items": items_with_alerts,
        "alerts_count": sum(1 for item in items_with_alerts if item["needs_alert"])
    }


@app.get("/relationships")
def get_relationships(item: Optional[str] = None):
    """Get object relationships - which items are often seen together"""
    
    if item:
        # Get relationships for a specific item
        item = item.lower()
        if item not in object_relationships:
            return {
                "ok": True,
                "item": item,
                "relationships": [],
                "message": f"No relationships found for '{item}'"
            }
        
        # Sort by frequency
        relationships = [
            {"item": related_item, "count": count}
            for related_item, count in object_relationships[item].items()
        ]
        relationships.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "ok": True,
            "item": item,
            "relationships": relationships
        }
    else:
        # Get all relationships
        all_relationships = []
        for item1, related_items in object_relationships.items():
            for item2, count in related_items.items():
                # Avoid duplicates (A->B and B->A)
                if item1 < item2:
                    all_relationships.append({
                        "item1": item1,
                        "item2": item2,
                        "count": count
                    })
        
        # Sort by frequency
        all_relationships.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "ok": True,
            "relationships": all_relationships[:20],  # Top 20
            "total": len(all_relationships)
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

