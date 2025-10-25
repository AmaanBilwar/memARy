import chromadb
from chromadb.config import Settings
from db.chroma_init.config import ChromaConfig

MIGRATION_ID = '2025-10-people-add-pii'

def up():
    cfg = ChromaConfig()
    client = chromadb.Client(Settings(persist_directory=cfg.persist_directory))
    col = client.get_collection('people')
    # naive scan: pull all items via pagination; Chroma Python client lacks full scan helper, so rely on app-managed ids or mirror index
    print('UP: please re-upsert people with PII=true using db/scripts/upsert_batch.py (metadata augmentation).')

def down():
    print('DOWN: re-upsert people without PII field.')

if __name__ == '__main__':
    up()
