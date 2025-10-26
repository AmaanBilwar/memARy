#!/usr/bin/env python3
"""
Initialize Helix database using Instance management.
"""
import helix
import os
import time

def initialize_with_instance():
    """Initialize Helix using Instance management."""
    print("Starting Helix instance...")
    
    try:
        # Create Helix instance
        helix_instance = helix.Instance("helixdb-cfg", 6969, verbose=True)
        
        # Wait a moment for the instance to start
        print("Waiting for Helix instance to start...")
        time.sleep(3)
        
        # Create client
        db = helix.Client(local=True, verbose=True)
        
        # Try to create the schema using single-line commands
        print("Creating memory entity...")
        
        # Create entity
        entity_cmd = 'entity memory { id: string, session_id: string, description: string, user_context: string, embedding: vector<float>(1536), created_at: datetime, @primary(id), @index(embedding, type = "hnsw", metric = "cosine"), @index(session_id, created_at) }'
        
        try:
            result = db.query(entity_cmd)
            print(f"Entity creation result: {result}")
        except Exception as e:
            print(f"Entity creation error: {e}")
        
        # Test adding a memory
        print("Testing memory insertion...")
        test_memory_cmd = 'insert into memory values { id: "test-789", session_id: "test-session", description: "Test memory", user_context: "Test context", embedding: [0.1, 0.1, 0.1, 0.1, 0.1], created_at: "2024-01-01T00:00:00Z" }'
        
        try:
            result = db.query(test_memory_cmd)
            print(f"Memory insertion result: {result}")
        except Exception as e:
            print(f"Memory insertion error: {e}")
        
        # Test listing memories
        print("Testing memory listing...")
        list_cmd = 'from memory order by created_at desc limit 10'
        
        try:
            result = db.query(list_cmd)
            print(f"Memory listing result: {result}")
        except Exception as e:
            print(f"Memory listing error: {e}")
        
        print("Helix instance will be automatically stopped when script exits")
        return True
        
    except Exception as e:
        print(f"Error with Helix instance: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting Helix database initialization with instance management...")
    initialize_with_instance()
