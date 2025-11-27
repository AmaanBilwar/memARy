# ⚡ Quick Deploy Guide

## For You (The Host)

Deploy Remembar to make it accessible to others:

```bash
# 1. Login
railway login --browserless
# → Open the URL shown, authorize, return to terminal

# 2. Initialize
cd /Users/arkanfadhilkautsar/Downloads/remembar
railway init

# 3. Set your API keys
railway variables set REKA_API_KEY=your_reka_key_here

# 4. Configure ChromaDB Cloud (recommended for persistence)
railway variables set USE_CHROMA_CLOUD=true
railway variables set CHROMA_API_KEY=ck-7QBdriXEhMjhkLgbr5DBT8vPx1pgUQbfM96rQ8pe3sr3
railway variables set CHROMA_TENANT=053f90af-f7f0-48dd-bd77-1f67ee514158
railway variables set CHROMA_DATABASE=remembar

# 5. Deploy
railway up

# 6. Get your URL
railway domain
# → You'll get: https://remembar-production-xyz.railway.app
```

**Done!** Share the URL with your friend.

---

## For Your Friend (The User)

Use the deployed Remembar via MCP:

### Setup (One-Time)

```bash
# 1. Install MCP
pip3 install mcp

# 2. Download the MCP server file
# Get mcp_server.py from your friend's GitHub repo
```

### Configure Claude Desktop

Edit: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "remembar": {
      "command": "python3",
      "args": [
        "/full/path/to/mcp_server.py"
      ],
      "env": {
        "REMEMBAR_API_URL": "https://remembar-production-xyz.railway.app"
      }
    }
  }
}
```

**Replace:**
- `/full/path/to/mcp_server.py` → actual path where you saved the file
- `https://remembar-production-xyz.railway.app` → the URL your friend gave you

### Restart Claude Desktop

That's it! Now talk to Claude:
- "I saw a yellow key on the table"
- "Where did I leave my keys?"
- "Show me my memories"

---

## What Gets Shared?

✅ **Your Friend Can:**
- Use the same memory database as you
- Add memories through Claude
- Search all memories (theirs + yours)
- Use all Remembar features

❌ **Your Friend Doesn't Need:**
- To run their own API server
- The full Remembar codebase
- Their own Reka API key
- To deploy anything

---

## Cost

- **Railway Free Tier**: $5 credit/month (~500 hours)
- **After free credit**: ~$0.01/hour
- **For hobby use**: Usually stays within free tier

---

## Troubleshooting

### "Could not connect to Remembar API"
- Check the URL in Claude config matches your deployed URL
- Make sure your Railway app is running: `railway status`

### Friend can't use it
1. Verify they installed MCP: `pip3 install mcp`
2. Check their Claude config has the correct URL
3. Make sure they restarted Claude Desktop

---

**That's it! You're live! 🚀**

