#!/bin/bash

echo "Starting Memory API in production mode..."

# Run with uvicorn (production ASGI server)
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-level info \
  --no-access-log

# For high traffic, increase workers:
# --workers 4

