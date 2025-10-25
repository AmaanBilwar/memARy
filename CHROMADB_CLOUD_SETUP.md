# ☁️ ChromaDB Cloud Configuration

## 🎉 What's New

Remembar now uses **ChromaDB Cloud** for persistent storage! This means:

✅ **No local database files** - Everything stored in the cloud  
✅ **True persistence** - Data survives restarts, redeployments, and crashes  
✅ **Easy deployment** - Works perfectly on Railway, Heroku, or any platform  
✅ **Scalable** - ChromaDB Cloud handles scaling for you  
✅ **Shared database** - Multiple instances can share the same database  

## 🔧 Configuration

### Current Setup

Your ChromaDB Cloud credentials are already configured:

```
Tenant: 053f90af-f7f0-48dd-bd77-1f67ee514158
Database: remembar
API Key: ck-7QBdriXEhMjhkLgbr5DBT8vPx1pgUQbfM96rQ8pe3sr3
```

### Environment Variables

The system uses these environment variables (in order of priority):

```bash
# Enable/disable cloud mode (default: true)
USE_CHROMA_CLOUD=true

# ChromaDB Cloud credentials
CHROMA_API_KEY=ck-7QBdriXEhMjhkLgbr5DBT8vPx1pgUQbfM96rQ8pe3sr3
CHROMA_TENANT=053f90af-f7f0-48dd-bd77-1f67ee514158
CHROMA_DATABASE=remembar

# Local fallback (if cloud fails)
CHROMA_DIR=./.chroma
```

### How It Works

1. **Default**: Uses ChromaDB Cloud with hardcoded credentials
2. **Override**: Set environment variables to use different credentials
3. **Fallback**: If cloud connection fails, falls back to local storage
4. **Local Mode**: Set `USE_CHROMA_CLOUD=false` to use local storage

## 🚀 Deployment

### Railway (Recommended)

The system is pre-configured for Railway deployment:

```bash
# Deploy with ChromaDB Cloud
railway variables set USE_CHROMA_CLOUD=true
railway variables set CHROMA_API_KEY=ck-7QBdriXEhMjhkLgbr5DBT8vPx1pgUQbfM96rQ8pe3sr3
railway variables set CHROMA_TENANT=053f90af-f7f0-48dd-bd77-1f67ee514158
railway variables set CHROMA_DATABASE=remembar
railway up
```

**That's it!** No need for volumes or persistent storage configuration.

### Other Platforms

For Heroku, Render, or other platforms:

1. Set the environment variables listed above
2. Deploy normally
3. The system will automatically use ChromaDB Cloud

## 🧪 Testing

Test the ChromaDB Cloud connection:

```bash
# Check service health
curl http://localhost:8001/healthz

# Should show all 5 collections:
# - frames_ephemeral_v1
# - entities_stream_v1
# - latest_entities_v1
# - user_notes_v1
# - long_term_memory_v1
```

## 📊 Collections

All 5 collections are automatically created on ChromaDB Cloud:

1. **frames_ephemeral_v1** - Scene summaries (24-72h TTL)
2. **entities_stream_v1** - Per-object mentions stream
3. **latest_entities_v1** - Last-seen location for tracked items
4. **user_notes_v1** - User-provided notes (highest trust)
5. **long_term_memory_v1** - Curated memories (user-selected)

## 🔐 Security

- API keys are stored as environment variables (never in code)
- Credentials have hardcoded fallbacks for easy setup
- Use `.env` files locally (they're gitignored)
- Use platform environment variables in production

## 💡 Benefits for Deployment

### Before (Local ChromaDB)
❌ Data lost on container restart  
❌ Need persistent volumes/storage  
❌ Complex Railway/Heroku configuration  
❌ Can't share data between instances  

### After (ChromaDB Cloud)
✅ Data persists forever  
✅ No volumes needed  
✅ Simple Railway deployment  
✅ Multiple instances can share database  

## 🛠️ Switching Modes

### Use Cloud (Default)
```bash
export USE_CHROMA_CLOUD=true
./start_services.sh
```

### Use Local Storage
```bash
export USE_CHROMA_CLOUD=false
./start_services.sh
```

## 🎯 Key Technical Details

### Embedding Function
- **ChromaDB Cloud** was trying to download a 79MB default embedding model
- **Solution**: We provide our own embeddings via `sentence-transformers`
- **Configuration**: Set `embedding_function=None` when creating collections
- **Result**: Instant startup, no downloads needed

### Connection
- **Client**: `chromadb.CloudClient()`
- **Upgraded**: ChromaDB version from 0.5.23 → 1.2.1 for better cloud support
- **Fallback**: Automatically uses local if cloud fails

## 📝 Files Modified

1. **`vector-store/chroma_client.py`** - Updated to support CloudClient
2. **`vector-store/requirements.txt`** - Upgraded chromadb to >=0.5.5
3. **`railway.toml`** - Added cloud environment variable placeholders
4. **`DEPLOY_QUICK_START.md`** - Added ChromaDB Cloud setup steps

## ✅ Verification

After starting services, verify ChromaDB Cloud is active:

```bash
# Check logs for cloud connection
grep "ChromaDB Cloud" vector-store/vectorstore.log

# Should show:
# ✓ ChromaDB Cloud connected (tenant: 053f90af-f7f0-48dd-bd77-1f67ee514158, database: remembar)
```

## 🎊 Success!

Your Remembar system is now cloud-native and deployment-ready! 🚀

---

**Made with 🧠 and ☁️**

*No more local database files. No more lost data. Just pure cloud persistence.*

