import os
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")

import chromadb
from chromadb.config import Settings
from db.chroma_init.config import ChromaConfig

if __name__ == '__main__':
    cfg = ChromaConfig()
    try:
        client = chromadb.PersistentClient(path=cfg.persist_directory, settings=Settings(anonymized_telemetry=False))
    except AttributeError:
        client = chromadb.Client(Settings(persist_directory=cfg.persist_directory, anonymized_telemetry=False))
    # Placeholder: Chroma compaction happens internally; here we could reinsert or run any store-specific maintenance if exposed
    print('Maintenance: no-op (Chroma manages HNSW indexes automatically). Consider periodic export/import if needed.')
