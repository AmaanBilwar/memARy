# Architecture Overview

## Service Boundary

This is a **database-only microservice** focused exclusively on vector storage and retrieval using ChromaDB.

### What This Service Owns

- ✅ Vector collections lifecycle (create, evolve, delete)
- ✅ Embedding functions wiring
- ✅ Write paths: upsert, delete
- ✅ Read paths: vector similarity + metadata filters
- ✅ Backups and restores (snapshots)
- ✅ Migrations (metadata/collection changes)

### What This Service Does NOT Own

- ❌ HTTP/gRPC API gateway
- ❌ Ingestion from devices
- ❌ Business/domain logic
- ❌ AuthZ/AuthN (stubbed as future)

## Technical Stack

- **Language**: Python 3.11
- **Database**: ChromaDB (persistent client)
- **Embedding**: Pluggable (sentence-transformers default, supports OpenAI, instructor models)
- **Persistence**: Local folder or mounted volume (`./var/chroma`)
- **Observability**: Lightweight metrics/logging hooks; collection stats
- **Packaging**: pip + requirements.txt

## Collections Architecture

The service manages 7 vector collections:

1. **people** - Person identities and relationships
2. **objects** - Tracked objects and items
3. **places** - Location information
4. **reminders** - Task and reminder system
5. **frames** - Captured frame metadata
6. **notes** - General notes
7. **qa_index** - Query understanding patterns

Each collection:
- Uses a specific ID prefix (`p_`, `o_`, `pl_`, etc.)
- Has a defined metadata schema
- Employs cosine similarity search via HNSW index
- Supports metadata filtering

## Embedding Strategy

### Default Configuration

- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Dimensions: 384
- Normalization: Yes (L2 normalized)
- Similarity: Cosine

### Embedding Targets

Each collection has specific text content that gets embedded:

- **people**: Name + Relationship + Notes
- **objects**: Label + Description + Tags
- **places**: Name + Description
- **reminders**: Text content
- **frames**: Transcripts/Captions + Notes
- **notes**: Note text
- **qa_index**: Utterance patterns

### Pluggable Embedders

The `SimpleEmbedder` class can be swapped out:

```python
from db.chroma_init.embedder import SimpleEmbedder

# Default
emb = SimpleEmbedder('sentence-transformers/all-MiniLM-L6-v2')

# Alternatives
emb = SimpleEmbedder('sentence-transformers/all-mpnet-base-v2')
emb = SimpleEmbedder('intfloat/e5-large-v2')
```

## Persistence Strategy

### Local Storage

- Default path: `./var/chroma`
- Format: ChromaDB's native persistent format
- Contains: Collections, HNSW indexes, metadata, embeddings

### Snapshot Backups

- Path: `./var/chroma-snapshots`
- Frequency: Daily (configurable via cron)
- Retention: 7 days (configurable)
- Method: Filesystem copy
- Remote sync: Optional S3 support

### Backup Process

1. Stop writes (or use copy-on-write)
2. Copy `./var/chroma` to `./var/chroma-snapshots/snapshot-TIMESTAMP`
3. Optional: Upload to S3
4. Cleanup old snapshots (>7 days)

## Query Patterns

### Semantic Search

```python
# Embed query text
query_vector = embedder.embed([query_text])[0]

# Search with optional metadata filter
results = collection.query(
    query_embeddings=[query_vector],
    n_results=5,
    where={"Status": "found"}
)
```

### Metadata Filtering

Supported operators:
- Equality: `{"Status": "found"}`
- Comparison: `{"Confidence": {"$gt": 0.8}}`
- Logical OR: `{"$or": [{"Status": "found"}, {"Status": "missing"}]}`

## Migration Strategy

### Philosophy

- Evolve metadata schemas via up/down scripts
- Collections are append-only
- Allow metadata rewrites
- Re-embed only when text changes

### Migration Process

1. Create migration script in `db/migrations/`
2. Define `up()` and `down()` functions
3. Run migration via `python db/migrations/MIGRATION_NAME.py`
4. Re-upsert affected documents if needed

### Example Migration

```python
def up():
    # Add new field to all people
    # Re-upsert with augmented metadata
    pass

def down():
    # Remove new field
    # Re-upsert without field
    pass
```

## Multitenancy

### Namespace Strategy

- Separate ChromaDB clients per tenant
- Tenant ID stored in config
- ID prefixes include tenant context (future enhancement)

### Current Implementation

Single tenant by default (`default_tenant`), with hooks for multi-tenant:
- Configurable tenant in `ChromaConfig`
- Client isolation via separate persistent directories

## Security Considerations

### PII Handling

- Tag PII=true in metadata
- Allow selective export/backup with redaction
- Blocklist sensitive keys from filters

### Metadata Scrub

Blocklist sensitive metadata keys from being used as positive filters:
- Future enhancement: Add `FORBIDDEN_FILTER_KEYS` config
- Enforce in higher layers (API gateway)

### Access Control

- Not implemented in this service
- Stubbed for future API layer
- Assume trusted callers at DB boundary

## Scaling Considerations

### Horizontal Scaling

- **Sharding**: Separate directories or Chroma instances per tenant
- **Replication**: Read replicas via filesystem replication
- **Load balancing**: External to this service

### Vertical Scaling

- **Index tuning**: Adjust HNSW parameters (ef_construction, M)
- **Batch operations**: Prefer batched upserts
- **Embedding pre-computation**: Compute embeddings upstream

### Retention Strategy

- Age out old frames via TTL scripts
- Keep last N entries per entity
- Archive to cold storage

## Operational Metrics

### Collection Stats

Track:
- Document count per collection
- Index size
- Query latency
- Upsert throughput

### Monitoring Hooks

- Log collection operations
- Track query patterns
- Monitor snapshot success/failure
- Alert on index corruption

## Handoff Notes

### For Upstream Services

1. **Minimal DB Interface**: Expose only essential operations via RPC
2. **Stable IDs**: Require callers to provide stable, unique IDs
3. **Well-formed Metadata**: Enforce schema compliance
4. **Dual Mode**: Accept both pre-computed embeddings and text

### For API Gateway

1. **Single Responsibility**: This service owns only DB operations
2. **No Business Logic**: All domain logic lives in upstream services
3. **Error Handling**: Translate DB errors to appropriate API responses
4. **Rate Limiting**: Implement in API layer, not DB layer

## Future Enhancements

### Planned

- [ ] Multitenancy isolation improvements
- [ ] Metadata schema validation
- [ ] Incremental backup support
- [ ] Collection-specific retention policies
- [ ] Query result caching

### Considered

- [ ] GraphQL adapter layer
- [ ] Real-time replication
- [ ] Embedding model A/B testing
- [ ] Query analytics dashboard

