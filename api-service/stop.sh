#!/bin/bash

if [ -f api.pid ]; then
    PID=$(cat api.pid)
    echo "Stopping API (PID: $PID)..."
    kill $PID 2>/dev/null
    rm api.pid
    echo "✓ API stopped"
else
    echo "No PID file found. API may not be running."
    echo "Checking for uvicorn processes..."
    pkill -f "uvicorn main:app"
fi

