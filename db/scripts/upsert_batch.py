import os, json, argparse
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")

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

parser = argparse.ArgumentParser()
parser.add_argument('--collection', required=True)
parser.add_argument('--jsonl', required=True, help='path to JSONL with {id, text, metadata} per line')
args = parser.parse_args()

cfg = ChromaConfig()
try:
    client = chromadb.PersistentClient(path=cfg.persist_directory, settings=Settings(anonymized_telemetry=False))
except AttributeError:
    client = chromadb.Client(Settings(persist_directory=cfg.persist_directory, anonymized_telemetry=False))
col = client.get_collection(args.collection)
emb = SimpleEmbedder(cfg.embedding_model)

ids, docs, metas = [], [], []
with open(args.jsonl, 'r', encoding='utf-8') as f:
    for line in f:
        row = json.loads(line)
        ids.append(row['id'])
        docs.append(row['text'])
        metas.append(row.get('metadata', {}))

vectors = emb.embed(docs)
col.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)
print(f'Upserted {len(ids)} items into {args.collection}')
