#!/usr/bin/env python3
"""
Create a simple Helix schema for testing.
"""
import helix

def create_simple_schema():
    """Create a simple schema for testing."""
    print("Creating simple schema...")
    
    try:
        # Create schema
        schema = helix.Schema()
        
        # Create a simple node first
        print("Creating simple node...")
        schema.create_node("test_node", {
            "id": "String",
            "name": "String"
        })
        
        # Save the schema
        print("Saving schema...")
        schema.save()
        
        print("Simple schema created successfully!")
        
        # Show the schema
        print("\nSchema contents:")
        schema.show_schema()
        
        return True
        
    except Exception as e:
        print(f"Error creating simple schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Creating simple Helix schema...")
    create_simple_schema()
