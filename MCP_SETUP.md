# Remembar MCP Setup Guide

Connect Remembar to Claude Desktop or other MCP-compatible AI assistants!

## What is MCP?

Model Context Protocol (MCP) is an open protocol that lets AI assistants access external data sources and tools. With Remembar's MCP server, you can ask Claude to remember things and search your memories naturally!

## Prerequisites

- Python 3.9+
- Remembar API server running (`python3 api-service/main.py`)
- Claude Desktop (or another MCP-compatible client)

## Quick Setup

### Step 1: Install Dependencies

```bash
cd api-service
pip3 install -r requirements.txt
```

### Step 2: Start the Remembar API Server

```bash
cd api-service
python3 main.py
```

The API should be running at `http://localhost:8000`

### Step 3: Configure Claude Desktop

1. **Find your Claude Desktop config file:**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Edit the config file** (create it if it doesn't exist):

```json
{
  "mcpServers": {
    "remembar": {
      "command": "python3",
      "args": [
        "/FULL/PATH/TO/remembar/api-service/mcp_server.py"
      ],
      "env": {
        "REMEMBAR_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

**Important:** Replace `/FULL/PATH/TO/remembar` with the actual path to your Remembar installation!

3. **Restart Claude Desktop**

### Step 4: Test It!

Open Claude Desktop and try:

- **"I saw a yellow key on the table"** - Claude will store this memory
- **"What color is the key?"** - Claude will search and answer
- **"Show me my memory timeline"** - Claude will show all memories grouped by date
- **"Track my medication and alert me if I haven't seen it in 12 hours"** - Claude will set up tracking

## Available Tools

Once connected, Claude Desktop can use these Remembar tools:

### 🧠 Memory Operations

- **`store_memory`** - Store a new observation/memory
- **`search_memories`** - Search memories with natural language
- **`get_timeline`** - Get memories organized by date

### 📌 Tracking & Alerts

- **`track_item`** - Add an item to track with alerts
- **`get_tracked_items`** - See all tracked items and their status

### 📊 Analytics

- **`get_statistics`** - Get comprehensive memory stats
- **`get_flashcards`** - Generate memory reinforcement flashcards

### 🗑️ Management

- **`clear_storage`** - Clear all memories (use with caution!)

## Example Conversations

### Example 1: Storing Memories

```
You: I just saw my wallet on the kitchen counter next to a blue mug
Claude: [uses store_memory tool]
✓ I've stored that memory! You saw:
- wallet (on kitchen counter)
- mug (blue, on kitchen counter)
```

### Example 2: Searching

```
You: Where did I leave my wallet?
Claude: [uses search_memories tool]
Your wallet was on the kitchen counter, last seen 2 minutes ago. 
It was next to a blue mug.
```

### Example 3: Tracking Important Items

```
You: Can you remind me where my keys are if I search for them?
Claude: [uses track_item tool]
✓ Now tracking 'keys'. I'll let you know when you search for them 
and alert if they haven't been seen for 24 hours.
```

## Troubleshooting

### Claude Desktop doesn't show Remembar tools

1. Check that the config file path is correct
2. Ensure the full path to `mcp_server.py` is absolute (not relative)
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### "Could not connect to Remembar API" error

1. Make sure the API server is running: `python3 api-service/main.py`
2. Verify it's accessible at `http://localhost:8000`
3. Check that no firewall is blocking port 8000

### Permission errors

Make sure `mcp_server.py` is executable:
```bash
chmod +x api-service/mcp_server.py
```

## Advanced Configuration

### Using a Different Port

If your API runs on a different port, update the config:

```json
{
  "mcpServers": {
    "remembar": {
      "command": "python3",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "REMEMBAR_API_URL": "http://localhost:9000"
      }
    }
  }
}
```

### Remote API Server

To connect to a remote Remembar instance:

```json
{
  "env": {
    "REMEMBAR_API_URL": "https://your-remembar-instance.com"
  }
}
```

## Architecture

```
┌─────────────────────┐
│  Claude Desktop     │
│  (MCP Client)       │
└──────────┬──────────┘
           │ stdio
           │ (JSON-RPC)
           ↓
┌─────────────────────┐
│  mcp_server.py      │
│  (MCP Server)       │
└──────────┬──────────┘
           │ HTTP
           │ REST API
           ↓
┌─────────────────────┐
│  main.py            │
│  (Remembar API)     │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│  ChromaDB           │
│  (Vector Store)     │
└─────────────────────┘
```

## Next Steps

- Try voice input with Claude Desktop for hands-free memory storage
- Set up tracked items for important belongings
- Use flashcards for memory training
- Explore timeline view to see patterns in your observations

## Resources

- **MCP Documentation**: https://modelcontextprotocol.io
- **Claude Desktop**: https://claude.ai/download
- **Remembar GitHub**: [Your repository URL]

---

**Happy Memory Tracking! 🧠✨**

