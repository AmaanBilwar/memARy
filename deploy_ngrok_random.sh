#!/bin/bash
# Deploy with random ngrok URL (fastest method, no custom domain needed)

set -e

cd /Users/arkanfadhilkautsar/Downloads/memary

# Activate virtual environment if it exists
if [ -d "env" ]; then
    echo "🔧 Activating virtual environment..."
    source env/bin/activate
fi

echo "🚀 Starting Memary API with Random Ngrok URL"
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
cd ..
sleep 3

# Start API Service
echo "🔧 Starting API Service (port 8000)..."
cd api-service
python3 main.py > ../logs/api-service.log 2>&1 &
cd ..
sleep 3

# Health check
echo ""
echo "🔍 Health check..."
if curl -s http://localhost:8000/ | grep -q "memory-api"; then
    echo "   ✅ API Service: Running"
else
    echo "   ❌ API Service: Failed"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ API running on port 8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Starting ngrok tunnel with RANDOM URL..."
echo ""
echo "📝 Your URL will be shown below (changes each time)"
echo "🎛️  Dashboard at: http://localhost:4040"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start ngrok with random URL (simplest method)
ngrok http 8000

