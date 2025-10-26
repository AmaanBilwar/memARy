from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import uvicorn
import os 
from dotenv import load_dotenv
import requests
import json
from openai import OpenAI

load_dotenv()

OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")
CHROMADB_BASE_URL=os.getenv("CHROMADB_BASE_URL")

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
    }
]

# Helper function for API calls
def make_api_call(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Helper function to make API calls with error handling"""
    try:
        url = f"{CHROMADB_BASE_URL}{endpoint}"
        response = requests.request(method, url, **kwargs)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API request failed with status {response.status_code}",
                "details": response.text
            }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Request failed: {str(e)}",
            "details": None
        }

# Tool implementations
def get_all_memories(session_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """Get all stored memories"""
    params = {"limit": limit}
    if session_id:
        params["session_id"] = session_id
    return make_api_call("GET", "/memories", params=params)

def search_memories(query: str, session_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """Search through memories using natural language"""
    params = {"query": query, "limit": limit}
    if session_id:
        params["session_id"] = session_id
    return make_api_call("GET", "/search", params=params)

def find_object(object_name: str) -> Dict[str, Any]:
    """Find where a specific object was last seen"""
    return make_api_call("GET", f"/find/{object_name}")

def query_item_history(item_name: str, question: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """Get detailed history of a specific item"""
    params = {"limit": limit}
    if question:
        params["question"] = question
    return make_api_call("GET", f"/item/{item_name}", params=params)

def store_text_memory(text_summary: str, session_id: str = "default-session") -> Dict[str, Any]:
    """Store a text-based memory"""
    data = {"text_summary": text_summary, "session_id": session_id}
    return make_api_call("POST", "/store_text", json=data)

def get_statistics() -> Dict[str, Any]:
    """Get statistics about stored memories"""
    return make_api_call("GET", "/statistics")

def track_item(item_name: str, alert_hours: int = 24, notes: str = "", session_id: str = "default-session") -> Dict[str, Any]:
    """Start tracking an item"""
    data = {"item_name": item_name, "alert_hours": alert_hours, "notes": notes}
    return make_api_call("POST", "/track_item", json=data)

def untrack_item(item_name: str) -> Dict[str, Any]:
    """Stop tracking an item"""
    return make_api_call("DELETE", f"/track_item/{item_name}")

def get_tracked_items() -> Dict[str, Any]:
    """Get all currently tracked items"""
    return make_api_call("GET", "/tracked_items")

def get_relationships(item: Optional[str] = None) -> Dict[str, Any]:
    """Get relationships between objects"""
    params = {}
    if item:
        params["item"] = item
    return make_api_call("GET", "/relationships", params=params)

# Tool execution function
def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool with given parameters"""
    tool_functions = {
        "get_all_memories": get_all_memories,
        "search_memories": search_memories,
        "find_object": find_object,
        "query_item_history": query_item_history,
        "store_text_memory": store_text_memory,
        "get_statistics": get_statistics,
        "track_item": track_item,
        "untrack_item": untrack_item,
        "get_tracked_items": get_tracked_items,
        "get_relationships": get_relationships
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

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "memARy Voice Agent API is running", "version": "1.0.0"}

@app.get("/tools")
def get_available_tools():
    """Get list of available tools"""
    return {"tools": TOOLS}

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