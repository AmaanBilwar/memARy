"""
ChromaDB client with 5-tier memory architecture
"""
import os
import chromadb

PERSIST_DIR = os.getenv("CHROMA_DIR", "./.chroma")

# Collection names (versioned for migrations)
COLL_FRAMES = "frames_ephemeral_v1"
COLL_ENTITIES = "entities_stream_v1"
COLL_LATEST = "latest_entities_v1"
COLL_NOTES = "user_notes_v1"
COLL_LTM = "long_term_memory_v1"

_client = None

def get_client():
    """Get or create persistent ChromaDB client"""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=PERSIST_DIR)
        print(f"✓ ChromaDB connected at {PERSIST_DIR}")
    return _client

def get_or_create_collection(name: str, metadata: dict = None):
    """
    Get or create a collection with cosine similarity by default.
    One collection = one embedding model/type (no mixing).
    """
    client = get_client()
    meta = metadata if metadata else {"hnsw:space": "cosine"}
    return client.get_or_create_collection(name=name, metadata=meta)

def init_collections():
    """Initialize all collections on startup"""
    collections = [
        COLL_FRAMES,
        COLL_ENTITIES,
        COLL_LATEST,
        COLL_NOTES,
        COLL_LTM
    ]
    for coll in collections:
        get_or_create_collection(coll)
    print(f"✓ Initialized {len(collections)} collections")
