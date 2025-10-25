#!/bin/bash
# Stop all Remembar services

echo "🛑 Stopping Remembar Services..."
echo ""

# Kill processes on ports
echo "Stopping API Service (port 8000)..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "   ✓ API Service stopped" || echo "   ℹ️  No process on port 8000"

echo "Stopping Vector Store (port 8001)..."
lsof -ti:8001 | xargs kill -9 2>/dev/null && echo "   ✓ Vector Store stopped" || echo "   ℹ️  No process on port 8001"

echo ""
echo "✅ All services stopped"


