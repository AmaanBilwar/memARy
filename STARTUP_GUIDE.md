# Remembar Startup Guide

## 🚀 Quick Start (Automatic)

### Start All Services
```bash
./start_services.sh
```

This will:
- ✅ Start Vector Store (port 8001) - Persistent storage
- ✅ Start API Service (port 8000) - Main API
- ✅ Open web interface automatically
- ✅ Display service status and endpoints

### Stop All Services
```bash
./stop_services.sh
```

## 📦 What's Running

### Vector Store (Port 8001)
- **Purpose**: Persistent database for memories
- **Storage**: `.chroma/` directory (keeps data across restarts)
- **Log**: `vector-store/vectorstore.log`

### API Service (Port 8000)
- **Purpose**: Main API for text-to-JSON conversion and search
- **Storage**: In-memory + Vector Store
- **Log**: `api-service/api.log`

## 🗑️ Clear Storage

### Option 1: Web Interface
1. Open the web interface
2. Click "🗑️ Clear All Storage" button at the top
3. Confirm the deletion

### Option 2: Command Line
```bash
curl -X POST http://localhost:8000/clear_storage
```

### Option 3: Delete Database Files
```bash
# Stop services first
./stop_services.sh

# Delete persistent storage
rm -rf vector-store/.chroma

# Start services again
./start_services.sh
```

## 📊 Storage Persistence

### ✅ Data IS Persistent When:
- Vector Store is running (port 8001)
- Stored in: `vector-store/.chroma/`
- Survives restarts

### ❌ Data is NOT Persistent When:
- Only API service is running (vector store down)
- Data stored in-memory only
- Lost on restart

## 🔍 Check Service Status

```bash
# Check if services are running
curl http://localhost:8000/  # API Service
curl http://localhost:8001/healthz  # Vector Store

# View logs
tail -f api-service/api.log
tail -f vector-store/vectorstore.log
```

## 🌐 Web Interface

The web interface opens automatically, or access it at:
```
file:///Users/arkanfadhilkautsar/Downloads/remembar/web-test/index.html
```

### Features:
- 📝 **Text to JSON**: Convert descriptions to structured data
- 🔍 **Search**: Find stored memories with natural language
- 🗑️ **Clear Storage**: Delete all memories (with confirmation)

## 🔧 Manual Start (Advanced)

If you prefer to start services manually:

### Terminal 1 - Vector Store
```bash
cd vector-store
source venv/bin/activate  # If using venv
python3 app.py
```

### Terminal 2 - API Service
```bash
cd api-service
python3 main.py
```

## 📝 Example Usage

### 1. Store a Memory
```bash
curl -X POST http://localhost:8000/store_text \
  -H "Content-Type: application/json" \
  -d '{"text_summary":"theres a yellow key on the table","session_id":"test"}'
```

### 2. Search Memories
```bash
curl "http://localhost:8000/search?query=what%20color%20is%20the%20key"
```

### 3. Clear Storage
```bash
curl -X POST http://localhost:8000/clear_storage
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill processes on ports
lsof -ti:8000 | xargs kill -9  # API
lsof -ti:8001 | xargs kill -9  # Vector Store
```

### Services Not Starting
```bash
# Check logs
cat api-service/api.log
cat vector-store/vectorstore.log

# Ensure dependencies are installed
pip3 install reka-api pillow fastapi httpx uvicorn
```

### Storage Not Persisting
```bash
# Make sure vector store is running
curl http://localhost:8001/healthz

# If not running, start it
cd vector-store && python3 app.py
```

## 📚 API Endpoints

### Main Endpoints
- `POST /store_text` - Store text description
- `GET /search?query=...` - Search memories
- `POST /clear_storage` - Clear all storage
- `GET /debug/memory` - View in-memory items

### Vector Store Endpoints
- `POST /add_frame` - Add frame data
- `POST /search_semantic` - Semantic search
- `POST /clear_collection` - Clear a collection
- `GET /healthz` - Health check

## 💾 Data Location

```
remembar/
├── vector-store/.chroma/          # Persistent database (survives restarts)
├── api-service/api.log           # API logs
├── vector-store/vectorstore.log  # Vector store logs
└── web-test/index.html           # Web interface
```

## 🎯 Best Practices

1. **Always use `start_services.sh`** - Ensures both services run
2. **Check logs if issues occur** - Logs in `api.log` and `vectorstore.log`
3. **Use web interface** - Easier than curl commands
4. **Clear storage when testing** - Prevents duplicate/stale data
5. **Keep services running** - Data only persists with vector store

---

**Happy memory storing! 🧠✨**


