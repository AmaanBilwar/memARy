// Helix schema for memARy text-only memory engine

N::Memory {
  id: String,
  session_id: String,
  description: String,
  user_context: String,
  embedding: Vector<Float>(1536),
  created_at: DateTime
}
