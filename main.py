from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import uvicorn
import os 
from dotenv import load_dotenv
import requests
import json
from openai import OpenAI
import base64
from PIL import Image
import io
from uuid import uuid4
from datetime import datetime
from simple_memory import add_memory, list_memories, search_memories, get_stats, delete_memory
try:
    # Prefer Helix embedders per docs: https://docs.helix-db.com/documentation/sdks/helix-py#embedders
    from helix.embedding.openai_client import OpenAIEmbedder  # type: ignore
    from helix.embedding.gemini_client import GeminiEmbedder  # type: ignore
except Exception:
    OpenAIEmbedder = None  # type: ignore
    GeminiEmbedder = None  # type: ignore

load_dotenv()

OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")
CHROMADB_BASE_URL=os.getenv("CHROMADB_BASE_URL")
EMBEDDING_PROVIDER=os.getenv("EMBEDDING_PROVIDER")  # optional: 'openai' | 'gemini'

# Initialize OpenAI client for OpenRouter
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

app = FastAPI(title="memARy Voice Agent API", version="1.0.0")

# Pydantic Models
class AgentRequest(BaseModel):
    text: str
    session_id: Optional[str] = "default-session"

class AgentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    tool_used: Optional[str] = None
    error: Optional[str] = None

# Tool definitions for the agent
TOOLS = [
    {
        "name": "get_all_memories",
        "description": "Get all stored memories. Use when user asks about memories, what they've seen, or wants to browse their memory bank.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to filter memories"},
                "limit": {"type": "integer", "description": "Maximum number of memories to return", "default": 100}
            }
        }
    },
    {
        "name": "search_memories",
        "description": "Search through memories using natural language. Use when user asks specific questions about their memories or wants to find something specific.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "session_id": {"type": "string", "description": "Session ID to filter search"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "find_object",
        "description": "Find where a specific object was last seen. Use when user asks 'where is my [object]' or 'where did I last see [object]'.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "description": "Name of the object to find"}
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "query_item_history",
        "description": "Get detailed history of a specific item. Use when user asks about the history, details, or properties of a specific item.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item to query"},
                "question": {"type": "string", "description": "Specific question about the item"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
            },
            "required": ["item_name"]
        }
    },
    {
        "name": "store_text_memory",
        "description": "Store a text-based memory. Use when user wants to remember something they said or when they describe something they want to remember.",
        "parameters": {
            "type": "object",
            "properties": {
                "text_summary": {"type": "string", "description": "Text description to store as memory"},
                "session_id": {"type": "string", "description": "Session ID for the memory"}
            },
            "required": ["text_summary"]
        }
    },
    {
        "name": "get_statistics",
        "description": "Get statistics about stored memories. Use when user asks about how many memories they have, storage info, or general statistics.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "track_item",
        "description": "Start tracking an item. Use when user wants to keep track of something specific.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item to track"},
                "alert_hours": {"type": "integer", "description": "Hours after which to alert if not seen", "default": 24},
                "notes": {"type": "string", "description": "Additional notes about the item", "default": ""}
            },
            "required": ["item_name"]
        }
    },
    {
        "name": "untrack_item",
        "description": "Stop tracking an item. Use when user wants to stop tracking something.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item to stop tracking"}
            },
            "required": ["item_name"]
        }
    },
    {
        "name": "get_tracked_items",
        "description": "Get all currently tracked items. Use when user asks what they're tracking or wants to see their tracked items list.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_relationships",
        "description": "Get relationships between objects. Use when user asks about what items are often seen together or relationships between objects.",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Specific item to check relationships for"}
            }
        }
    },
    {
        "name": "store_image_memory",
        "description": "Store an image as a memory with AI-generated description. Use when user wants to remember a picture, photo, or visual content.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_description": {"type": "string", "description": "AI-generated description of the image content"},
                "user_context": {"type": "string", "description": "Additional context provided by the user about the image", "default": ""},
                "session_id": {"type": "string", "description": "Session ID for the memory", "default": "default-session"}
            },
            "required": ["image_description"]
        }
    },
    {
        "name": "add_memory_direct",
        "description": "Directly add a memory without going through the AI agent. Use when user explicitly wants to store a specific memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Description of the memory to store"},
                "user_context": {"type": "string", "description": "Additional context about the memory", "default": ""},
                "session_id": {"type": "string", "description": "Session ID for the memory", "default": "default-session"}
            },
            "required": ["description"]
        }
    },
    {
        "name": "list_memories_direct",
        "description": "Directly list memories without going through the AI agent. Use when user wants to see all their memories.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to filter memories", "default": None},
                "limit": {"type": "integer", "description": "Maximum number of memories to return", "default": 100}
            }
        }
    },
    {
        "name": "search_memories_direct",
        "description": "Directly search memories without going through the AI agent. Use when user wants to find specific memories.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query to find memories"},
                "session_id": {"type": "string", "description": "Session ID to filter search", "default": None},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "delete_memory_direct",
        "description": "Directly delete a memory by ID without going through the AI agent. Use when user wants to remove a specific memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "ID of the memory to delete"}
            },
            "required": ["memory_id"]
        }
    }
]

## Helix-backed implementations (Chroma removed)

_embedder = None
def _create_embedder():
    try:
        provider = (EMBEDDING_PROVIDER or "").lower()
        # Explicit choice
        if provider == "openai" and OpenAIEmbedder and os.getenv("OPENAI_API_KEY"):
            return OpenAIEmbedder()
        if provider == "gemini" and GeminiEmbedder and os.getenv("GEMINI_API_KEY"):
            return GeminiEmbedder()
        # Auto-detect
        if OpenAIEmbedder and os.getenv("OPENAI_API_KEY"):
            return OpenAIEmbedder()
        if GeminiEmbedder and os.getenv("GEMINI_API_KEY"):
            return GeminiEmbedder()
    except Exception as e:
        print(f"Warning: Failed to initialize Helix embedder: {e}")
    return None

_embedder = _create_embedder()

def generate_text_embedding(text: str, for_query: bool = False) -> List[float]:
    """Create a text embedding via OpenRouter (OpenAI embeddings). Robust to response shapes."""
    # Preferred path: use Helix embedders
    if _embedder is not None:
        try:
            # Only Gemini supports task_type tuning; OpenAI doesn't
            if isinstance(_embedder, GeminiEmbedder):
                task_kwargs = {"task_type": "RETRIEVAL_QUERY" if for_query else "RETRIEVAL_DOCUMENT"}
                vec = _embedder.embed(text, **task_kwargs)  # type: ignore[attr-defined]
            else:
                # OpenAI embedder doesn't support task_type
                vec = _embedder.embed(text)  # type: ignore[attr-defined]
            
            # Helix embedders return the vector directly, not wrapped in an object
            if not isinstance(vec, list):
                raise TypeError("Embedder returned non-list vector")
            return [float(x) for x in vec]
        except Exception as e:
            # Fall through to OpenRouter fallback if Helix embedder fails
            print(f"Helix embedder failed: {e}, falling back to OpenRouter")
            pass
    def _to_dict(obj):
        try:
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            if hasattr(obj, "dict"):
                return obj.dict()
            if isinstance(obj, (str, bytes)):
                return json.loads(obj if isinstance(obj, str) else obj.decode())
            return obj
        except Exception:
            return obj

    last_err: Optional[Exception] = None
    attempts = [
        {"input": [text], "encoding_format": "float"},
        {"input": text},  # some providers require a plain string and no encoding_format
    ]
    for kwargs in attempts:
        try:
            res = client.embeddings.create(model="openai/text-embedding-3-small", **kwargs)  # type: ignore[arg-type]

            # Handle different response types
            if hasattr(res, "data") and res.data:
                # Standard OpenAI SDK response
                embedding = res.data[0].embedding  # type: ignore[attr-defined]
            else:
                # Try to parse as dict/JSON
                parsed = _to_dict(res)
                if isinstance(parsed, dict) and "data" in parsed and parsed["data"]:
                    embedding = parsed["data"][0]["embedding"]
                else:
                    # If it's a string, try to parse it as JSON
                    if isinstance(parsed, str):
                        try:
                            parsed = json.loads(parsed)
                            embedding = parsed["data"][0]["embedding"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            raise TypeError(f"Unexpected response format: {type(parsed)}")
                    else:
                        raise TypeError(f"Unexpected response format: {type(parsed)}")

            if not isinstance(embedding, list):
                raise TypeError("Embedding is not a list")
            return [float(x) for x in embedding]
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Embedding failed: {last_err}")

# Tool implementations
def get_all_memories(session_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """List memories (recent first)."""
    return list_memories(session_id, limit)

def search_memories_tool(query: str, session_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """Search memories using text search."""
    return search_memories(query, session_id, limit)

def find_object(object_name: str) -> Dict[str, Any]:
    """Not implemented with Helix yet."""
    return {"error": "find_object not implemented"}

def query_item_history(item_name: str, question: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """Not implemented with Helix yet."""
    return {"error": "query_item_history not implemented"}

def store_text_memory(text_summary: str, user_context: str = "", session_id: str = "default-session") -> Dict[str, Any]:
    """Store a text-based memory."""
    return add_memory(text_summary, user_context, session_id)

def get_statistics() -> Dict[str, Any]:
    """Get memory statistics."""
    return get_stats()

def track_item(item_name: str, alert_hours: int = 24, notes: str = "", session_id: str = "default-session") -> Dict[str, Any]:
    return {"error": "track_item not implemented"}

def untrack_item(item_name: str) -> Dict[str, Any]:
    return {"error": "untrack_item not implemented"}

def get_tracked_items() -> Dict[str, Any]:
    return {"error": "get_tracked_items not implemented"}

def get_relationships(item: Optional[str] = None) -> Dict[str, Any]:
    return {"error": "get_relationships not implemented"}

def process_image_for_memory(image_data: bytes) -> Dict[str, Any]:
    """Process image and generate description using AI"""
    try:
        # Convert image to base64 for AI processing
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Use Gemini model for vision analysis
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash-preview-09-2025",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in detail, focusing on objects, people, locations, and any important visual elements that would be useful for memory storage. Be specific about what you see."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        description = response.choices[0].message.content
        return {"success": True, "description": description}
        
    except Exception as e:
        return {"success": False, "error": f"Image processing failed: {str(e)}"}

def store_image_memory(image_description: str, user_context: str = "", session_id: str = "default-session") -> Dict[str, Any]:
    """Store an image memory with AI-generated description."""
    return add_memory(image_description, user_context, session_id)

# Direct memory operation tools
def add_memory_direct(description: str, user_context: str = "", session_id: str = "default-session") -> Dict[str, Any]:
    """Directly add a memory without AI processing."""
    return add_memory(description, user_context, session_id)

def list_memories_direct(session_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """Directly list memories without AI processing."""
    return list_memories(session_id, limit)

def search_memories_direct(query: str, session_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """Directly search memories without AI processing."""
    return search_memories(query, session_id, limit)

def delete_memory_direct(memory_id: str) -> Dict[str, Any]:
    """Directly delete a memory by ID."""
    return delete_memory(memory_id)

# Tool execution function
def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool with given parameters"""
    tool_functions = {
        "get_all_memories": get_all_memories,
        "search_memories": search_memories_tool,
        "find_object": find_object,
        "query_item_history": query_item_history,
        "store_text_memory": store_text_memory,
        "get_statistics": get_statistics,
        "track_item": track_item,
        "untrack_item": untrack_item,
        "get_tracked_items": get_tracked_items,
        "get_relationships": get_relationships,
        "store_image_memory": store_image_memory,
        "add_memory_direct": add_memory_direct,
        "list_memories_direct": list_memories_direct,
        "search_memories_direct": search_memories_direct,
        "delete_memory_direct": delete_memory_direct
    }
    
    if tool_name not in tool_functions:
        return {"error": f"Unknown tool: {tool_name}"}
    
    try:
        return tool_functions[tool_name](**parameters)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

# AI Agent function
def call_agent(user_text: str, session_id: str = "default-session") -> AgentResponse:
    """Call the AI agent to process user text and execute appropriate tools"""
    try:
        # Create the system prompt
        prompt_files = ["prompts/Prompt1.md", "prompts/Prompt2.md", "prompts/Prompt3.md", "prompts/Prompt4.md"]

        prompt_contents = []
        for prompt_file in prompt_files:
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_contents.append(f.read())
            except FileNotFoundError:
                print(f"Warning: Could not find {prompt_file}")
        
        combined_prompts = "\n\n".join(prompt_contents)

        system_prompt = f"""
        {combined_prompts}
        
        Remember to add if api response is 404 not found, this means that the memory for that is not found, or saved in the database / user's memory engine.
                
        You have access to the following tools:
        {json.dumps(TOOLS, indent=2)}

        Based on the user's input, decide which tool to call and with what parameters. Always respond with a JSON object containing:
        - "tool_name": the name of the tool to call
        - "parameters": the parameters for the tool

        User input: "{user_text}"
        Session ID: "{session_id}"

        Respond with only the JSON object, no other text.
        
        """

        response = client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        try:
            tool_decision = json.loads(ai_response)
            tool_name = tool_decision.get("tool_name")
            parameters = tool_decision.get("parameters", {})
            
            if not tool_name:
                return AgentResponse(
                    success=False,
                    message="AI agent did not specify a tool to use",
                    error="No tool_name in AI response"
                )
            
            # Execute the tool
            tool_result = execute_tool(tool_name, parameters)
            
            # Check if tool execution was successful
            if "error" in tool_result:
                return AgentResponse(
                    success=False,
                    message=f"Tool execution failed: {tool_result['error']}",
                    tool_used=tool_name,
                    error=tool_result["error"]
                )
            
            return AgentResponse(
                success=True,
                message="Tool executed successfully",
                data=tool_result,
                tool_used=tool_name
            )
            
        except json.JSONDecodeError:
            return AgentResponse(
                success=False,
                message="AI agent response was not valid JSON",
                error=f"Invalid JSON: {ai_response}"
            )
            
    except Exception as e:
        return AgentResponse(
            success=False,
            message=f"Agent call failed: {str(e)}",
            error=str(e)
        )

# API Endpoints
@app.post("/process", response_model=AgentResponse)
def process_text(request: AgentRequest):
    """Process transcribed text and return agent response"""
    return call_agent(request.text, request.session_id)

class ImageMemoryRequest(BaseModel):
    base64_image: str
    user_context: Optional[str] = ""
    session_id: Optional[str] = "default-session"

@app.post("/process-image")
async def process_image(request: ImageMemoryRequest):
    """Process base64 image and store as memory"""
    try:
        # Decode base64 image
        try:
            # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
            if ',' in request.base64_image:
                base64_data = request.base64_image.split(',')[1]
            else:
                base64_data = request.base64_image
                
            image_data = base64.b64decode(base64_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")
        
        # Process image to get description
        processing_result = process_image_for_memory(image_data)
        
        if not processing_result["success"]:
            raise HTTPException(status_code=500, detail=processing_result["error"])
        
        # Store as memory
        memory_result = store_image_memory(
            image_description=processing_result["description"],
            user_context=request.user_context,
            session_id=request.session_id
        )
        
        return AgentResponse(
            success=True,
            message=f"Image saved as memory: {processing_result['description'][:100]}...",
            data={
                "image_description": processing_result["description"],
                "user_context": request.user_context,
                "memory_result": memory_result
            },
            tool_used="store_image_memory"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return AgentResponse(
            success=False,
            message=f"Failed to process image: {str(e)}",
            error=str(e)
        )

@app.post("/process-image-file")
async def process_image_file(file: UploadFile = File(...), user_context: str = "", session_id: str = "default-session"):
    """Process uploaded image file and store as memory (legacy endpoint)"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Process image to get description
        processing_result = process_image_for_memory(image_data)
        
        if not processing_result["success"]:
            raise HTTPException(status_code=500, detail=processing_result["error"])
        
        # Store as memory
        memory_result = store_image_memory(
            image_description=processing_result["description"],
            user_context=user_context,
            session_id=session_id
        )
        
        return AgentResponse(
            success=True,
            message=f"Image saved as memory: {processing_result['description'][:100]}...",
            data={
                "image_description": processing_result["description"],
                "user_context": user_context,
                "memory_result": memory_result
            },
            tool_used="store_image_memory"
        )
        
    except Exception as e:
        return AgentResponse(
            success=False,
            message=f"Failed to process image: {str(e)}",
            error=str(e)
        )

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "memARy Voice Agent API is running", "version": "1.0.0"}

@app.get("/tools")
def get_available_tools():
    """Get list of available tools"""
    return {"tools": TOOLS}

@app.get("/memories")
def list_memories_endpoint(session_id: Optional[str] = None, limit: int = 100):
    """HTTP endpoint to list recent memories."""
    try:
        print(f"DEBUG: list_memories called with session_id={session_id}, limit={limit}")
        result = list_memories(session_id, limit)
        print(f"DEBUG: list_memories result: {result}")
        return result
    except Exception as e:
        print(f"DEBUG: Error in list_memories_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-agent")
def test_agent(request: AgentRequest):
    """Test endpoint that shows detailed information about the agent's decision process"""
    try:
        # Load prompts for display
        prompt_files = ["prompts/Prompt1.md", "prompts/Prompt2.md", "prompts/Prompt3.md", "prompts/Prompt4.md"]
        prompt_contents = []
        for prompt_file in prompt_files:
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_contents.append(f.read())
            except FileNotFoundError:
                prompt_contents.append(f"Could not find {prompt_file}")
        
        combined_prompts = "\n\n".join(prompt_contents)
        
        # Create the system prompt
        system_prompt = f"""
        {combined_prompts}
        
        Remember to add if api response is 404 not found, this means that the memory for that is not found, or saved in the database / user's memory engine.
                
        You have access to the following tools:
        {json.dumps(TOOLS, indent=2)}

        Based on the user's input, decide which tool to call and with what parameters. Always respond with a JSON object containing:
        - "tool_name": the name of the tool to call
        - "parameters": the parameters for the tool

        User input: "{request.text}"
        Session ID: "{request.session_id}"

        Respond with only the JSON object, no other text.
        
        """
        
        # Call the AI model
        response = client.chat.completions.create(
            model="openai/gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.text}
            ],
            temperature=0.1
        )
        
        # Parse the AI response
        ai_response = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        try:
            tool_decision = json.loads(ai_response)
            tool_name = tool_decision.get("tool_name")
            parameters = tool_decision.get("parameters", {})
            
            # Execute the tool
            tool_result = execute_tool(tool_name, parameters) if tool_name else {"error": "No tool specified"}
            
            return {
                "success": True,
                "user_input": request.text,
                "session_id": request.session_id,
                "ai_raw_response": ai_response,
                "parsed_tool_decision": tool_decision,
                "tool_execution_result": tool_result,
                "system_prompt_preview": system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": "AI response was not valid JSON",
                "ai_raw_response": ai_response,
                "json_error": str(e)
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Test failed: {str(e)}"
        }

@app.delete("/memories/{memory_id}")
def delete_memory_endpoint(memory_id: str):
    """Delete a memory by ID"""
    try:
        result = delete_memory(memory_id)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/system-prompt")
def get_system_prompt():
    """Get the current system prompt for debugging"""
    try:
        prompt_files = ["prompts/Prompt1.md", "prompts/Prompt2.md", "prompts/Prompt3.md", "prompts/Prompt4.md"]
        prompt_contents = []
        for prompt_file in prompt_files:
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_contents.append(f"=== {prompt_file} ===\n{f.read()}")
            except FileNotFoundError:
                prompt_contents.append(f"=== {prompt_file} ===\nCould not find file")
        
        return {
            "prompt_files": prompt_files,
            "combined_prompts": "\n\n".join(prompt_contents),
            "tools": TOOLS
        }
    except Exception as e:
        return {"error": f"Failed to load system prompt: {str(e)}"}

@app.post("/test-tool")
def test_tool_directly(tool_name: str, parameters: Dict[str, Any]):
    """Test a tool directly without going through the AI agent"""
    try:
        result = execute_tool(tool_name, parameters)
        return {
            "success": True,
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }

# ASGI application for Gunicorn
asgi_app = app

def main(): 
    print("Hello from memary-voice agent!")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()