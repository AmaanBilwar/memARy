"""
ChromaDB client with 5-tier memory architecture
"""
import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

# ChromaDB Cloud configuration
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY", "ck-7QBdriXEhMjhkLgbr5DBT8vPx1pgUQbfM96rQ8pe3sr3")
CHROMA_TENANT = os.getenv("CHROMA_TENANT", "053f90af-f7f0-48dd-bd77-1f67ee514158")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "remembar")

# Local fallback
PERSIST_DIR = os.getenv("CHROMA_DIR", "./.chroma")
USE_CLOUD = os.getenv("USE_CHROMA_CLOUD", "true").lower() == "true"

# Collection names (versioned for migrations)
COLL_FRAMES = "frames_ephemeral_v1"
COLL_ENTITIES = "entities_stream_v1"
COLL_LATEST = "latest_entities_v1"
COLL_NOTES = "user_notes_v1"
COLL_LTM = "long_term_memory_v1"

_client = None

def get_client():
    """Get or create ChromaDB client (Cloud or local persistent)"""
    global _client
    if _client is None:
        if USE_CLOUD:
            try:
                _client = chromadb.CloudClient(
                    api_key=CHROMA_API_KEY,
                    tenant=CHROMA_TENANT,
                    database=CHROMA_DATABASE
                )
                print(f"✓ ChromaDB Cloud connected (tenant: {CHROMA_TENANT}, database: {CHROMA_DATABASE})")
            except Exception as e:
                print(f"⚠️  ChromaDB Cloud connection failed: {e}")
                print(f"   Falling back to local persistent client")
                _client = chromadb.PersistentClient(path=PERSIST_DIR)
                print(f"✓ ChromaDB local connected at {PERSIST_DIR}")
        else:
            _client = chromadb.PersistentClient(path=PERSIST_DIR)
            print(f"✓ ChromaDB local connected at {PERSIST_DIR}")
    return _client

def get_or_create_collection(name: str, metadata: dict = None):
    """
    Get or create a collection with cosine similarity by default.
    One collection = one embedding model/type (no mixing).
    
    We provide our own embeddings, so we disable ChromaDB's default embedding function.
    """
    client = get_client()
    
    # Import the default embedding function class to create a no-op version
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    
    if USE_CLOUD:
        # For cloud, don't use embedding function since we provide our own embeddings
        # This prevents ChromaDB from trying to download the default model
        return client.get_or_create_collection(
            name=name,
            embedding_function=None  # We provide pre-computed embeddings
        )
    else:
        # Local persistent client supports custom metadata
        meta = metadata if metadata else {"hnsw:space": "cosine"}
        return client.get_or_create_collection(
            name=name,
            metadata=meta,
            embedding_function=None  # We provide pre-computed embeddings
        )

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
