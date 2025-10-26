#!/usr/bin/env python3
"""
Add vector to existing schema.
"""
import helix

def add_vector_to_schema():
    """Add vector to existing schema."""
    print("Adding vector to schema...")
    
    try:
        # Load existing schema
        schema = helix.Schema()
        
        # Add the memory node
        print("Adding memory node...")
        schema.create_node("memory", {
            "id": "String",
            "session_id": "String", 
            "description": "String",
            "user_context": "String",
            "created_at": "Date"
        })
        
        # Add vector
        print("Adding vector...")
        schema.create_vector("memory_embedding", {"vec": "Vec32"})
        
        # Save the schema
        print("Saving schema...")
        schema.save()
        
        print("Schema with vector created successfully!")
        
        # Show the schema
        print("\nSchema contents:")
        schema.show_schema()
        
        return True
        
    except Exception as e:
        print(f"Error adding vector: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Adding vector to Helix schema...")
    add_vector_to_schema()
