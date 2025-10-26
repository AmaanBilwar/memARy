"""
ASGI entry point for FastAPI application
This file provides compatibility with ASGI servers like Gunicorn with uvicorn workers
"""
import os
from main import app

# For ASGI compatibility, we expose the FastAPI app directly
# Gunicorn with uvicorn workers will handle the ASGI protocol
application = app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
