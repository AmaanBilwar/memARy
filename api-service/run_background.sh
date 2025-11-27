#!/bin/bash

echo "Starting Memory API in background..."

# Run in background with nohup
nohup uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-level info \
  > api.log 2>&1 &

# Save PID
echo $! > api.pid

echo "✓ API started in background"
echo "✓ PID: $(cat api.pid)"
echo "✓ Logs: api.log"
echo ""
echo "To stop: kill \$(cat api.pid)"

