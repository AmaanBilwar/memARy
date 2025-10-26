"""
Simple FastAPI service to store and fetch from vector database
"""
from typing import Union, Optional
import asyncio
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


# --- Helpers: retries and normalization ---
async def post_with_retry(url: str, *, json: dict, retries: int = 3, base_backoff: float = 0.5, timeout: float = 30.0) -> httpx.Response:
    """POST with exponential backoff retries."""
    last_err = None
    for attempt in range(retries):
        try:
            resp = await client.post(url, json=json, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as err:
            last_err = err
            if attempt == retries - 1:
                break
            await asyncio.sleep(base_backoff * (2 ** attempt))
    raise last_err


def normalize_objects(objects_raw: list) -> list:
    """Normalize objects to match vector-store DetectedObject schema."""
    normalized = []
    for obj in objects_raw or []:
        label = obj.get("label") or obj.get("name") or "unknown"
        # confidence -> float, default 0.9
        conf = obj.get("confidence", 0.9)
        try:
            conf = float(conf)
        except Exception:
            conf = 0.9
        # clean fields
        color = obj.get("color")
        if isinstance(color, str) and color.lower() == "null":
            color = None
        rel_pos = obj.get("rel_pos")
        if isinstance(rel_pos, str) and rel_pos.lower() == "null":
            rel_pos = None
        bbox = obj.get("bbox")
        if bbox is not None and isinstance(bbox, list):
            try:
                bbox = [float(x) for x in bbox]
            except Exception:
                bbox = None
        is_person = bool(obj.get("is_person", str(label).lower() in ["person", "people", "human"]))
        relationship_hint = obj.get("relationship_hint")

        normalized.append({
            "label": str(label),
            "confidence": conf,
            "bbox": bbox,
            "color": color,
            "rel_pos": rel_pos,
            "relationship_hint": relationship_hint,
            "is_person": is_person,
        })
    return normalized

# Tracked items storage (in-memory for fast access)
tracked_items = {}  # {item_name: {alert_hours: 24, last_seen: timestamp, notes: ""}}


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


@app.get("/debug/storage")
async def get_storage_info():
    """View storage information (for debugging)"""
    try:
        # Get collection counts from vector store
        collections_info = []
        collections = ["frames_ephemeral_v1", "entities_stream_v1", "latest_entities_v1"]
        
        for coll_name in collections:
            try:
                response = await client.get(
                    f"{VECTOR_STORE_URL}/healthz",
                    timeout=5.0
                )
                collections_info.append({"collection": coll_name, "status": "available"})
            except:
                collections_info.append({"collection": coll_name, "status": "unavailable"})
        
        return {
            "storage_mode": "vector_store_only",
            "vector_store_url": VECTOR_STORE_URL,
            "collections": collections_info,
            "tracked_items_count": len(tracked_items)
        }
    except Exception as e:
        return {
            "storage_mode": "vector_store_only",
            "error": str(e)
        }


@app.get("/memories")
async def get_all_memories(session_id: Optional[str] = None, limit: int = 100):
    """
    Get all memories with entity IDs for each object.
    Queries vector store frames_ephemeral_v1 collection.
    """
    try:
        # Query vector store for frames
        where_clause = {"tenant_id": "user_123"}
        if session_id:
            where_clause["session_id"] = session_id
        
        # Get frames from vector store
        response = await client.post(
            f"{VECTOR_STORE_URL}/search_time_window",
            json={
                "tenant_id": "user_123",
                "start_ts": 0,  # Get all frames
                "end_ts": int(time.time()) + 3600,  # Future timestamp to include all
                "n_results": limit
            },
            timeout=10.0
        )
        response.raise_for_status()
        result = response.json()
        
        # Transform vector store format to API format
        enhanced_memories = []
        for item in result.get("results", []):
            metadata = item.get("metadata", {})
            
            # Parse objects from metadata
            objects = metadata.get("objects", [])
            if isinstance(objects, str):
                import json
                try:
                    objects = json.loads(objects)
                except:
                    objects = []
            
            # Add entity IDs to each object
            enhanced_objects = []
            for obj in objects:
                obj_copy = obj.copy() if isinstance(obj, dict) else {"label": str(obj)}
                item_name = obj_copy.get("label", "unknown")
                session = metadata.get("session_id", "default")
                timestamp = metadata.get("frame_ts", 0)
                
                # New format: tenant:ITEM_NAME:session:timestamp
                obj_copy["entity_id"] = f"user_123:{item_name}:{session}:{timestamp}"
                enhanced_objects.append(obj_copy)
            
            memory_entry = {
                "session_id": metadata.get("session_id", "default"),
                "timestamp": metadata.get("frame_ts", 0),
                "scene": item.get("document", ""),
                "objects": enhanced_objects,
                "frame_id": item.get("id", "")
            }
            enhanced_memories.append(memory_entry)
        
        # Sort by timestamp (newest first)
        enhanced_memories.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        return {
            "ok": True,
            "total": len(enhanced_memories),
            "memories": enhanced_memories,
            "mode": "vector_store"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector store query failed: {str(e)}")


@app.post("/clear_storage")
async def clear_storage():
    """Clear all stored memories from vector store"""
    try:
        # Clear all collections in vector store
        collections = ["frames_ephemeral_v1", "entities_stream_v1", "latest_entities_v1"]
        cleared_collections = []
        
        for collection in collections:
            try:
                response = await client.post(
                    f"{VECTOR_STORE_URL}/clear_collection",
                    json={"collection_name": collection},
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                cleared_collections.append({
                    "collection": collection,
                    "deleted_count": result.get("deleted_count", 0)
                })
            except Exception as e:
                cleared_collections.append({
                    "collection": collection,
                    "error": str(e)
                })
        
        return {
            "ok": True,
            "message": "Vector store cleared successfully",
            "collections": cleared_collections
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
            vision_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vision-processor'))
            if vision_path not in sys.path:
                sys.path.insert(0, vision_path)
            
            print(f"[DEBUG] Importing vision_reka from: {vision_path}")
            print(f"[DEBUG] sys.path: {sys.path[:3]}")
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
            
            # Normalize objects for vector-store schema
            objects = normalize_objects(objects)
            
            # Store in vector database
            try:
                response = await post_with_retry(
                    f"{VECTOR_STORE_URL}/add_frame",
                    json={
                        "tenant_id": "user_123",
                        "device_id": "web_upload",
                        "session_id": data.session_id,
                        "frame_ts": int(time.time()),
                        "scene_summary": scene,
                        "objects": objects,
                    },
                    retries=3,
                    base_backoff=0.75,
                    timeout=30.0,
                )
                storage_result = response.json()
                storage_result["mode"] = "vector_store"
                
                print(f"[DEBUG] Stored in vector store: {storage_result.get('frame_id')}")
                
                return {
                    "ok": True,
                    "analysis": {
                        "scene": scene,
                        "objects": objects,
                        "full_result": analysis_result
                    },
                    "storage": storage_result
                }
            except Exception as storage_error:
                raise HTTPException(
                    status_code=503, 
                    detail=f"Vector store unavailable: {str(storage_error)}"
                )
            
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
        vision_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vision-processor'))
        if vision_path not in sys.path:
            sys.path.insert(0, vision_path)
        
        from vision_reka import text_summary_to_json
        
        # Convert text to JSON
        print(f"[DEBUG] Converting text to JSON: {data.text_summary[:100]}...")
        json_result = text_summary_to_json(data.text_summary)
        print(f"[DEBUG] JSON result: {json_result}")
        
        scene = json_result.get("scene_summary", "Scene captured")
        objects = json_result.get("objects", [])
        
        # Normalize objects for vector-store schema
        objects = normalize_objects(objects)
        
        current_timestamp = int(time.time())
        
        # Update tracked items last_seen timestamps
        for obj in objects:
            obj_label = obj.get("label", obj.get("name", "")).lower()
            if obj_label in tracked_items:
                tracked_items[obj_label]["last_seen"] = current_timestamp
                print(f"[DEBUG] Updated tracked item '{obj_label}' last_seen")
        
        # Store in vector database
        try:
            response = await post_with_retry(
                f"{VECTOR_STORE_URL}/add_frame",
                json={
                    "tenant_id": "user_123",
                    "device_id": "text_input",
                    "session_id": data.session_id,
                    "frame_ts": current_timestamp,
                    "scene_summary": scene,
                    "objects": objects,
                },
                retries=3,
                base_backoff=0.75,
                timeout=30.0,
            )
            storage_result = response.json()
            storage_result["mode"] = "vector_store"
            
            print(f"[DEBUG] Stored in vector store: {storage_result.get('frame_id')}")
            
            return {
                "ok": True,
                "text_summary": data.text_summary,
                "extracted_json": {
                    "scene": scene,
                    "objects": objects
                },
                "storage": storage_result
            }
        except Exception as storage_error:
            raise HTTPException(
                status_code=503,
                detail=f"Vector store unavailable: {str(storage_error)}"
            )
                
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
        # Query vector store
        response = await client.get(
            f"{VECTOR_STORE_URL}/query_by_item/{item_name}",
            params={"tenant_id": "user_123", "limit": limit},
            timeout=10.0
        )
        response.raise_for_status()
        vector_results = response.json()
        
        # If no question, return raw data
        if not question:
            return vector_results
        
        # Answer the question based on item data
        question_lower = question.lower()
        
        # Check if we have results
        if not vector_results.get("results"):
            return {
                "ok": True,
                "item_name": item_name,
                "question": question,
                "answer": f"I haven't seen any {item_name} yet.",
                "confidence": "none"
            }
        
        # Use most recent data from vector store
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
            "total_mentions": vector_results.get("total_mentions", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search_memories(query: str, session_id: Optional[str] = None, limit: int = 5):
    """Search memories using vector store semantic search and return natural language answer"""
    try:
        # Use vector store semantic search across collections
        collections = ["frames_ephemeral_v1", "entities_stream_v1", "latest_entities_v1"]
        
        response = await client.post(
            f"{VECTOR_STORE_URL}/search_semantic",
            json={
                "tenant_id": "user_123",
                "query_text": query,
                "collections": collections,
                "n_results": limit
            },
            timeout=10.0
        )
        response.raise_for_status()
        result = response.json()
        
        results = result.get("results", [])
        
        # Generate natural language answer
        if not results:
            answer = f"I couldn't find anything about '{query}' in your memories."
        else:
            # Use the top result
            top = results[0]
            metadata = top.get("metadata", {})
            document = top.get("document", "")
            
            # Extract timestamp
            timestamp = metadata.get("frame_ts") or metadata.get("last_frame_ts", 0)
            
            # Calculate time ago
            seconds_ago = int(time.time()) - timestamp if timestamp else 0
            if seconds_ago < 60:
                time_str = "just now"
            elif seconds_ago < 3600:
                mins = seconds_ago // 60
                time_str = f"{mins} minute{'s' if mins != 1 else ''} ago"
            else:
                hours = seconds_ago // 3600
                time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
            
            # Build answer based on collection type
            collection = top.get("collection", "")
            query_lower = query.lower()
            
            if collection == "latest_entities_v1":
                # This is a "last seen" result
                answer = f"{document} ({time_str})"
            elif collection == "entities_stream_v1":
                # This is a specific object mention
                obj_label = metadata.get("obj_label", "")
                if obj_label:
                    answer = f"I saw {obj_label} {time_str}. {document}"
                else:
                    answer = f"{document} ({time_str})"
            else:
                # Frame/scene result
                answer = f"{time_str.capitalize()}: {document}"
        
        # Check for tracked items in query
        tracked_info = None
        query_lower = query.lower()
        for item_name, item_data in tracked_items.items():
            if item_name in query_lower:
                last_seen = item_data["last_seen"]
                alert_hours = item_data["alert_hours"]
                
                if last_seen:
                    hours_since = (int(time.time()) - last_seen) / 3600
                    if hours_since >= alert_hours:
                        tracked_info = {
                            "item": item_name,
                            "status": "alert",
                            "message": f"⚠️ Haven't seen your {item_name} in {round(hours_since, 1)} hours (alert threshold: {alert_hours}h)",
                            "hours_since_seen": round(hours_since, 1)
                        }
                else:
                    tracked_info = {
                        "item": item_name,
                        "status": "never_seen",
                        "message": f"📌 {item_name.capitalize()} is being tracked, but hasn't been seen yet"
                    }
                break
        
        return {
            "ok": True,
            "answer": answer,
            "query": query,
            "mode": "vector_store",
            "matches": len(results),
            "tracked_item": tracked_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/statistics")
async def get_statistics():
    """Get comprehensive statistics about stored memories from vector store"""
    from collections import Counter
    from datetime import datetime
    
    try:
        # Query all frames from vector store
        response = await client.post(
            f"{VECTOR_STORE_URL}/search_time_window",
            json={
                "tenant_id": "user_123",
                "start_ts": 0,
                "end_ts": int(time.time()) + 3600,
                "n_results": 1000  # Get a large batch for statistics
            },
            timeout=15.0
        )
        response.raise_for_status()
        result = response.json()
        
        frames = result.get("results", [])
        
        if not frames:
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
                    "mode": "vector_store",
                    "message": "No memories stored yet"
                }
            }
    
        # Basic stats
        total_memories = len(frames)
        
        # Object analysis
        import json as json_lib
        all_objects = []
        object_colors = {}
        
        for frame in frames:
            metadata = frame.get("metadata", {})
            objects = metadata.get("objects", [])
            
            # Parse objects if they're stored as JSON string
            if isinstance(objects, str):
                try:
                    objects = json_lib.loads(objects)
                except:
                    objects = []
            
            for obj in objects:
                if not isinstance(obj, dict):
                    continue
                label = obj.get("label", "unknown")
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
        for frame in frames:
            metadata = frame.get("metadata", {})
            sid = metadata.get("session_id", "unknown")
            timestamp = metadata.get("frame_ts", 0)
            
            objects = metadata.get("objects", [])
            if isinstance(objects, str):
                try:
                    objects = json_lib.loads(objects)
                except:
                    objects = []
            
            if sid not in session_data:
                session_data[sid] = {
                    "count": 0,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "objects": []
                }
            session_data[sid]["count"] += 1
            session_data[sid]["last_seen"] = max(session_data[sid]["last_seen"], timestamp)
            session_data[sid]["first_seen"] = min(session_data[sid]["first_seen"], timestamp)
            session_data[sid]["objects"].extend([o.get("label", "") for o in objects if isinstance(o, dict)])
        
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
        for frame in frames:
            metadata = frame.get("metadata", {})
            ts = metadata.get("frame_ts", 0)
            
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
            "mode": "vector_store",
            "total_memories": total_memories
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/track_item")
async def track_item(data: TrackItem):
    """Add an item to the tracked items list"""
    item_name = data.item_name.lower()
    
    # Initialize or update tracked item
    tracked_items[item_name] = {
        "alert_hours": data.alert_hours,
        "last_seen": None,  # Will be updated when item is seen
        "notes": data.notes,
        "tracked_since": int(time.time())
    }
    
    # Check if we've seen this item before by querying vector store
    try:
        response = await client.get(
            f"{VECTOR_STORE_URL}/query_by_item/{item_name}",
            params={"tenant_id": "user_123", "limit": 1},
            timeout=5.0
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("results"):
                # Get most recent mention
                latest = result["results"][0]
                metadata = latest.get("metadata", {})
                last_ts = metadata.get("frame_ts", 0)
                if last_ts:
                    tracked_items[item_name]["last_seen"] = last_ts
    except:
        # If vector store is unavailable, just track with no last_seen
        pass
    
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
async def get_relationships(item: Optional[str] = None):
    """Get object relationships - which items are often seen together"""
    try:
        from collections import Counter, defaultdict
        import json as json_lib
        
        # Query all frames from vector store to compute relationships
        response = await client.post(
            f"{VECTOR_STORE_URL}/search_time_window",
            json={
                "tenant_id": "user_123",
                "start_ts": 0,
                "end_ts": int(time.time()) + 3600,
                "n_results": 500  # Get recent frames for relationship analysis
            },
            timeout=10.0
        )
        response.raise_for_status()
        result = response.json()
        
        frames = result.get("results", [])
        
        # Compute relationships from frames
        relationships_data = defaultdict(lambda: defaultdict(int))
        
        for frame in frames:
            metadata = frame.get("metadata", {})
            objects = metadata.get("objects", [])
            
            # Parse objects if they're stored as JSON string
            if isinstance(objects, str):
                try:
                    objects = json_lib.loads(objects)
                except:
                    objects = []
            
            # Get labels from objects
            labels = [obj.get("label", "").lower() for obj in objects if isinstance(obj, dict) and obj.get("label")]
            
            # Count co-occurrences
            for i, label1 in enumerate(labels):
                for label2 in labels[i+1:]:
                    if label1 and label2:
                        relationships_data[label1][label2] += 1
                        relationships_data[label2][label1] += 1
        
        if item:
            # Get relationships for a specific item
            item = item.lower()
            if item not in relationships_data:
                return {
                    "ok": True,
                    "item": item,
                    "relationships": [],
                    "message": f"No relationships found for '{item}'"
                }
            
            # Sort by frequency
            relationships = [
                {"item": related_item, "count": count}
                for related_item, count in relationships_data[item].items()
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
            seen_pairs = set()
            
            for item1, related_items in relationships_data.items():
                for item2, count in related_items.items():
                    # Avoid duplicates (A->B and B->A)
                    pair = tuple(sorted([item1, item2]))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        all_relationships.append({
                            "item1": pair[0],
                            "item2": pair[1],
                            "count": count
                        })
            
            # Sort by frequency
            all_relationships.sort(key=lambda x: x["count"], reverse=True)
            
            return {
                "ok": True,
                "relationships": all_relationships[:20],  # Top 20
                "total": len(all_relationships)
            }
    
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

