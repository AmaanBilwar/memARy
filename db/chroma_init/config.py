from pydantic import BaseModel
class ChromaConfig(BaseModel):
    persist_directory: str = './var/chroma'
    tenant: str = 'default_tenant'
    database: str = 'memory_copilot'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
