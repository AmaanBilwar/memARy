# 🌐 Ngrok Deployment Guide

## Quick Start

Your ngrok configuration is ready! Just run:

```bash
cd /Users/arkanfadhilkautsar/Downloads/memary
./deploy_ngrok.sh
```

This will:
1. ✅ Start Vector Store (port 8001)
2. ✅ Start API Service (port 8000)  
3. ✅ Start Web Interface (port 8080)
4. ✅ Expose API via ngrok public URL
5. ✅ Open ngrok dashboard at http://localhost:4040

## Your Public API

Once running, you'll see output like:

```
Forwarding    https://abc123.ngrok.io -> http://localhost:8000
```

**That's your public API URL!** Share it with anyone. 🌍

## Test Your Public API

```bash
# Replace with your actual ngrok URL
export NGROK_URL="https://abc123.ngrok.io"

# Health check
curl $NGROK_URL/

# Upload text
curl -X POST $NGROK_URL/store_text \
  -H "Content-Type: application/json" \
  -d '{
    "text_summary": "I see a red coffee mug on my desk",
    "session_id": "public-test"
  }'

# Search memories
curl "$NGROK_URL/search?query=coffee"

# Get all memories
curl "$NGROK_URL/memories?limit=5"
```

## Image Upload from Web

1. Open your web interface: http://localhost:8080
2. Change the API URL to your ngrok URL (e.g., `https://abc123.ngrok.io`)
3. Upload images - they now work from anywhere!

## View Traffic & URLs

Open the ngrok dashboard:
```bash
open http://localhost:4040
```

Here you can:
- See all active tunnel URLs
- Inspect HTTP requests/responses
- Replay requests
- View traffic statistics

## Configuration Files

### ngrok.yml
Location: `/Users/arkanfadhilkautsar/Downloads/memary/ngrok.yml`

Currently exposing:
- ✅ **memary-api** (port 8000) - Main API with image pipeline

To expose additional services, uncomment in `ngrok.yml`:
```yaml
# Uncomment these to make them public:
# vector-store:
#   proto: http
#   addr: 8001
# 
# web-interface:
#   proto: http
#   addr: 8080
```

## Add Security (Recommended)

### Option 1: Basic Authentication

Edit `ngrok.yml` and uncomment:
```yaml
tunnels:
  memary-api:
    proto: http
    addr: 8000
    basic_auth:
      - "admin:YourSecurePassword123"
```

Restart ngrok. Now users need username/password to access.

### Option 2: IP Restrictions (Paid Plan)

Add to your ngrok dashboard: https://dashboard.ngrok.com/security/ip-restrictions

## Stop Services

Press `Ctrl+C` in the terminal running ngrok, or:

```bash
# Kill all services
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9
lsof -ti:8080 | xargs kill -9
```

## Permanent Deployment

### Run as System Service

```bash
# Install ngrok as a service
ngrok service install --config /Users/arkanfadhilkautsar/Downloads/memary/ngrok.yml

# Start service
ngrok service start

# Check status
ngrok service status

# Stop service
ngrok service stop

# Uninstall
ngrok service uninstall
```

### Custom Domain (Paid Plan)

Edit `ngrok.yml`:
```yaml
tunnels:
  memary-api:
    proto: http
    addr: 8000
    domain: memary.ngrok.app  # Your custom subdomain
```

## Troubleshooting

### "ngrok: command not found"
```bash
# Install ngrok
brew install ngrok/ngrok/ngrok
```

### "Invalid authtoken"
Your authtoken is already configured in `ngrok.yml`. If you need to change it:
```bash
ngrok config add-authtoken NEW_TOKEN_HERE
```

### Services not starting
Check logs:
```bash
tail -f logs/api-service.log
tail -f logs/vector-store.log
tail -f /tmp/ngrok.log
```

### Port already in use
```bash
# Find what's using the port
lsof -i :8000

# Kill it
lsof -ti:8000 | xargs kill -9
```

### Check ngrok connection issues
```bash
ngrok diagnose
```

## Logs

- API Service: `logs/api-service.log`
- Vector Store: `logs/vector-store.log`
- Web Server: `logs/web-server.log`
- Ngrok: `/tmp/ngrok.log`

## API Endpoints Available

Once deployed, your public API has all these endpoints:

- `GET /` - Health check
- `POST /store` - Upload image (Reka analyzes → ChromaDB)
- `POST /store_text` - Text → JSON → ChromaDB
- `GET /search?query=...` - Search memories
- `GET /memories` - Get all memories
- `GET /item/{name}` - Query specific item
- `POST /track_item` - Track an item
- `GET /tracked_items` - Get tracked items
- `GET /statistics` - Memory statistics
- `GET /relationships` - Object relationships
- `POST /clear_storage` - Clear all data

Full API docs at: `https://YOUR-NGROK-URL.ngrok.io/docs`

## Performance

- **Local:** ~10-50ms
- **Through ngrok:** +50-100ms latency
- **Reka API:** 5-15 seconds (bottleneck)

Overall: Fast enough for production! ⚡

## Cost

**Ngrok Free Tier:**
- ✅ 1 online ngrok agent
- ✅ 4 tunnels per agent
- ✅ 40 connections/minute
- ✅ Random URLs
- ❌ No custom domains

**Paid Plans ($8-49/month):**
- Custom domains
- More bandwidth
- IP restrictions
- Multiple regions

## Next Steps

1. **Run it:** `./deploy_ngrok.sh`
2. **Copy the ngrok URL** from output
3. **Share with friends** - they can use your API!
4. **Monitor traffic** at http://localhost:4040
5. **Add security** (basic auth recommended)

---

**Your FastAPI image pipeline is now publicly accessible!** 🚀🌍

Questions? Check https://ngrok.com/docs or run `ngrok help`


