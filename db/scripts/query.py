import argparse
import json
import os
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")
os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "1")
os.environ.setdefault("CHROMADB_DISABLE_TELEMETRY", "1")

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
from db.chroma_init.config import ChromaConfig
from db.chroma_init.embedder import SimpleEmbedder

p = argparse.ArgumentParser()
p.add_argument('--collection', required=True)
p.add_argument('--q', required=True)
p.add_argument('--where', default='{}', help='JSON metadata filter, e.g. {"Status":"found"}')
args = p.parse_args()

cfg = ChromaConfig()
try:
    client = chromadb.PersistentClient(path=cfg.persist_directory, settings=Settings(anonymized_telemetry=False))
except AttributeError:
    client = chromadb.Client(Settings(persist_directory=cfg.persist_directory, anonymized_telemetry=False))
col = client.get_collection(args.collection)
emb = SimpleEmbedder(cfg.embedding_model)
qv = emb.embed([args.q])[0]

where = json.loads(args.where) if args.where else {}
res = col.query(query_embeddings=[qv], n_results=5, where=where)
print(res)
