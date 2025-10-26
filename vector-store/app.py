"""
FastAPI service implementing 5-tier ChromaDB memory architecture
with devil's-advocate safeguards for AR glasses workflow.
"""
import os
import sys

# === SUPPRESS CHROMADB TELEMETRY ERRORS ===
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"

# Filter stderr to hide telemetry error messages
import io
class _TelemetryFilter(io.TextIOBase):
    def __init__(self, original):
        self.original = original
    def write(self, msg):
        if msg and not any(x in str(msg) for x in ['telemetry', 'posthog', 'capture()']):
            return self.original.write(msg)
        return len(msg)
    def flush(self):
        return self.original.flush()

sys.stderr = _TelemetryFilter(sys.stderr)
# === END TELEMETRY SUPPRESSION ===

import time
import hashlib
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from chroma_client import (
    get_or_create_collection, init_collections,
    COLL_FRAMES, COLL_ENTITIES, COLL_LATEST, COLL_NOTES, COLL_LTM
)
from embeddings import embed_texts, EMB_MODEL_VER, SCENE_MODEL_VER, DET_MODEL_VER
from schema import (
    FrameIngestRequest, NoteIngestRequest, SearchLastSeenRequest,
    SearchSemanticRequest, SearchTimeWindowRequest, CurateToLTMRequest,
    CompactRequest, CONFIDENCE_THRESHOLD, TRACKED_OBJECTS
)

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize collections on startup"""
    init_collections()
    yield

app = FastAPI(
    title="AR Glasses Vector Memory Store",
    version="1.0.0",
    description="5-tier ChromaDB architecture with safeguards",
    lifespan=lifespan
)

# --- Helper Functions ---

def _id_frame(tenant: str, session: str, ts: int) -> str:
    """Time-sortable frame ID"""
    return f"{tenant}:{session}:{ts}"

def _id_entity(tenant: str, session: str, ts: int, label: str, idx: int) -> str:
    """Entity ID - using item name as primary key for easy querying"""
    # Format: tenant:label:session:timestamp
    # This allows querying by label easily
    return f"{tenant}:{label}:{session}:{ts}"

def _id_latest(tenant: str, canonical_key: str) -> str:
    """Latest entity ID - using item name as key"""
    return f"{tenant}:{canonical_key}"

def _id_note(tenant: str, note_id: str) -> str:
    """Note ID"""
    return f"{tenant}:note:{note_id}"

def _id_ltm(tenant: str, origin_id: str) -> str:
    """LTM ID based on hash of origin"""
    hash_suffix = hashlib.md5(origin_id.encode()).hexdigest()[:8]
    return f"{tenant}:ltm:{hash_suffix}"

def _assign_role(person_idx: int, hint: str = None) -> str:
    """Privacy safeguard: no biometric data, only ephemeral roles"""
    base = f"person_{person_idx}"
    return f"{base} ({hint})" if hint else base

def _clean_metadata(meta: dict) -> dict:
    """
    Clean metadata for ChromaDB - only str, int, float, bool allowed.
    Convert lists to JSON strings, remove None values.
    """
    cleaned = {}
    for k, v in meta.items():
        if v is None:
            continue  # Skip None values
        elif isinstance(v, (list, dict)):
            cleaned[k] = json.dumps(v)  # Serialize complex types
        elif isinstance(v, (str, int, float, bool)):
            cleaned[k] = v
        else:
            cleaned[k] = str(v)  # Convert other types to string
    return cleaned

# --- API Endpoints ---

@app.post("/add_frame")
async def add_frame(req: FrameIngestRequest):
    """
    Ingest a frame captured every ~5 seconds.
    
    Stores in 3 places:
    1. frames_ephemeral_v1 - full scene summary (TTL: 24-72h)
    2. entities_stream_v1 - per-object mentions
    3. latest_entities_v1 - upsert for tracked objects (if confidence ≥ threshold)
    
    Safeguards:
    - Only upsert to latest if object in TRACKED_OBJECTS and confidence ≥ CONFIDENCE_THRESHOLD
    - Record model versions for drift tracking
    - Privacy: no biometric data for people
    """
    try:
        # --- 1) Add to frames_ephemeral_v1 ---
        frames = get_or_create_collection(COLL_FRAMES)
        frame_id = _id_frame(req.tenant_id, req.session_id, req.frame_ts)
        
        scene_text = req.scene_summary.strip()
        scene_vec = embed_texts([scene_text])[0]
        
        # Build objects metadata
        objs_meta = []
        has_keys = False
        has_pills = False
        person_count = 0
        
        for obj in req.objects:
            entry = {
                "label": obj.label,
                "confidence": obj.confidence,
                "bbox": obj.bbox,
                "color": obj.color,
                "rel_pos": obj.rel_pos,
            }
            if obj.is_person:
                person_count += 1
                entry["role"] = _assign_role(person_count, obj.relationship_hint)
            if obj.label == "keys":
                has_keys = True
            if obj.label in {"pill_bottle", "pills", "medication"}:
                has_pills = True
            objs_meta.append(entry)
        
        frame_meta = {
            "tenant_id": req.tenant_id,
            "device_id": req.device_id,
            "session_id": req.session_id,
            "frame_ts": req.frame_ts,
            "tz": req.tz,
            "lat_lon_hash": req.lat_lon_hash,
            "objects": objs_meta,
            "has_keys": has_keys,
            "has_pills": has_pills,
            "model_scene_ver": SCENE_MODEL_VER,
            "emb_model_ver": EMB_MODEL_VER,
        }
        
        frames.add(
            ids=[frame_id],
            documents=[scene_text],
            embeddings=[scene_vec],
            metadatas=[_clean_metadata(frame_meta)]
        )
        
        # --- 2) Add to entities_stream_v1 ---
        entities = get_or_create_collection(COLL_ENTITIES)
        ent_ids, ent_docs, ent_vecs, ent_metas = [], [], [], []
        
        for idx, obj in enumerate(req.objects):
            ent_id = _id_entity(req.tenant_id, req.session_id, req.frame_ts, obj.label, idx)
            
            # Canonical object string
            parts = [obj.label]
            if obj.color:
                parts.append(obj.color)
            if obj.rel_pos:
                parts.append(obj.rel_pos)
            doc = " | ".join(parts)
            
            ent_ids.append(ent_id)
            ent_docs.append(doc)
            
            meta = {
                "tenant_id": req.tenant_id,
                "device_id": req.device_id,
                "session_id": req.session_id,
                "frame_ts": req.frame_ts,
                "obj_label": obj.label,
                "obj_attrs": {"color": obj.color, "rel_pos": obj.rel_pos},
                "bbox": obj.bbox,
                "scene_anchor": None,  # Could extract from scene_summary
                "confidence": obj.confidence,
                "model_det_ver": DET_MODEL_VER,
                "emb_model_ver": EMB_MODEL_VER,
            }
            ent_metas.append(meta)
        
        if ent_docs:
            ent_vecs = embed_texts(ent_docs)
            entities.add(
                ids=ent_ids,
                documents=ent_docs,
                embeddings=ent_vecs,
                metadatas=[_clean_metadata(m) for m in ent_metas]
            )
        
        # --- 3) Upsert to latest_entities_v1 (with safeguards) ---
        latest = get_or_create_collection(COLL_LATEST)
        upserted = []
        
        for obj in req.objects:
            # Safeguard: only tracked objects with high confidence
            if obj.label in TRACKED_OBJECTS and obj.confidence >= CONFIDENCE_THRESHOLD:
                canonical_key = f"{obj.label}@home"  # Could be scoped by location
                latest_id = _id_latest(req.tenant_id, canonical_key)
                
                # Short up-to-date sentence
                text = f"{obj.label} last seen at {req.frame_ts}"
                if obj.rel_pos:
                    text += f" {obj.rel_pos}"
                
                vec = embed_texts([text])[0]
                meta = {
                    "tenant_id": req.tenant_id,
                    "canonical_key": canonical_key,
                    "last_frame_ts": req.frame_ts,
                    "scene_anchor": None,
                    "confidence": obj.confidence,
                    "source_frame_id": frame_id,
                    "session_id": req.session_id,
                    "emb_model_ver": EMB_MODEL_VER,
                }
                
                # Upsert: delete then add
                try:
                    latest.delete(ids=[latest_id])
                except:
                    pass
                
                latest.add(
                    ids=[latest_id],
                    documents=[text],
                    embeddings=[vec],
                    metadatas=[_clean_metadata(meta)]
                )
                upserted.append(latest_id)
        
        return {
            "ok": True,
            "frame_id": frame_id,
            "entity_ids": ent_ids,
            "latest_upserted": upserted
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/add_note")
async def add_note(req: NoteIngestRequest):
    """
    Store user-provided note (voice or typed 'remember this').
    Stores in user_notes_v1 - durable, most trusted memory.
    """
    try:
        notes = get_or_create_collection(COLL_NOTES)
        now = int(time.time())
        note_id = hex(now)[2:]
        
        text = req.text.strip()
        vec = embed_texts([text])[0]
        
        meta = {
            "tenant_id": req.tenant_id,
            "note_id": note_id,
            "created_ts": now,
            "modality": req.modality,
            "priority": req.priority,
            "tags": req.tags,
            "linked_entity": req.linked_entity,
            "emb_model_ver": EMB_MODEL_VER,
        }
        
        notes.add(
            ids=[_id_note(req.tenant_id, note_id)],
            documents=[text],
            embeddings=[vec],
            metadatas=[_clean_metadata(meta)]
        )
        
        return {"ok": True, "note_id": note_id}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/search_last_seen")
async def search_last_seen(req: SearchLastSeenRequest):
    """
    O(1) answer to 'Where are my keys?'
    Query latest_entities_v1 by canonical_key filter.
    """
    try:
        latest = get_or_create_collection(COLL_LATEST)
        
        results = latest.get(
            where={
                "$and": [
                    {"tenant_id": req.tenant_id},
                    {"canonical_key": req.canonical_key}
                ]
            },
            include=["documents", "metadatas"]
        )
        
        if not results["ids"]:
            return {"ok": True, "found": False}
        
        return {
            "ok": True,
            "found": True,
            "document": results["documents"][0],
            "metadata": results["metadatas"][0]
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/search_semantic")
async def search_semantic(req: SearchSemanticRequest):
    """
    Semantic search across specified collections.
    Useful for: 'When did I last see the red mug?', 'Remind me about pills'
    """
    try:
        query_vec = embed_texts([req.query_text])[0]
        all_results = []
        
        for coll_name in req.collections:
            coll = get_or_create_collection(coll_name)
            results = coll.query(
                query_embeddings=[query_vec],
                n_results=req.n_results,
                where={"tenant_id": req.tenant_id},
                include=["documents", "metadatas", "distances"]
            )
            
            for i in range(len(results["ids"][0])):
                all_results.append({
                    "collection": coll_name,
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })
        
        # Sort by distance
        all_results.sort(key=lambda x: x["distance"])
        
        return {"ok": True, "results": all_results[:req.n_results]}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/search_time_window")
async def search_time_window(req: SearchTimeWindowRequest):
    """
    'What happened around 10:40?'
    Query frames_ephemeral_v1 by time window.
    """
    try:
        frames = get_or_create_collection(COLL_FRAMES)
        
        results = frames.get(
            where={
                "$and": [
                    {"tenant_id": req.tenant_id},
                    {"frame_ts": {"$gte": req.start_ts}},
                    {"frame_ts": {"$lte": req.end_ts}}
                ]
            },
            limit=req.n_results,
            include=["documents", "metadatas"]
        )
        
        items = []
        for i in range(len(results["ids"])):
            items.append({
                "id": results["ids"][i],
                "document": results["documents"][i],
                "metadata": results["metadatas"][i]
            })
        
        return {"ok": True, "results": items}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/curate_to_ltm")
async def curate_to_ltm(req: CurateToLTMRequest):
    """
    User selects what to keep after session.
    This is the key cost control mechanism - only persist what matters.
    Stores in long_term_memory_v1.
    """
    try:
        ltm = get_or_create_collection(COLL_LTM)
        now = int(time.time())
        
        ids, docs, vecs, metas = [], [], [], []
        
        for item in req.items:
            origin = item.get("origin", "manual")
            origin_id = item.get("origin_id", "")
            text = item.get("text", "")
            
            if not text:
                continue
            
            ltm_id = _id_ltm(req.tenant_id, origin_id)
            vec = embed_texts([text])[0]
            
            meta = {
                "tenant_id": req.tenant_id,
                "origin": origin,
                "origin_id": origin_id,
                "curated_by": "user",
                "curated_ts": now,
                "session_id": req.session_id,
                "reviewed": True,
                "tags": req.tags,
                "emb_model_ver": EMB_MODEL_VER,
            }
            
            ids.append(ltm_id)
            docs.append(text)
            vecs.append(vec)
            metas.append(meta)
        
        if ids:
            ltm.add(ids=ids, documents=docs, embeddings=vecs, metadatas=[_clean_metadata(m) for m in metas])
        
        return {"ok": True, "curated": len(ids)}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/compact")
async def compact(req: CompactRequest):
    """
    Housekeeping: TTL enforcement.
    Delete frames_ephemeral_v1 and entities_stream_v1 older than TTL.
    Prevents cost explosion at 5-second capture cadence.
    """
    try:
        cutoff = int(time.time()) - (req.ttl_hours * 3600)
        
        frames = get_or_create_collection(COLL_FRAMES)
        entities = get_or_create_collection(COLL_ENTITIES)
        
        # Delete old frames
        try:
            frames.delete(
                where={
                    "$and": [
                        {"tenant_id": req.tenant_id},
                        {"frame_ts": {"$lt": cutoff}}
                    ]
                }
            )
        except Exception as e:
            print(f"Frames compaction warning: {e}")
        
        # Delete old entities
        try:
            entities.delete(
                where={
                    "$and": [
                        {"tenant_id": req.tenant_id},
                        {"frame_ts": {"$lt": cutoff}}
                    ]
                }
            )
        except Exception as e:
            print(f"Entities compaction warning: {e}")
        
        return {"ok": True, "cutoff_ts": cutoff}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/clear_collection")
async def clear_collection(req: dict):
    """Clear all documents from a collection"""
    try:
        collection_name = req.get("collection_name")
        if not collection_name:
            raise HTTPException(status_code=400, detail="collection_name required")
        
        collection = get_or_create_collection(collection_name)
        
        # Get all IDs in the collection
        all_items = collection.get()
        if all_items and all_items.get("ids"):
            count = len(all_items["ids"])
            collection.delete(ids=all_items["ids"])
            return {
                "ok": True,
                "collection": collection_name,
                "deleted_count": count
            }
        else:
            return {
                "ok": True,
                "collection": collection_name,
                "deleted_count": 0,
                "message": "Collection was already empty"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query_by_item/{item_name}")
async def query_by_item(item_name: str, tenant_id: str = "user_123", limit: int = 10):
    """
    Query all mentions of a specific item by name.
    New ID format makes this efficient: tenant:label:session:timestamp
    """
    try:
        entities = get_or_create_collection(COLL_ENTITIES)
        
        # Query by metadata filter on obj_label
        results = entities.get(
            where={
                "$and": [
                    {"tenant_id": tenant_id},
                    {"obj_label": item_name}
                ]
            },
            limit=limit,
            include=["documents", "metadatas"]
        )
        
        items = []
        for i in range(len(results["ids"])):
            items.append({
                "id": results["ids"][i],
                "document": results["documents"][i],
                "metadata": results["metadatas"][i],
                "timestamp": results["metadatas"][i].get("frame_ts")
            })
        
        # Sort by timestamp (newest first)
        items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        return {
            "ok": True,
            "item_name": item_name,
            "total_mentions": len(items),
            "results": items
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/healthz")
async def health():
    """Health check"""
    return {
        "ok": True,
        "service": "ar-glasses-vector-store",
        "collections": [COLL_FRAMES, COLL_ENTITIES, COLL_LATEST, COLL_NOTES, COLL_LTM]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    print(f"\n[STARTUP] AR Glasses Vector Memory Store")
    print(f"   Starting on port {port}")
    print(f"   Docs: http://localhost:{port}/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
