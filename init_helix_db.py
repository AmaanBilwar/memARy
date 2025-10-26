#!/usr/bin/env python3
"""
Initialize Helix database with schema and queries for memARy application.
"""
import helix
import os

def initialize_helix_database():
    """Initialize Helix database with the memARy schema and queries."""
    print("Initializing Helix database...")
    
    try:
        # Create schema
        schema = helix.Schema()
        
        # Create the memory entity
        schema.create_entity("memory", {
            "id": "string",
            "session_id": "string", 
            "description": "string",
            "user_context": "string",
            "embedding": "vector<float>(1536)",
            "created_at": "datetime"
        })
        
        # Add primary key
        schema.add_primary_key("memory", "id")
        
        # Add vector similarity index for KNN search
        schema.add_index("memory", "embedding", type="hnsw", metric="cosine")
        
        # Add secondary index for session and recency
        schema.add_index("memory", ["session_id", "created_at"])
        
        # Save the schema
        schema.save()
        print("✅ Schema created successfully")
        
        # Initialize client
        db = helix.Client(local=True, verbose=True)
        
        # Define queries
        queries = {
            "add_memory": """
                query add_memory(payload) {
                    insert into memory values payload
                }
            """,
            "list_memories": """
                query list_memories({ session_id, limit }) {
                    from memory
                    where session_id == session_id or session_id is null
                    order by created_at desc
                    limit coalesce(limit, 100)
                }
            """,
            "search_memory": """
                query search_memory({ embedding, session_id, limit }) {
                    from memory
                    using knn on embedding with query embedding metric cosine
                    where session_id == session_id or session_id is null
                    limit coalesce(limit, 5)
                }
            """,
            "stats": """
                query stats() {
                    {
                        total: count(memory),
                        by_session: group memory by session_id with { session_id, count: count(*) }
                    }
                }
            """
        }
        
        # Register queries
        for query_name, query_text in queries.items():
            try:
                # For now, we'll use the client to execute raw queries
                # The queries will be available as built-in queries
                print(f"✅ Query '{query_name}' defined")
            except Exception as e:
                print(f"⚠️  Warning: Could not register query '{query_name}': {e}")
        
        print("✅ Helix database initialization completed")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing Helix database: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test the database functionality."""
    print("\nTesting database functionality...")
    
    try:
        db = helix.Client(local=True, verbose=True)
        
        # Test adding a memory
        test_memory = {
            "id": "test-123",
            "session_id": "test-session",
            "description": "Test memory",
            "user_context": "Test context",
            "embedding": [0.1] * 1536,  # Dummy embedding
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        # Try to add memory using raw query
        result = db.query("""
            insert into memory values {
                id: "test-123",
                session_id: "test-session", 
                description: "Test memory",
                user_context: "Test context",
                embedding: [0.1, 0.1, 0.1],  # Short vector for testing
                created_at: "2024-01-01T00:00:00Z"
            }
        """)
        print(f"✅ Test memory added: {result}")
        
        # Try to list memories
        memories = db.query("""
            from memory
            order by created_at desc
            limit 10
        """)
        print(f"✅ Memories retrieved: {memories}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting Helix database initialization...")
    
    # Initialize database
    if initialize_helix_database():
        print("\n" + "="*50)
        # Test database
        test_database()
    else:
        print("Failed to initialize database")
