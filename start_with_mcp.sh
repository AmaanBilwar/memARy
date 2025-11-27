#!/bin/bash
# Start Remembar with MCP support

set -e

echo "🧠 Starting Remembar with MCP Support"
echo "======================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if vector store needs to be started
echo "1️⃣  Checking Vector Store..."
if ! curl -s http://localhost:8001/ > /dev/null 2>&1; then
    echo "   Starting Vector Store..."
    cd "$SCRIPT_DIR/vector-store"
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    nohup python3 app.py > vectorstore.log 2>&1 &
    echo "   ✓ Vector Store starting (PID: $!)"
    sleep 2
else
    echo "   ✓ Vector Store already running"
fi

# Start API service
echo ""
echo "2️⃣  Starting API Service..."
cd "$SCRIPT_DIR/api-service"

# Kill any existing API process
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Check if requirements are installed
if ! python3 -c "import mcp" 2>/dev/null; then
    echo "   Installing dependencies..."
    pip3 install -r requirements.txt --quiet
fi

# Start the API
nohup python3 main.py > api.log 2>&1 &
API_PID=$!
echo "   ✓ API Service starting (PID: $API_PID)"
sleep 3

# Check if API is running
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "   ✓ API is healthy at http://localhost:8000"
else
    echo "   ⚠️  API may not be ready yet, check api-service/api.log"
fi

echo ""
echo "3️⃣  MCP Server Ready!"
echo ""
echo "📋 Next Steps:"
echo ""
echo "   A. For Claude Desktop:"
echo "      1. Edit your Claude config file:"
echo "         macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "         Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
echo "         Linux:   ~/.config/Claude/claude_desktop_config.json"
echo ""
echo "      2. Add this configuration:"
echo '         {
           "mcpServers": {
             "remembar": {
               "command": "python3",
               "args": ["'$SCRIPT_DIR'/api-service/mcp_server.py"],
               "env": {
                 "REMEMBAR_API_URL": "http://localhost:8000"
               }
             }
           }
         }'
echo ""
echo "      3. Restart Claude Desktop"
echo ""
echo "   B. For web interface:"
echo "      Open: $SCRIPT_DIR/web-test/index.html"
echo ""
echo "   C. To test MCP directly:"
echo "      python3 $SCRIPT_DIR/api-service/mcp_server.py"
echo ""
echo "🎯 Status Check:"
echo "   Vector Store:  http://localhost:8001"
echo "   API Service:   http://localhost:8000"
echo "   Web Interface: $SCRIPT_DIR/web-test/index.html"
echo ""
echo "📖 Full MCP setup guide: $SCRIPT_DIR/MCP_SETUP.md"
echo ""
echo "✅ Remembar is ready!"

