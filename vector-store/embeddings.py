"""
Embedding strategy: text embeddings only (vision → text already done by LLM).
One collection = one embedding model. Normalize embeddings. Store model version.
"""
import os
from sentence_transformers import SentenceTransformer

MODEL_ID = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Model version for drift tracking
EMB_MODEL_VER = "minilm-l6-v2"
SCENE_MODEL_VER = "scene_v0.3"
DET_MODEL_VER = "det_v1.1"

_model = None

def _lazy_load():
    """Lazy load embedding model"""
    global _model
    if _model is None:
        print(f"Loading embedding model: {MODEL_ID}...")
        _model = SentenceTransformer(MODEL_ID)
        print("✓ Embedding model loaded")
    return _model

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed texts and return normalized vectors for cosine similarity.
    Normalization is crucial for stable vector search.
    """
    model = _lazy_load()
    # normalize=True for stable cosine similarity
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    # Convert numpy arrays to plain Python lists
    return [[float(x) for x in v] for v in vecs]
