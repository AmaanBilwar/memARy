#!/bin/bash
# Deploy with Basic Authentication (secure your public API)

set -e

cd /Users/arkanfadhilkautsar/Downloads/memary

# Activate virtual environment if it exists
if [ -d "env" ]; then
    echo "🔧 Activating virtual environment..."
    source env/bin/activate
fi

echo "🔒 Starting Memary API with Basic Auth Security"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Kill existing services
echo "🧹 Cleaning up..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
sleep 1

# Create logs directory
mkdir -p logs

# Start Vector Store
echo "📊 Starting Vector Store (port 8001)..."
cd vector-store
python3 app.py > ../logs/vector-store.log 2>&1 &
VECTOR_PID=$!
cd ..

# Wait for vector store to be ready (with timeout)
echo "   Waiting for Vector Store to start..."
for i in {1..30}; do
    if curl -s http://localhost:8001/healthz | grep -q "ok"; then
        echo "   ✅ Vector Store: Ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ⚠️  Vector Store: Timeout (continuing anyway)"
    fi
    sleep 1
done

# Start API Service
echo "🔧 Starting API Service (port 8000)..."
cd api-service
python3 main.py > ../logs/api-service.log 2>&1 &
API_PID=$!
cd ..

# Wait for API service to be ready (with timeout)
echo "   Waiting for API Service to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/ | grep -q "memory-api"; then
        echo "   ✅ API Service: Ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ API Service: Failed to start"
        tail -20 logs/api-service.log
        exit 1
    fi
    sleep 1
done

# Verify vector store connection
echo ""
echo "🔍 Testing connections..."
if curl -s http://localhost:8001/healthz | grep -q "ok"; then
    echo "   ✅ Vector Store: Connected"
    VECTOR_STATUS="connected"
else
    echo "   ⚠️  Vector Store: Not available (will use in-memory fallback)"
    VECTOR_STATUS="fallback"
fi

if curl -s http://localhost:8000/ | grep -q "memory-api"; then
    echo "   ✅ API Service: Connected"
else
    echo "   ❌ API Service: Not responding"
    exit 1
fi

# Create traffic policy file for basic auth
cat > traffic-policy.yml << 'EOF'
on_http_request:
  - actions:
      - type: basic-auth
        config:
          credentials:
            - admin:SecurePassword123
            - user:UserPassword456
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ALL SERVICES READY WITH BASIC AUTH!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Local Services:"
echo "   • API Service:      http://localhost:8000"
echo "   • Vector Store:     http://localhost:8001 ($VECTOR_STATUS)"
echo ""
echo "🔒 Authentication Credentials:"
echo "   • Username: admin  | Password: SecurePassword123"
echo "   • Username: user   | Password: UserPassword456"
echo ""
echo "🌐 Starting ngrok with authentication..."
echo "   • Public API:       https://memary-chromadb.ngrok-free.app"
echo "   • Dashboard:        http://localhost:4040"
echo ""
if [ "$VECTOR_STATUS" = "connected" ]; then
    echo "✅ Images will be stored in ChromaDB"
else
    echo "⚠️  Images will be stored in-memory only"
fi
echo ""
echo "📝 Test with:"
echo "   curl -u admin:SecurePassword123 https://memary-chromadb.ngrok-free.app/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Trap to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $API_PID $VECTOR_PID 2>/dev/null || true
    rm -f traffic-policy.yml
    echo "✅ Services stopped"
}
trap cleanup EXIT INT TERM

# Start ngrok with basic auth
ngrok http 8000 \
  --url https://memary-chromadb.ngrok-free.app \
  --traffic-policy-file traffic-policy.yml

