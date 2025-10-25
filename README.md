# 🧠 Remembar - AI Memory System

**Remember anything. Search everything. Ask naturally.**

Remembar is an AI-powered memory system that lets you store observations as natural language and search them conversationally. With Model Context Protocol (MCP) support, you can integrate Remembar directly with Claude Desktop and other AI assistants!

## ✨ Features

### 🎯 Core Capabilities
- **Natural Language Storage**: Just describe what you see - "there's a yellow key on the table"
- **Conversational Search**: Ask naturally - "where are my keys?" or "what color is the car?"
- **AI-Powered Understanding**: Uses Reka AI to extract structured data from descriptions
- **Vector Search**: Semantic search powered by ChromaDB for intelligent matching

### 🔌 MCP Integration (NEW!)
- **Direct AI Assistant Access**: Use with Claude Desktop, ChatGPT, or any MCP client
- **Voice-to-Memory**: Speak to Claude, have it remember for you
- **Seamless Queries**: Ask Claude about your memories conversationally
- **No Extra Interface Needed**: Your AI assistant becomes your memory interface

### 📊 Advanced Features
- **📅 Timeline View**: See memories grouped by date (Today, Yesterday, Last Week)
- **📌 Item Tracking**: Track important items with customizable alerts
- **🔗 Object Relationships**: Automatically learns which items are seen together
- **📈 Statistics Dashboard**: Analytics on your memories and patterns
- **🎴 Flashcards**: Memory reinforcement with intelligent Q&A generation
- **💾 Persistent Storage**: All data saved locally with ChromaDB

## 🚀 Quick Start

### Option 1: MCP Integration (Recommended)

Use Remembar directly through Claude Desktop or other AI assistants:

```bash
# Start Remembar with MCP support
./start_with_mcp.sh
```

Then follow the setup guide: **[MCP_SETUP.md](./MCP_SETUP.md)**

### Option 2: Web Interface

Use the browser-based interface:

```bash
# Start services
./start_services.sh

# Open web interface
open web-test/index.html
```

### Option 3: REST API

Direct API access:

```bash
# Start API server
cd api-service
python3 main.py

# Store a memory
curl -X POST http://localhost:8000/store_text \
  -H "Content-Type: application/json" \
  -d '{"text": "yellow key on the table"}'

# Search memories
curl "http://localhost:8000/search?query=where+is+the+key"
```

## 📋 Prerequisites

- **Python 3.9+**
- **Reka AI API Key** (get one at [reka.ai](https://reka.ai))
- **pip** or **pip3**

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd remembar
   ```

2. **Set up environment**
   ```bash
   # Create .env file in api-service/
   echo "REKA_API_KEY=your_key_here" > api-service/.env
   ```

3. **Install dependencies**
   ```bash
   cd api-service
   pip3 install -r requirements.txt
   ```

4. **Start services**
   ```bash
   ./start_with_mcp.sh
   ```

## 📖 Documentation

- **[MCP Setup Guide](./MCP_SETUP.md)** - Connect to Claude Desktop
- **[Startup Guide](./STARTUP_GUIDE.md)** - Detailed startup instructions
- **[Architecture](./ARCHITECTURE.md)** - System design and components
- **[API Reference](./API_QUICK_REFERENCE.md)** - REST API endpoints
- **[Pipeline Update](./PIPELINE_UPDATE.md)** - Text-to-JSON pipeline details

### Feature Guides
- **[Timeline Feature](./TIMELINE_FEATURE.md)** - Timeline view documentation
- **[Statistics & Flashcards](./STATISTICS_AND_FLASHCARDS.md)** - Analytics features

## 🎮 Usage Examples

### With Claude Desktop (MCP)

Once configured, just talk to Claude naturally:

```
You: I saw a yellow key on the table in the kitchen
Claude: ✓ I've stored that memory!

You: What color is the key?
Claude: The key was yellow. I saw it on the table in the kitchen, just now.

You: Track my medication and alert me if I haven't seen it in 12 hours
Claude: ✓ Now tracking 'medication'. I'll alert if not seen for 12 hours.
```

### With Web Interface

1. Open `web-test/index.html`
2. Go to "📝 Text to JSON" tab
3. Enter: "there's a yellow key on the table"
4. Click "Convert to JSON"
5. Switch to "🔍 Search Memories" tab
6. Ask: "what color is the key?"

### With REST API

```python
import requests

# Store memory
response = requests.post('http://localhost:8000/store_text', json={
    'text': 'yellow key on the table',
    'session_id': 'my-session'
})

# Search
response = requests.get('http://localhost:8000/search', params={
    'query': 'where is the key'
})
print(response.json()['answer'])
```

## 🏗️ Architecture

```
┌─────────────────┐
│  Claude Desktop │  ← MCP Client (NEW!)
└────────┬────────┘
         │ MCP Protocol
         ↓
┌─────────────────┐
│  mcp_server.py  │  ← MCP Server
└────────┬────────┘
         │ HTTP REST
         ↓
┌─────────────────┐
│  main.py API    │  ← FastAPI Service
└────────┬────────┘
         │
         ├─→ Reka AI (Image/Text → JSON)
         │
         └─→ ChromaDB (Vector Store)
```

## 🔧 Technology Stack

- **Backend**: FastAPI (Python)
- **AI Processing**: Reka AI (Vision + Text Models)
- **Vector Store**: ChromaDB
- **MCP Server**: Model Context Protocol SDK
- **Frontend**: HTML/CSS/JavaScript (Vanilla)

## 📁 Project Structure

```
remembar/
├── api-service/          # Main API server
│   ├── main.py          # FastAPI endpoints
│   ├── mcp_server.py    # MCP server (NEW!)
│   └── requirements.txt
├── vector-store/         # ChromaDB vector storage
│   └── app.py
├── vision-processor/     # Image processing (optional)
│   └── vision_reka.py
├── web-test/            # Web interface
│   └── index.html
├── start_with_mcp.sh    # Startup with MCP
├── start_services.sh    # Startup without MCP
└── MCP_SETUP.md         # MCP configuration guide
```

## 🧪 Testing

### Test MCP Server
```bash
python3 test_mcp.py
```

### Test API
```bash
cd api-service
python3 test.sh
```

### Test Integration
```bash
cd example-client-service
python3 test_integration.py
```

## 🤝 Contributing

Contributions welcome! Areas of interest:

- Additional MCP client integrations
- Mobile app development
- Additional AI model support
- Performance optimizations
- Documentation improvements

## 📝 License

[Your License Here]

## 🆘 Support

- **Issues**: [GitHub Issues](your-repo-url/issues)
- **Discussions**: [GitHub Discussions](your-repo-url/discussions)
- **Email**: [Your Email]

## 🎯 Roadmap

- [x] Basic memory storage and search
- [x] Timeline view
- [x] Item tracking with alerts
- [x] Object relationships
- [x] Statistics dashboard
- [x] MCP integration
- [ ] Mobile app
- [ ] Multi-user support
- [ ] Cloud deployment
- [ ] Additional AI model support
- [ ] Offline mode

## ⭐ Star History

If you find Remembar useful, please consider giving it a star on GitHub!

---

**Made with 🧠 by [Your Name]**

*Remember everything. Search naturally. Live smarter.*

