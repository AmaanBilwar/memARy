QUICK START
===========

1. Install:
   pip install "fastapi[standard]" httpx

2. Start vector store (Terminal 1):
   cd ../vector-store
   python app.py

3. Start API service (Terminal 2):
   cd api-service
   fastapi dev main.py

4. Test:
   Open http://localhost:8000/docs

EXAMPLES
========

Store:
  POST http://localhost:8000/store
  Body: {"scene": "Keys on table", "objects": [{"label": "keys", "confidence": 0.9, "is_person": false}]}

Find:
  GET http://localhost:8000/find/keys

Search:
  GET http://localhost:8000/search?q=red%20mug&limit=5

