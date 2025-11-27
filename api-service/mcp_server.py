#!/usr/bin/env python3
"""
Remembar MCP Server
Exposes memory operations as MCP tools for AI assistants
"""
import asyncio
import json
import time
import httpx
import os
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    CallToolResult,
    LATEST_PROTOCOL_VERSION
)
from pydantic import Field

# Remembar API endpoints
API_BASE = os.getenv("REMEMBAR_API_URL", "http://localhost:8000")

app = Server("remembar")


# ============================================================================
# MCP Tools - Memory Operations
# ============================================================================

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available memory tools"""
    return [
        Tool(
            name="store_memory",
            description="Store a new memory from a text description. Use this when the user mentions seeing something or wants to remember an observation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Natural language description of what was seen or observed (e.g., 'there is a yellow key on the table')"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session identifier to group related memories",
                        "default": "default"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="search_memories",
            description="Search memories using natural language. Use this when the user asks 'where is', 'what color', or any question about past observations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language question (e.g., 'what color is the key?', 'where are my keys?')"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session to search within",
                        "default": None
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_timeline",
            description="Get all memories organized by date (today, yesterday, last week, etc.). Use this when user asks to see all memories or a timeline.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return",
                        "default": 100
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="track_item",
            description="Add an important item to track with alerts. Use this when user says 'remind me about X' or 'track my X'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Name of item to track (e.g., 'keys', 'medication', 'wallet')"
                    },
                    "alert_hours": {
                        "type": "integer",
                        "description": "Hours before alerting if item not seen",
                        "default": 24
                    }
                },
                "required": ["item_name"]
            }
        ),
        Tool(
            name="get_tracked_items",
            description="Get list of all tracked items with their status and alerts. Use this when user asks what items are being tracked.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_statistics",
            description="Get comprehensive statistics about stored memories (total count, objects, timeline). Use when user asks for stats or overview.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_flashcards",
            description="Generate memory reinforcement flashcards based on stored memories. Use for memory training or review.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of flashcards to generate",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="clear_storage",
            description="Clear all stored memories and reset the database. Use only when explicitly requested by user.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Execute a memory tool"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if name == "store_memory":
                text = arguments.get("text", "")
                session_id = arguments.get("session_id", "default")
                
                response = await client.post(
                    f"{API_BASE}/store_text",
                    json={"text": text, "session_id": session_id}
                )
                response.raise_for_status()
                result = response.json()
                
                # Format response
                objects = result.get("objects", [])
                obj_list = [f"{o['label']} ({o.get('color', 'unknown')})" for o in objects]
                
                return [TextContent(
                    type="text",
                    text=f"✓ Memory stored!\n\nScene: {result['scene']}\nObjects found: {', '.join(obj_list) if obj_list else 'none'}\nTimestamp: {result.get('timestamp', 'now')}"
                )]
            
            elif name == "search_memories":
                query = arguments.get("query", "")
                session_id = arguments.get("session_id")
                limit = arguments.get("limit", 5)
                
                params = {"query": query, "limit": limit}
                if session_id:
                    params["session_id"] = session_id
                
                response = await client.get(
                    f"{API_BASE}/search",
                    params=params
                )
                response.raise_for_status()
                result = response.json()
                
                # Format the natural language answer
                answer = result.get("answer", "No results found")
                
                # Add tracked items info if present
                tracked_info = result.get("tracked_items")
                if tracked_info:
                    answer += f"\n\n⚠️ Tracked Item Alert:\n{tracked_info}"
                
                # Add related items if present
                relationships = result.get("relationships", [])
                if relationships:
                    rel_text = ", ".join([f"{r['item']} (seen together {r['count']} times)" for r in relationships])
                    answer += f"\n\n🔗 Related Items: {rel_text}"
                
                return [TextContent(type="text", text=answer)]
            
            elif name == "get_timeline":
                limit = arguments.get("limit", 100)
                
                response = await client.get(
                    f"{API_BASE}/memories",
                    params={"limit": limit}
                )
                response.raise_for_status()
                memories = response.json()
                
                if not memories:
                    return [TextContent(type="text", text="No memories stored yet.")]
                
                # Group by date
                from datetime import datetime, timedelta
                now = datetime.now()
                today = []
                yesterday = []
                this_week = []
                older = []
                
                for mem in memories:
                    mem_time = datetime.fromtimestamp(mem["timestamp"])
                    delta = now - mem_time
                    
                    if delta.days == 0:
                        today.append(mem)
                    elif delta.days == 1:
                        yesterday.append(mem)
                    elif delta.days <= 7:
                        this_week.append(mem)
                    else:
                        older.append(mem)
                
                # Format output
                output = "📅 Memory Timeline\n\n"
                
                if today:
                    output += "**Today:**\n"
                    for m in today[:10]:
                        objs = [o["label"] for o in m["objects"]]
                        output += f"  • {m['scene']} ({', '.join(objs)})\n"
                    output += "\n"
                
                if yesterday:
                    output += "**Yesterday:**\n"
                    for m in yesterday[:10]:
                        objs = [o["label"] for o in m["objects"]]
                        output += f"  • {m['scene']} ({', '.join(objs)})\n"
                    output += "\n"
                
                if this_week:
                    output += "**This Week:**\n"
                    for m in this_week[:10]:
                        objs = [o["label"] for o in m["objects"]]
                        output += f"  • {m['scene']} ({', '.join(objs)})\n"
                    output += "\n"
                
                if older:
                    output += f"**Older:** ({len(older)} memories)\n"
                
                output += f"\n📊 Total: {len(memories)} memories"
                
                return [TextContent(type="text", text=output)]
            
            elif name == "track_item":
                item_name = arguments.get("item_name", "")
                alert_hours = arguments.get("alert_hours", 24)
                
                response = await client.post(
                    f"{API_BASE}/track_item",
                    json={"item_name": item_name, "alert_hours": alert_hours}
                )
                response.raise_for_status()
                result = response.json()
                
                return [TextContent(
                    type="text",
                    text=f"✓ Now tracking '{item_name}'\nWill alert if not seen for {alert_hours} hours"
                )]
            
            elif name == "get_tracked_items":
                response = await client.get(f"{API_BASE}/tracked_items")
                response.raise_for_status()
                items = response.json()
                
                if not items:
                    return [TextContent(type="text", text="No items are currently being tracked.")]
                
                output = "📌 Tracked Items\n\n"
                for item in items:
                    status = "✅" if item["status"] == "ok" else "⚠️"
                    output += f"{status} **{item['item_name']}**\n"
                    output += f"   Last seen: {item['last_seen_text']}\n"
                    if item["status"] == "alert":
                        output += f"   ⚠️ Not seen for {item['alert_hours']} hours!\n"
                    output += "\n"
                
                return [TextContent(type="text", text=output)]
            
            elif name == "get_statistics":
                response = await client.get(f"{API_BASE}/statistics")
                response.raise_for_status()
                stats = response.json()
                
                output = "📊 Remembar Statistics\n\n"
                output += f"🧠 Total Memories: {stats['total_memories']}\n"
                output += f"📦 Objects Detected: {stats['total_objects']}\n"
                output += f"🎯 Active Sessions: {stats['active_sessions']}\n\n"
                
                if stats.get("most_common_objects"):
                    output += "**Most Common Objects:**\n"
                    for obj in stats["most_common_objects"][:5]:
                        output += f"  • {obj['label']}: {obj['count']} times\n"
                    output += "\n"
                
                if stats.get("timeline"):
                    output += "**Timeline Distribution:**\n"
                    for period in stats["timeline"]:
                        output += f"  • {period['period']}: {period['count']} memories\n"
                
                return [TextContent(type="text", text=output)]
            
            elif name == "get_flashcards":
                limit = arguments.get("limit", 10)
                
                # Get memories
                response = await client.get(
                    f"{API_BASE}/memories",
                    params={"limit": limit}
                )
                response.raise_for_status()
                memories = response.json()
                
                if not memories:
                    return [TextContent(type="text", text="No memories available for flashcards.")]
                
                output = "🎴 Memory Flashcards\n\n"
                for i, mem in enumerate(memories[:limit], 1):
                    if mem["objects"]:
                        obj = mem["objects"][0]
                        obj_name = obj["label"]
                        color = obj.get("color", "")
                        location = obj.get("rel_pos", "")
                        
                        # Generate question based on available data
                        if color and color != "null":
                            output += f"**Card {i}:**\n"
                            output += f"Q: What color was the {obj_name}?\n"
                            output += f"A: The {obj_name} was {color}.\n\n"
                        elif location and location != "null":
                            output += f"**Card {i}:**\n"
                            output += f"Q: Where was the {obj_name}?\n"
                            output += f"A: The {obj_name} was {location}.\n\n"
                        else:
                            output += f"**Card {i}:**\n"
                            output += f"Q: What object was in the scene?\n"
                            output += f"A: A {obj_name}.\n\n"
                
                return [TextContent(type="text", text=output)]
            
            elif name == "clear_storage":
                response = await client.post(f"{API_BASE}/clear_storage")
                response.raise_for_status()
                result = response.json()
                
                return [TextContent(
                    type="text",
                    text=f"✓ Storage cleared\nRemoved {result.get('cleared_count', 0)} memories"
                )]
            
            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
                
        except httpx.HTTPError as e:
            return [TextContent(
                type="text",
                text=f"Error communicating with Remembar API: {str(e)}\nMake sure the API server is running at {API_BASE}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]


# ============================================================================
# MCP Prompts - Conversation Templates
# ============================================================================

@app.list_prompts()
async def list_prompts() -> List[Prompt]:
    """Provide useful prompt templates"""
    return [
        Prompt(
            name="remember_context",
            description="Set up context for remembering observations during a conversation",
            arguments=[]
        ),
        Prompt(
            name="search_helper",
            description="Help formulate memory search queries",
            arguments=[
                PromptArgument(
                    name="question",
                    description="What the user is looking for",
                    required=True
                )
            ]
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: Dict[str, str] | None = None) -> GetPromptResult:
    """Get a specific prompt template"""
    
    if name == "remember_context":
        return GetPromptResult(
            description="Memory assistant context",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text="You are a memory assistant. When the user mentions seeing, observing, or noticing something, use the store_memory tool to save it. When they ask 'where is' or 'what color', use search_memories to find the answer. Be proactive in storing and retrieving memories."
                    )
                )
            ]
        )
    
    elif name == "search_helper":
        question = arguments.get("question", "") if arguments else ""
        return GetPromptResult(
            description="Memory search assistant",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"Help me find: {question}\n\nUse natural language search to look through stored memories. Consider object names, colors, locations, and relationships between items."
                    )
                )
            ]
        )
    
    raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run the MCP server"""
    # Check if API is available
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE}/")
            response.raise_for_status()
            print(f"✓ Connected to Remembar API at {API_BASE}", flush=True)
    except Exception as e:
        print(f"⚠️  Warning: Could not connect to Remembar API at {API_BASE}", flush=True)
        print(f"   Make sure the API server is running: cd api-service && python3 main.py", flush=True)
    
    # Run MCP server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        print(f"✓ Remembar MCP Server started", flush=True)
        print(f"   Protocol version: {LATEST_PROTOCOL_VERSION}", flush=True)
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

