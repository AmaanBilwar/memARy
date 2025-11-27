#!/bin/bash
# Auto-start script for Remembar services

echo "🚀 Starting Remembar Services..."
echo ""

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Kill any existing processes on these ports
echo "🧹 Cleaning up existing processes..."
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start Vector Store (port 8001)
echo ""
echo "📦 Starting Vector Store (port 8001)..."
cd "$DIR/vector-store"
source venv/bin/activate
python3 app.py > vectorstore.log 2>&1 &
VECTOR_PID=$!
echo "   ✓ Vector Store PID: $VECTOR_PID"

# Wait for vector store to be ready
echo "   ⏳ Waiting for vector store..."
sleep 5

# Start API Service (port 8000)
echo ""
echo "🔌 Starting API Service (port 8000)..."
cd "$DIR/api-service"
python3 main.py > api.log 2>&1 &
API_PID=$!
echo "   ✓ API Service PID: $API_PID"

# Wait for API to be ready
sleep 3

# Check if services are running
echo ""
echo "🔍 Checking services..."
if curl -s http://localhost:8001/health > /dev/null 2>&1 || curl -s http://localhost:8001/ > /dev/null 2>&1; then
    echo "   ✅ Vector Store: Running"
else
    echo "   ⚠️  Vector Store: Not responding (check vectorstore.log)"
fi

if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "   ✅ API Service: Running"
else
    echo "   ⚠️  API Service: Not responding (check api.log)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Services Started!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Endpoints:"
echo "   • API Service:    http://localhost:8000"
echo "   • Vector Store:   http://localhost:8001"
echo "   • Web Interface:  file://$DIR/web-test/index.html"
echo ""
echo "📝 Logs:"
echo "   • Vector Store:   $DIR/vector-store/vectorstore.log"
echo "   • API Service:    $DIR/api-service/api.log"
echo ""
echo "🛑 To stop services, run: ./stop_services.sh"
echo "🗑️  To clear storage, use the web interface or run: curl -X POST http://localhost:8000/clear_storage"
echo ""

# Open web interface
if command -v open &> /dev/null; then
    sleep 1
    open "$DIR/web-test/index.html"
fi


