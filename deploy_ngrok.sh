#!/bin/bash
# Deploy memary image pipeline with ngrok agent

set -e

cd /Users/arkanfadhilkautsar/Downloads/memary

echo "🚀 Starting Memary Image Pipeline with Ngrok Agent"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Kill any existing services
echo "🧹 Cleaning up existing services..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
sleep 1

# Create logs directory
mkdir -p logs

# Start Vector Store (run from vector-store directory to use correct .chroma path)
echo "📊 Starting Vector Store (port 8001)..."
(cd vector-store && python3 app.py > ../logs/vector-store.log 2>&1) &
VECTOR_PID=$!
sleep 3

# Start API Service (run from api-service directory)
echo "🔧 Starting API Service (port 8000)..."
(cd api-service && python3 main.py > ../logs/api-service.log 2>&1) &
API_PID=$!
sleep 3

# Start Web Interface (run from web-test directory)
echo "🌐 Starting Web Interface (port 8080)..."
(cd web-test && python3 -m http.server 8080 > ../logs/web-server.log 2>&1) &
WEB_PID=$!
sleep 2

# Health check
echo ""
echo "🔍 Running health checks..."
if curl -s http://localhost:8000/ | grep -q "memory-api"; then
    echo "   ✅ API Service: Running (port 8000)"
else
    echo "   ❌ API Service: Failed to start"
    echo "   Check logs: tail -f logs/api-service.log"
    exit 1
fi

if curl -s http://localhost:8001/healthz | grep -q "ok"; then
    echo "   ✅ Vector Store: Running (port 8001)"
else
    echo "   ⚠️  Vector Store: Fallback mode (in-memory)"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ | grep -q "200"; then
    echo "   ✅ Web Interface: Running (port 8080)"
else
    echo "   ❌ Web Interface: Failed to start"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All local services started!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Local URLs:"
echo "   • API Service:      http://localhost:8000"
echo "   • Vector Store:     http://localhost:8001"  
echo "   • Web Interface:    http://localhost:8080"
echo ""
echo "🌐 Starting ngrok tunnels..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏳ Ngrok will show public URLs in a moment..."
echo ""
echo "🎛️  View all tunnels and traffic at: http://localhost:4040"
echo ""
echo "💡 Tips:"
echo "   • Press Ctrl+C to stop all services"
echo "   • Check logs in: ./logs/"
echo "   • Test API: curl https://YOUR-NGROK-URL.ngrok.io/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Save PIDs for cleanup
echo $API_PID > /tmp/memary-api.pid
echo $VECTOR_PID > /tmp/memary-vector.pid
echo $WEB_PID > /tmp/memary-web.pid

# Trap to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $API_PID $VECTOR_PID $WEB_PID 2>/dev/null || true
    rm -f /tmp/memary-*.pid
    echo "✅ Services stopped"
}
trap cleanup EXIT INT TERM

# Start ngrok with config file
ngrok start --all --config ngrok.yml


