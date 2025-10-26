// Helix schema for memARy text-only memory engine

entity memory {
  id: string,
  session_id: string,
  description: string,
  user_context: string,
  embedding: vector<float>(1536),
  created_at: datetime

  // Primary key
  @primary(id)

  // Vector similarity index for KNN search
  @index(embedding, type = "hnsw", metric = "cosine")

  // Secondary index to list by session and recency
  @index(session_id, created_at)
}
