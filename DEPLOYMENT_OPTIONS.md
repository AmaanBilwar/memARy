# 🚀 Ngrok Deployment Options

Your authtoken is configured: `34YKWpfQYvmFUsYvspG7g...8xEL5bRU`

## Choose Your Deployment Method:

### 1. 🎯 Simple Deployment (Custom Domain)
**Best for: Production use with consistent URL**

```bash
./deploy_ngrok_simple.sh
```

- ✅ Uses your custom domain: `https://memary-chromadb.ngrok-free.app`
- ✅ URL stays the same every time
- ✅ Simple command-line method
- ✅ No config file needed

### 2. ⚡ Random URL Deployment
**Best for: Quick testing, development**

```bash
./deploy_ngrok_random.sh
```

- ✅ Fastest startup
- ✅ Random URL (e.g., `https://abc123.ngrok.io`)
- ✅ No custom domain required
- ⚠️ URL changes each restart

### 3. 🔒 Secure Deployment (Basic Auth)
**Best for: Production with password protection**

```bash
./deploy_ngrok_secure.sh
```

- ✅ Custom domain: `https://memary-chromadb.ngrok-free.app`
- ✅ Password protected
- ✅ Credentials:
  - `admin:SecurePassword123`
  - `user:UserPassword456`

Test with:
```bash
curl -u admin:SecurePassword123 https://memary-chromadb.ngrok-free.app/
```

### 4. 📋 Config File Deployment (Advanced)
**Best for: Multiple tunnels, complex setups**

```bash
./deploy_ngrok.sh
```

- ✅ Uses `ngrok.yml` config file
- ✅ Can run multiple tunnels
- ✅ More configuration options
- ✅ Can expose API, Vector Store, and Web Interface simultaneously

---

## Quick Comparison

| Method | Speed | Security | URL Type | Best For |
|--------|-------|----------|----------|----------|
| Simple | Fast | None | Custom | Production |
| Random | Fastest | None | Random | Testing |
| Secure | Fast | Basic Auth | Custom | Secure Production |
| Config | Medium | Flexible | Custom | Complex Setup |

---

## Common Commands

### View Authtoken
```bash
ngrok config check
```

### Test Connection
```bash
ngrok diagnose
```

### Update ngrok
```bash
ngrok update
```

### View Active Tunnels
```bash
curl http://localhost:4040/api/tunnels | python3 -m json.tool
```

### Stop All Services
```bash
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9
pkill -f ngrok
```

---

## API Endpoints Available

Once deployed (any method), test your endpoints:

```bash
# Set your URL
export API_URL="https://memary-chromadb.ngrok-free.app"

# Health check
curl $API_URL/

# API documentation
open $API_URL/docs

# Upload text
curl -X POST $API_URL/store_text \
  -H "Content-Type: application/json" \
  -d '{
    "text_summary": "I see a red coffee mug on my desk",
    "session_id": "test"
  }'

# Search memories
curl "$API_URL/search?query=coffee"

# Get statistics
curl "$API_URL/statistics"

# Upload image (requires base64 encoding)
curl -X POST $API_URL/store \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'"$(base64 -i your_image.jpg)"'",
    "session_id": "test"
  }'
```

---

## Monitor Traffic

All methods provide a dashboard at:
**http://localhost:4040**

Here you can:
- 📊 View all requests/responses
- 🔄 Replay requests
- 📈 See traffic statistics
- 🔍 Inspect headers and bodies

---

## Troubleshooting

### Authtoken Issues
```bash
# Re-add authtoken
ngrok config add-authtoken 34YKWpfQYvmFUsYvspG7g6pu9Mh_4CKphHFXeHrZf8xEL5bRU
```

### Domain Already in Use
```bash
# Kill all ngrok processes
pkill -f ngrok
sleep 2
# Then restart
```

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000
# Kill it
lsof -ti:8000 | xargs kill -9
```

### Services Not Starting
```bash
# Check logs
tail -f logs/api-service.log
tail -f logs/vector-store.log
```

---

## Permanent Deployment (Run on Boot)

### Install as System Service
```bash
# Install (runs ngrok.yml config)
ngrok service install --config /Users/arkanfadhilkautsar/Downloads/memary/ngrok.yml

# Start
ngrok service start

# Check status
ngrok service status

# Stop
ngrok service stop

# Uninstall
ngrok service uninstall
```

---

## Performance

- **Local API:** 10-50ms
- **Through ngrok:** +50-100ms
- **Reka processing:** 5-15 seconds
- **Total for image:** ~5-15 seconds (Reka is the bottleneck)

**FastAPI + ngrok = Production Ready!** ⚡

---

## Security Best Practices

1. **Use Basic Auth** for public APIs (deploy_ngrok_secure.sh)
2. **Rotate authtokens** regularly
3. **Monitor traffic** via dashboard
4. **Set up IP restrictions** (paid plan)
5. **Use HTTPS** (automatic with ngrok)

---

## Next Steps

1. **Choose a deployment method** above
2. **Run the script**
3. **Test your API** with curl commands
4. **Share the URL** with your team
5. **Monitor** at http://localhost:4040

---

## 💡 Recommendation

For production: **Use deploy_ngrok_secure.sh** (Basic Auth)  
For testing: **Use deploy_ngrok_random.sh** (Fastest)  
For development: **Use deploy_ngrok_simple.sh** (Custom domain)

**All methods are ready to use!** Just pick one and run! 🚀

