# 🚂 Deploy Remembar to Railway

Deploy your Remembar memory system to Railway and make it accessible to anyone with the MCP server!

## 📋 Prerequisites

- Railway account (sign up at [railway.app](https://railway.app))
- Railway CLI installed: `npm install -g @railway/cli`
- Reka AI API key ([reka.ai](https://reka.ai))
- Your code pushed to GitHub

## 🚀 Quick Deploy

### Step 1: Login to Railway

```bash
railway login --browserless
```

This will:
1. Show you a URL like `https://railway.app/cli-login?token=...`
2. Open that URL in your browser
3. Click "Authorize"
4. Return to terminal - you're now logged in!

### Step 2: Initialize Project

```bash
cd /Users/arkanfadhilkautsar/Downloads/remembar
railway init
```

Select:
- **Create a new project**: Yes
- **Project name**: remembar (or your choice)

### Step 3: Set Environment Variables

```bash
railway variables set REKA_API_KEY=your_reka_api_key_here
```

### Step 4: Deploy!

```bash
railway up
```

This will:
- Build your application
- Install dependencies
- Deploy to Railway
- Give you a URL

### Step 5: Get Your Public URL

```bash
railway domain
```

Or create a custom domain:
```bash
railway domain add
```

You'll get something like: `https://remembar-production.up.railway.app`

## 🔧 Configuration

Your deployment uses these files:

- **`railway.toml`** - Main Railway configuration
- **`nixpacks.toml`** - Build configuration
- **`Procfile`** - Process definition
- **`.railwayignore`** - Files to exclude from deployment

## 📊 Using Your Deployed Instance

### Option 1: Your Friend Uses Your Deployed API

Your friend can point their local MCP server to your deployed API:

**Their MCP config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "remembar": {
      "command": "python3",
      "args": [
        "/path/to/their/local/mcp_server.py"
      ],
      "env": {
        "REMEMBAR_API_URL": "https://your-app.railway.app"
      }
    }
  }
}
```

They need:
1. Only the `mcp_server.py` file (not the full API)
2. MCP package installed: `pip install mcp`
3. Claude Desktop configured to point to YOUR deployed URL

### Option 2: Test Directly

```bash
# Test the deployed API
curl https://your-app.railway.app/

# Store a memory
curl -X POST https://your-app.railway.app/store_text \
  -H "Content-Type: application/json" \
  -d '{"text": "yellow key on the table"}'

# Search
curl "https://your-app.railway.app/search?query=where+is+the+key"
```

## ⚠️ Important Notes

### Database Persistence

By default, Railway deployments use **in-memory storage** which means:
- ✅ Fast and works immediately
- ❌ Data is lost when the app restarts or redeploys

**Solutions:**

#### Option A: Add Railway Volume (Persistent Storage)
```bash
railway volume create
railway volume attach <volume-id> /app/.chroma
```

#### Option B: Use ChromaDB Cloud
```bash
railway variables set CHROMA_URL=https://your-chromadb-cloud.com
railway variables set CHROMA_API_KEY=your_chroma_key
```

#### Option C: Accept In-Memory (For Testing)
- Good for demos and testing
- Data persists during the session
- Lost on restart

### Monitoring

Check your deployment:
```bash
# View logs
railway logs

# Check status
railway status

# Open in browser
railway open
```

## 🌐 Sharing with Your Friend

Once deployed, share these with your friend:

1. **Your Railway URL**: `https://your-app.railway.app`
2. **The MCP server file**: `api-service/mcp_server.py`
3. **Setup instructions**: "Install MCP (`pip install mcp`) and configure Claude Desktop"

### Your Friend's Setup (Minimal)

```bash
# 1. Install MCP
pip install mcp

# 2. Download mcp_server.py
wget https://raw.githubusercontent.com/your-repo/main/api-service/mcp_server.py

# 3. Configure Claude Desktop
# Edit: ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "remembar": {
      "command": "python3",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "REMEMBAR_API_URL": "https://your-app.railway.app"
      }
    }
  }
}

# 4. Restart Claude Desktop
# 5. Start using it!
```

## 🔒 Security Considerations

Your deployed API is **publicly accessible**. Consider:

1. **Add Authentication** (if needed):
   ```bash
   railway variables set API_SECRET_KEY=your_secret_key
   ```
   Then update `main.py` to require this key.

2. **Rate Limiting**: Already included in the API

3. **CORS**: Already configured for web access

## 💰 Pricing

Railway free tier includes:
- $5 free credit per month
- ~500 hours of runtime
- Good for hobby projects

For production:
- Pay as you go after free credit
- ~$0.01/hour for small apps

## 🐛 Troubleshooting

### Build Fails

```bash
# Check logs
railway logs

# Redeploy
railway up --detach
```

### App Crashes

```bash
# Check logs
railway logs

# Restart
railway restart
```

### Can't Access API

1. Check deployment status: `railway status`
2. Verify environment variables: `railway variables`
3. Check logs: `railway logs`
4. Test locally first: `python3 api-service/main.py`

### "No module named 'mcp'" Error

Your friend needs to install MCP:
```bash
pip install mcp
```

### MCP Server Can't Connect

Verify the URL in the config:
```json
"REMEMBAR_API_URL": "https://your-app.railway.app"  // ← Must be YOUR deployed URL
```

## 📚 Additional Resources

- **Railway Docs**: https://docs.railway.app
- **MCP Setup**: See `MCP_SETUP.md`
- **Heroku Alternative**: See `api-service/HEROKU_DEPLOY.md`

## 🎯 Next Steps

1. ✅ Deploy to Railway
2. ✅ Get your public URL
3. ✅ Share URL + `mcp_server.py` with friends
4. ✅ They configure Claude Desktop
5. ✅ Everyone can access YOUR memory database!

---

**Happy Deploying! 🚂✨**

Need help? Check Railway logs or the troubleshooting section above.

