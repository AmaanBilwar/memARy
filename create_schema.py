#!/usr/bin/env python3
"""
Create Helix schema using the Schema class.
"""
import helix
import os

def create_memory_schema():
    """Create the memory schema using Helix Schema class."""
    print("Creating memory schema...")
    
    try:
        # Create schema
        schema = helix.Schema()
        
        # Create the memory node (entity)
        print("Creating memory node...")
        schema.create_node("memory", {
            "id": "String",
            "session_id": "String", 
            "description": "String",
            "user_context": "String",
            "created_at": "Date"
        })
        
        # Create the embedding vector separately
        print("Creating embedding vector...")
        schema.create_vector("memory_embedding", {"vec": "Vec32"})
        
        print("Note: Primary keys and indexes will be added via the schema.hx file")
        
        # Save the schema
        print("Saving schema...")
        schema.save()
        
        print("Schema created and saved successfully!")
        
        # Show the schema
        print("\nSchema contents:")
        schema.show_schema()
        
        return True
        
    except Exception as e:
        print(f"Error creating schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Creating Helix memory schema...")
    create_memory_schema()
