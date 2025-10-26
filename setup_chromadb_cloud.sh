#!/bin/bash
# Setup ChromaDB Cloud Configuration

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║              🌐 ChromaDB Cloud Setup for Memary                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if API key is provided
if [ -z "$1" ]; then
    echo "❌ ERROR: ChromaDB API Key required!"
    echo ""
    echo "📖 HOW TO GET YOUR API KEY:"
    echo "   1. Go to: https://www.trychroma.com/"
    echo "   2. Login to your account (arkankau)"
    echo "   3. Go to Settings → API Keys"
    echo "   4. Copy your API key"
    echo ""
    echo "💡 USAGE:"
    echo "   ./setup_chromadb_cloud.sh YOUR_API_KEY_HERE"
    echo ""
    exit 1
fi

API_KEY="$1"

echo "✅ Creating .env file with ChromaDB Cloud configuration..."
echo ""

# Create .env file
cat > .env << EOF
# ChromaDB Cloud Configuration
USE_CHROMA_CLOUD=true
CHROMA_TENANT=arkankau
CHROMA_DATABASE=remembar
CHROMA_API_KEY=$API_KEY

# Vector Store
VECTOR_STORE_URL=http://localhost:8001

# Other settings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EOF

echo "✅ .env file created!"
echo ""
echo "📋 Configuration:"
echo "   • Tenant: arkankau"
echo "   • Database: remembar"
echo "   • Cloud URL: https://www.trychroma.com/arkankau/remembar/"
echo ""
echo "🚀 Next Steps:"
echo "   1. Stop current services: killall python3 ngrok"
echo "   2. Start with cloud: ./deploy_ngrok.sh"
echo ""
echo "✅ All data will now sync to ChromaDB Cloud!"
echo ""
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

