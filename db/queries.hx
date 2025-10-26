// Helix queries for memARy text-only memory engine

query add_memory(payload) {
  insert into N::Memory values payload
}

query list_memories({ session_id, limit }) {
  from N::Memory
  where session_id == session_id or session_id is null
  order by created_at desc
  limit coalesce(limit, 100)
}

query search_memory({ embedding, session_id, limit }) {
  from N::Memory
  using knn on embedding with query embedding metric cosine
  where session_id == session_id or session_id is null
  limit coalesce(limit, 5)
}

query stats() {
  {
    total: count(N::Memory),
    by_session: group N::Memory by session_id with { session_id, count: count(*) }
  }
}

