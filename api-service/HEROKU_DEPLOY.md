# Deploy to Heroku

## Prerequisites

1. Install Heroku CLI:
```bash
brew tap heroku/brew && brew install heroku
# or
curl https://cli-assets.heroku.com/install.sh | sh
```

2. Login to Heroku:
```bash
heroku login
```

## Deploy Steps

### 1. Create Heroku App

```bash
cd /Users/arkanfadhilkautsar/Downloads/remembar/api-service

# Create app
heroku create your-memory-api

# Or with specific name
heroku create memory-api-uniquename
```

### 2. Set Environment Variables

```bash
# Set vector store URL (if you deploy vector-store separately)
heroku config:set VECTOR_STORE_URL=https://your-vector-store.herokuapp.com

# Or keep it local for now
heroku config:set VECTOR_STORE_URL=http://localhost:8001
```

### 3. Deploy

```bash
# Initialize git if not already
git init
git add .
git commit -m "Initial commit"

# Deploy to Heroku
git push heroku main

# Or if on a branch
git push heroku your-branch:main
```

### 4. Open Your App

```bash
heroku open
```

Your API will be at: `https://your-app-name.herokuapp.com`

### 5. View Logs

```bash
heroku logs --tail
```

## Test Deployed API

```bash
# Get app URL
heroku info

# Test endpoints
curl https://your-app-name.herokuapp.com/

curl -X POST https://your-app-name.herokuapp.com/store \
  -H "Content-Type: application/json" \
  -d '{"scene": "test", "objects": []}'
```

## Important Notes

⚠️ **Vector Store Must Be Accessible:**
- If your vector store is on `localhost:8001`, Heroku can't reach it
- Options:
  1. Deploy vector-store to Heroku too
  2. Use a cloud-hosted ChromaDB
  3. Use ngrok to expose localhost (for testing)

## Deploy Vector Store to Heroku

```bash
cd /Users/arkanfadhilkautsar/Downloads/remembar/vector-store

# Create Procfile
echo "web: uvicorn app:app --host 0.0.0.0 --port \$PORT" > Procfile

# Create runtime.txt
echo "python-3.11.9" > runtime.txt

# Create Heroku app
heroku create your-vector-store

# Deploy
git init
git add .
git commit -m "Vector store"
git push heroku main
```

Then update your API's env var:
```bash
cd /Users/arkanfadhilkautsar/Downloads/remembar/api-service
heroku config:set VECTOR_STORE_URL=https://your-vector-store.herokuapp.com
```

## CORS is Enabled

The API now accepts requests from any domain. Your frontend can call it from anywhere!

```javascript
// Frontend can call from any domain
fetch('https://your-app.herokuapp.com/store', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({scene: 'test', objects: []})
})
```

## Heroku Free Tier

- ⚠️ Heroku removed free tier in 2022
- You'll need a paid plan ($5-7/month minimum)
- Alternative free options:
  - Railway.app
  - Render.com
  - Fly.io

## Alternative: Railway (Free Alternative)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway init
railway up
```

## Alternative: Render (Free Alternative)

1. Push to GitHub
2. Go to render.com
3. Connect your repo
4. Select "Web Service"
5. Build command: `pip install -r requirements.txt`
6. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Done! 🚀

