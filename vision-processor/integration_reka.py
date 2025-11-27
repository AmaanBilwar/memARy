"""
Complete Pipeline: Image → Text Summary → JSON → Vector Store
2-stage vision analysis with ChromaDB memory storage
"""
import os
import time
import requests
from dotenv import load_dotenv
from vision_reka import analyze_image

# Load environment variables
load_dotenv()

VECTOR_STORE_URL = os.getenv("VECTOR_STORE_URL", "http://localhost:8001")
TENANT_ID = os.getenv("TENANT_ID", "user_123")
DEVICE_ID = os.getenv("DEVICE_ID", "glasses_01")

def process_image_to_memory(image_path: str, session_id: str = None) -> dict:
    """
    Complete 2-stage pipeline:
    1. Image → Text summary (Reka vision)
    2. Text summary → JSON (structured extraction)
    3. Store in vector database with embeddings
    4. Return results
    """
    
    print(f"📸 Processing: {image_path}")
    
    # Steps 1+2: Reka 2-stage analysis (image → text → JSON)
    print("🤖 Analyzing with Reka (2-stage)...")
    vision_result = analyze_image(image_path)
    
    # Step 2: Prepare for vector store
    frame_ts = int(time.time())
    session_id = session_id or f"session_{frame_ts}"
    
    payload = {
        "tenant_id": TENANT_ID,
        "device_id": DEVICE_ID,
        "session_id": session_id,
        "frame_ts": frame_ts,
        "scene_summary": vision_result["scene_summary"],
        "objects": vision_result["objects"]
    }
    
    # Step 3: Store in vector database
    print("💾 Storing in vector database...")
    try:
        response = requests.post(
            f"{VECTOR_STORE_URL}/add_frame",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        vector_result = response.json()
        
        print(f"✓ Stored: {vector_result['frame_id']}")
        print(f"✓ Objects: {len(vector_result.get('entity_ids', []))}")
        print(f"✓ Tracked: {vector_result.get('latest_upserted', [])}")
        
        return {
            "ok": True,
            "vision": vision_result,
            "stored": vector_result
        }
        
    except Exception as e:
        print(f"✗ Vector store error: {e}")
        return {
            "ok": False,
            "vision": vision_result,
            "error": str(e)
        }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python integration_reka.py <image_path>")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("IMAGE → TEXT → JSON → VECTOR STORE PIPELINE")
    print("="*60 + "\n")
    
    result = process_image_to_memory(sys.argv[1])
    
    print("\n" + "="*60)
    if result["ok"]:
        print("✅ COMPLETE PIPELINE SUCCESS!")
    else:
        print("⚠️  PARTIAL SUCCESS (vision ok, storage failed)")
    print("="*60)