#!/bin/bash

echo "Testing API..."
echo ""

echo "1. Store data:"
curl -X POST http://localhost:8000/store \
  -H "Content-Type: application/json" \
  -d '{"scene": "Kitchen with keys on counter", "objects": [{"label": "keys", "confidence": 0.95, "is_person": false}]}'

echo -e "\n\n2. Find keys:"
curl http://localhost:8000/find/keys

echo -e "\n\n3. Search for 'keys':"
curl "http://localhost:8000/search?q=keys&limit=5"

echo -e "\n\nDone!"

