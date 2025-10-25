from typing import List
class SimpleEmbedder:
    def __init__(self, model_name: str):
        # Lazy import to keep startup light
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
    def embed(self, texts: List[str]):
        return self.model.encode(texts, normalize_embeddings=True)
