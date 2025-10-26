#!/usr/bin/env python3
"""
Simple in-memory memory storage for memARy application.
This provides basic memory operations without complex database setup.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4
import json

class SimpleMemoryStore:
    """Simple in-memory memory storage."""
    
    def __init__(self):
        self.memories: List[Dict[str, Any]] = []
    
    def add_memory(self, description: str, user_context: str = "", session_id: str = "default-session") -> Dict[str, Any]:
        """Add a memory to the store."""
        memory = {
            "id": str(uuid4()),
            "session_id": session_id,
            "description": description,
            "user_context": user_context,
            "created_at": datetime.now().isoformat()
        }
        self.memories.append(memory)
        return {"success": True, "memory": memory}
    
    def list_memories(self, session_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """List memories, optionally filtered by session."""
        filtered_memories = self.memories
        if session_id:
            filtered_memories = [m for m in self.memories if m["session_id"] == session_id]
        
        # Sort by created_at descending (newest first)
        filtered_memories.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply limit
        filtered_memories = filtered_memories[:limit]
        
        return {"success": True, "memories": filtered_memories, "count": len(filtered_memories)}
    
    def search_memories(self, query: str, session_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Search memories by text content."""
        filtered_memories = self.memories
        if session_id:
            filtered_memories = [m for m in self.memories if m["session_id"] == session_id]
        
        # Simple text search
        query_lower = query.lower()
        matching_memories = []
        for memory in filtered_memories:
            if (query_lower in memory["description"].lower() or 
                query_lower in memory["user_context"].lower()):
                matching_memories.append(memory)
        
        # Sort by created_at descending
        matching_memories.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply limit
        matching_memories = matching_memories[:limit]
        
        return {"success": True, "memories": matching_memories, "count": len(matching_memories)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories."""
        total = len(self.memories)
        by_session = {}
        for memory in self.memories:
            session = memory["session_id"]
            by_session[session] = by_session.get(session, 0) + 1
        
        return {
            "success": True,
            "total": total,
            "by_session": by_session
        }
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory by ID."""
        for i, memory in enumerate(self.memories):
            if memory["id"] == memory_id:
                deleted_memory = self.memories.pop(i)
                return {"success": True, "deleted_memory": deleted_memory}
        
        return {"success": False, "error": "Memory not found"}

# Global memory store instance
memory_store = SimpleMemoryStore()

# Convenience functions that match the original API
def add_memory(description: str, user_context: str = "", session_id: str = "default-session") -> Dict[str, Any]:
    """Add a memory."""
    return memory_store.add_memory(description, user_context, session_id)

def list_memories(session_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """List memories."""
    return memory_store.list_memories(session_id, limit)

def search_memories(query: str, session_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """Search memories."""
    return memory_store.search_memories(query, session_id, limit)

def get_stats() -> Dict[str, Any]:
    """Get memory statistics."""
    return memory_store.get_stats()

def delete_memory(memory_id: str) -> Dict[str, Any]:
    """Delete a memory."""
    return memory_store.delete_memory(memory_id)

if __name__ == "__main__":
    # Test the simple memory store
    print("Testing simple memory store...")
    
    # Add some test memories
    add_memory("I saw a red car today", "It was parked outside my house", "session-1")
    add_memory("Had lunch at the cafe", "The sandwich was delicious", "session-1")
    add_memory("Meeting with the team", "Discussed the new project", "session-2")
    
    # List memories
    print("\nAll memories:")
    result = list_memories()
    print(json.dumps(result, indent=2))
    
    # Search memories
    print("\nSearching for 'car':")
    result = search_memories("car")
    print(json.dumps(result, indent=2))
    
    # Get stats
    print("\nStats:")
    result = get_stats()
    print(json.dumps(result, indent=2))
