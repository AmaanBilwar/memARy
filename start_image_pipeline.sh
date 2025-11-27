#!/bin/bash
# Start all services for the image upload pipeline

echo "🚀 Starting Image Upload Pipeline Services..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check for REKA_API_KEY
if [ -z "$REKA_API_KEY" ]; then
    if [ -f "vision-processor/.env" ]; then
        echo "✓ Found .env file in vision-processor"
        export $(cat vision-processor/.env | grep REKA_API_KEY | xargs)
    elif [ -f ".env" ]; then
        echo "✓ Found .env file in root"
        export $(cat .env | grep REKA_API_KEY | xargs)
    else
        echo "⚠️  WARNING: REKA_API_KEY not found!"
        echo "   Create a .env file with: REKA_API_KEY=your_key_here"
        echo ""
    fi
fi

# Kill any existing services
echo "🧹 Cleaning up existing services..."
pkill -f "python3.*app.py" 2>/dev/null
pkill -f "python3.*main.py" 2>/dev/null
pkill -f "http.server" 2>/dev/null
sleep 1

# Start Vector Store (port 8001)
echo "📊 Starting Vector Store (port 8001)..."
cd vector-store
python3 app.py > ../logs/vector-store.log 2>&1 &
VECTOR_PID=$!
cd ..

# Wait for vector store to start
sleep 2

# Start API Service (port 8000)
echo "🔧 Starting API Service (port 8000)..."
cd api-service
python3 main.py > ../logs/api-service.log 2>&1 &
API_PID=$!
cd ..

# Wait for API service to start
sleep 2

# Start Web Server (port 8080)
echo "🌐 Starting Web Interface (port 8080)..."
cd web-test
python3 -m http.server 8080 > ../logs/web-server.log 2>&1 &
WEB_PID=$!
cd ..

# Create logs directory if it doesn't exist
mkdir -p logs

# Wait a bit for everything to start
sleep 2

echo ""
echo "✅ All services started!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📸 Image Upload Pipeline is Ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🌐 Web Interface:    http://localhost:8080"
echo "  🔧 API Service:      http://localhost:8000"
echo "  📊 Vector Store:     http://localhost:8001"
echo ""
echo "  📝 Logs directory:   ./logs/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To stop all services, run: ./stop_services.sh"
echo "Or press Ctrl+C and run: pkill -f 'python3.*app.py|python3.*main.py|http.server'"
echo ""

# Test services
echo "🔍 Testing services..."
sleep 1

if curl -s http://localhost:8000/ | grep -q "memory-api"; then
    echo "  ✓ API Service: Running"
else
    echo "  ✗ API Service: Failed to start (check logs/api-service.log)"
fi

if curl -s http://localhost:8001/healthz | grep -q "ok"; then
    echo "  ✓ Vector Store: Running"
else
    echo "  ✗ Vector Store: Failed to start (check logs/vector-store.log)"
fi

if curl -s http://localhost:8080/ | grep -q "Remembar"; then
    echo "  ✓ Web Interface: Running"
else
    echo "  ✗ Web Interface: Failed to start (check logs/web-server.log)"
fi

echo ""
echo "🎉 Ready to upload images! Open http://localhost:8080 in your browser."
echo ""

# Keep script running
echo "Press Ctrl+C to stop all services..."
wait

