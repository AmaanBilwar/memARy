"""
ChromaDB client with 5-tier memory architecture
"""
import os
import sys

# Disable ChromaDB telemetry BEFORE importing chromadb
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

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

"""ChromaDB configuration - secrets must come from environment (.env).

If cloud credentials are not present, we fall back to a local persistent client.
We never hardcode or print secrets here.
"""

# ChromaDB Cloud configuration (no defaults; rely on env)
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")

# Local fallback
PERSIST_DIR = os.getenv("CHROMA_DIR", "./.chroma")

# Decide cloud usage: explicit env override or auto if all secrets present
_USE_CLOUD_ENV = os.getenv("USE_CHROMA_CLOUD")
if _USE_CLOUD_ENV is None:
    USE_CLOUD = bool(CHROMA_API_KEY and CHROMA_TENANT and CHROMA_DATABASE)
else:
    USE_CLOUD = _USE_CLOUD_ENV.lower() == "true"

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
        # Aggressive settings to completely disable all telemetry
        settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=True
        )
        
        # Additional environment variable enforcement
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"
        
        if USE_CLOUD and CHROMA_API_KEY and CHROMA_TENANT and CHROMA_DATABASE:
            try:
                _client = chromadb.CloudClient(
                    api_key=CHROMA_API_KEY,
                    tenant=CHROMA_TENANT,
                    database=CHROMA_DATABASE,
                    settings=settings
                )
                print("[OK] ChromaDB Cloud connected")
            except Exception as e:
                print("[WARN] ChromaDB Cloud connection failed; falling back to local persistent client")
                _client = chromadb.PersistentClient(
                    path=PERSIST_DIR,
                    settings=settings
                )
                print(f"[OK] ChromaDB local connected at {PERSIST_DIR}")
        else:
            if _USE_CLOUD_ENV and _USE_CLOUD_ENV.lower() == "true":
                print("[WARN] USE_CHROMA_CLOUD=true but required credentials are missing; using local persistent client")
            _client = chromadb.PersistentClient(
                path=PERSIST_DIR,
                settings=settings
            )
            print(f"[OK] ChromaDB local connected at {PERSIST_DIR}")
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
    print(f"[OK] Initialized {len(collections)} collections")
