#!/bin/bash
# Vector Store Startup Script with Telemetry Disabled

# Disable ChromaDB/PostHog telemetry completely
export ANONYMIZED_TELEMETRY=False
export CHROMA_TELEMETRY_DISABLED=1
export POSTHOG_DISABLED=1

# Additional safety measures
export TELEMETRY_DISABLED=1
export DO_NOT_TRACK=1

echo "🚀 Starting Vector Store with telemetry DISABLED"
echo "   Environment variables set:"
echo "   - ANONYMIZED_TELEMETRY=False"
echo "   - CHROMA_TELEMETRY_DISABLED=1"
echo "   - POSTHOG_DISABLED=1"
echo ""

# Run the app
python3 app.py

