#!/usr/bin/env python3
"""
Simple Helix database initialization using direct client commands.
"""
import helix

def initialize_helix_database():
    """Initialize Helix database with the memARy schema."""
    print("Initializing Helix database...")
    
    try:
        # Create client
        db = helix.Client(local=True, verbose=True)
        
        # Create the memory entity using raw Helix commands
        print("Creating memory entity...")
        
        # First, let's try to create the schema using raw commands
        schema_commands = [
            # Create the memory entity
            """
            entity memory {
                id: string,
                session_id: string,
                description: string,
                user_context: string,
                embedding: vector<float>(1536),
                created_at: datetime
                
                @primary(id)
                @index(embedding, type = "hnsw", metric = "cosine")
                @index(session_id, created_at)
            }
            """
        ]
        
        for cmd in schema_commands:
            try:
                print(f"Executing: {cmd.strip()}")
                result = db.query(cmd)
                print(f"Result: {result}")
            except Exception as e:
                print(f"Warning: {e}")
        
        print("Database initialization completed")
        return True
        
    except Exception as e:
        print(f"Error initializing Helix database: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test the database functionality."""
    print("\nTesting database functionality...")
    
    try:
        db = helix.Client(local=True, verbose=True)
        
        # Test adding a memory
        print("Adding test memory...")
        result = db.query("""
            insert into memory values {
                id: "test-123",
                session_id: "test-session", 
                description: "Test memory",
                user_context: "Test context",
                embedding: [0.1, 0.1, 0.1, 0.1, 0.1],
                created_at: "2024-01-01T00:00:00Z"
            }
        """)
        print(f"Add result: {result}")
        
        # Try to list memories
        print("Listing memories...")
        memories = db.query("""
            from memory
            order by created_at desc
            limit 10
        """)
        print(f"Memories: {memories}")
        
        return True
        
    except Exception as e:
        print(f"Error testing database: {e}")
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
