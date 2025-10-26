"""
WSGI entry point for FastAPI application
This file provides compatibility with WSGI servers like Gunicorn
"""
import os
from main import app

# For WSGI compatibility, we need to expose the ASGI app
# Gunicorn with uvicorn workers will handle the ASGI conversion
application = app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
