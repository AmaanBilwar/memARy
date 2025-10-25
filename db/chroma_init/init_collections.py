import os
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")
os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "1")
os.environ.setdefault("CHROMADB_DISABLE_TELEMETRY", "1")

"""Initialize Chroma with telemetry fully disabled."""

# Monkeypatch posthog BEFORE importing chromadb so import-time hooks are no-ops
try:
    import posthog as _ph
    def _noop2(*args, **kwargs):
        return None
    for _name in ("capture", "identify", "flush", "shutdown", "init"):
        if hasattr(_ph, _name):
            setattr(_ph, _name, _noop2)
except Exception:
    pass

import chromadb
from chromadb.config import Settings
from .config import ChromaConfig

# Best-effort: silence any lingering telemetry hooks if library still tries to capture (after import)
try:
    import chromadb.telemetry as _ct
    def _noop(*args, **kwargs):
        return None
    _ct.capture = _noop  # type: ignore
    if hasattr(_ct, 'posthog') and hasattr(_ct.posthog, 'capture'):
        _ct.posthog.capture = _noop  # type: ignore
    if hasattr(_ct, 'client') and hasattr(_ct.client, 'capture'):
        _ct.client.capture = _noop  # type: ignore
except Exception:
    pass

# (posthog monkeypatch already executed before import)

COLLECTIONS = {
    'people': {}, 'objects': {}, 'places': {}, 'reminders': {}, 'frames': {}, 'notes': {}, 'qa_index': {}
}

def get_client(cfg: ChromaConfig):
    # Prefer PersistentClient for on-disk persistence
    try:
        return chromadb.PersistentClient(
            path=cfg.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
    except AttributeError:
        # Fallback for older chroma versions
        return chromadb.Client(Settings(persist_directory=cfg.persist_directory, anonymized_telemetry=False))

def ensure_collections(client):
    for name in COLLECTIONS:
        try:
            client.get_collection(name)
        except Exception:
            client.create_collection(name, metadata={'hnsw:space': 'cosine'})

if __name__ == '__main__':
    cfg = ChromaConfig()
    client = get_client(cfg)
    ensure_collections(client)
    print('Chroma collections initialized:', list(COLLECTIONS.keys()))
