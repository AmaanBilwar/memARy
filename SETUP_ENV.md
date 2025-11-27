# 🔑 Setting Up Your API Key

## Quick Setup (30 seconds)

### Option 1: Create .env file (Recommended)

```bash
cd /Users/arkanfadhilkautsar/Downloads/memary

# Create .env file with your Reka API key
echo "REKA_API_KEY=your_actual_reka_key_here" > vision-processor/.env
```

### Option 2: Export environment variable (Temporary)

```bash
export REKA_API_KEY=your_actual_reka_key_here
```

## Where to Get Your Reka API Key

1. Go to: https://www.reka.ai/
2. Sign up/Login
3. Navigate to API Keys section
4. Copy your API key

## After Setting Up

Restart the API service:

```bash
# Kill the current service
lsof -ti:8000 | xargs kill -9

# Start with environment loaded
cd /Users/arkanfadhilkautsar/Downloads/memary/api-service
export REKA_API_KEY=your_key_here  # or source ../.env
python3 main.py > /tmp/api-service.log 2>&1 &
```

Or use the startup script which will auto-load the .env:

```bash
cd /Users/arkanfadhilkautsar/Downloads/memary
./start_image_pipeline.sh
```

## Test It Works

```bash
# Should show your key (first few characters)
echo $REKA_API_KEY | cut -c1-10

# Test the endpoint
curl -X POST http://localhost:8000/store_text \
  -H "Content-Type: application/json" \
  -d '{"text_summary": "test", "session_id": "test"}'
```

---

**Once you have the API key set up, the image upload will work perfectly!**

