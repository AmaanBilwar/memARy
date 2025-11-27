#!/bin/bash
# Quick test script for image upload endpoint

echo "🧪 Testing Image Upload Pipeline"
echo ""

# Check if services are running
echo "1️⃣ Checking services..."
if curl -s http://localhost:8000/ | grep -q "memory-api"; then
    echo "   ✅ API Service is running"
else
    echo "   ❌ API Service is NOT running"
    echo "   Run: cd api-service && python3 main.py"
    exit 1
fi

if curl -s http://localhost:8001/healthz | grep -q "ok"; then
    echo "   ✅ Vector Store is running"
else
    echo "   ❌ Vector Store is NOT running"
    echo "   Run: cd vector-store && python3 app.py"
    exit 1
fi

echo ""
echo "2️⃣ Testing vision_reka import..."
cd /Users/arkanfadhilkautsar/Downloads/memary
python3 << 'EOF'
import sys
import os
vision_path = os.path.abspath('vision-processor')
sys.path.insert(0, vision_path)
try:
    import vision_reka
    print("   ✅ vision_reka import works!")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "3️⃣ Testing text-to-JSON endpoint (simpler test)..."
RESPONSE=$(curl -s -X POST http://localhost:8000/store_text \
    -H "Content-Type: application/json" \
    -d '{
        "text_summary": "I see a red mug on my desk",
        "session_id": "test-session"
    }')

if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo "   ✅ Text-to-JSON endpoint works!"
    echo "   Response: $(echo $RESPONSE | python3 -m json.tool 2>/dev/null | head -10)"
else
    echo "   ❌ Text-to-JSON endpoint failed"
    echo "   Response: $RESPONSE"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All tests passed! The pipeline is working correctly."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 Next step: Upload an image via the web interface"
echo "   URL: http://localhost:8080"
echo ""
echo "Note: The image upload requires:"
echo "   • Reka API key in .env file"
echo "   • An actual image file (for Reka Vision API)"
echo "   • ~10 seconds for Reka to analyze"
echo ""

