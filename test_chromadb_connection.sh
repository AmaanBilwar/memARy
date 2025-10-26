#!/bin/bash
# Test script to verify ChromaDB storage is working

cd /Users/arkanfadhilkautsar/Downloads/memary

# Activate virtual environment if it exists
if [ -d "env" ]; then
    source env/bin/activate
fi

echo "🧪 Testing ChromaDB Connection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test Vector Store
echo "1️⃣ Testing Vector Store (port 8001)..."
if curl -s http://localhost:8001/healthz | grep -q "ok"; then
    echo "   ✅ Vector Store is running"
    echo ""
    curl -s http://localhost:8001/healthz | python3 -m json.tool
else
    echo "   ❌ Vector Store is NOT running"
    echo "   Start it with: cd vector-store && python3 app.py"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test API Service
echo "2️⃣ Testing API Service (port 8000)..."
if curl -s http://localhost:8000/ | grep -q "memory-api"; then
    echo "   ✅ API Service is running"
else
    echo "   ❌ API Service is NOT running"
    echo "   Start it with: cd api-service && python3 main.py"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test storing data
echo "3️⃣ Testing data storage..."
RESPONSE=$(curl -s -X POST http://localhost:8000/store_text \
  -H "Content-Type: application/json" \
  -d '{
    "text_summary": "Test: A red coffee mug on the desk",
    "session_id": "chromadb-test"
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool | head -30

# Check if vector store was used
if echo "$RESPONSE" | grep -q '"mode": "vector_store"'; then
    echo ""
    echo "✅ SUCCESS: Data stored in ChromaDB!"
elif echo "$RESPONSE" | grep -q '"mode": "in_memory_only"'; then
    echo ""
    echo "⚠️  WARNING: Data stored in memory only (ChromaDB not connected)"
    echo "   Check vector store logs: tail -f /tmp/vector-store.log"
else
    echo ""
    echo "❌ ERROR: Could not determine storage mode"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Summary
echo "📊 Summary:"
echo "   • Vector Store: $(curl -s http://localhost:8001/healthz >/dev/null 2>&1 && echo '✅ Running' || echo '❌ Down')"
echo "   • API Service:  $(curl -s http://localhost:8000/ >/dev/null 2>&1 && echo '✅ Running' || echo '❌ Down')"

if echo "$RESPONSE" | grep -q '"mode": "vector_store"'; then
    echo "   • ChromaDB:     ✅ Connected and storing data"
else
    echo "   • ChromaDB:     ⚠️  Not connected (using fallback)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

