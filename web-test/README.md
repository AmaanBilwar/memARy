# Web Test Interface

Beautiful web interface to test your Remembar API - Text to JSON conversion.

> **💡 TIP**: For voice-based memory access, check out the **[MCP Integration](../MCP_SETUP.md)** which lets you use Claude Desktop or other AI assistants to interact with Remembar naturally!

## Features

- 📝 **Text to JSON**: Convert text descriptions to structured JSON with objects
- 🔍 **Search Memories**: Search through stored memories using semantic search
- 📅 **Timeline View**: Browse all memories organized by date (Today, Yesterday, Last Week)
- 📊 **Statistics Dashboard**: Comprehensive analytics with charts and insights
- 🎴 **Flashcards**: Interactive memory training to reinforce recall
- 🎨 **Beautiful UI**: Modern, responsive design
- 🔄 **Real-time Results**: See API responses instantly

## How It Works

The system uses **Stage 2 of the pipeline** for testing:

1. **Input**: Natural language text description (what you saw)
2. **Processing**: Text → Structured JSON extraction (Reka AI)
3. **Output**: JSON with scene summary and detected objects
4. **Storage**: Saved to vector database with embeddings
5. **Detection & Fetching**: Uses existing search methods for querying memories

## How to Use

### 1. Start Your API Service

```bash
cd api-service
python main.py
```

Your API should be running at `http://localhost:8000`

### 2. Open the Web Interface

Simply open `index.html` in your browser:

```bash
open index.html
```

Or double-click the file to open it.

### 3. Test Your API

#### Text to JSON Tab:
1. Enter a Session ID (e.g., "test-session")
2. Type or paste a text description in the text area, for example:
   ```
   The image shows an office desk with a silver laptop in the center, 
   a red coffee mug on the left side, and a black phone on the right.
   ```
3. Click "Convert to JSON"
4. View the response showing:
   - Original text summary
   - Extracted JSON with scene and objects
   - Storage confirmation with mode (vector_store or in_memory)

#### Search Tab:
1. Enter a search query (e.g., "Where is my notebook?", "What did I see with the coffee mug?")
2. Optionally specify a Session ID to filter results
3. Click "Search"
4. View natural language answer with context from stored memories
5. Uses existing detection and fetching methods:
   - Semantic search across vector embeddings
   - Temporal and session-based filtering
   - Natural language response generation

#### Timeline Tab:
1. Click the "📅 Timeline" tab
2. Memories automatically load, grouped by:
   - **Today** - Memories from today
   - **Yesterday** - Memories from yesterday
   - **Last Week** - Memories from the past 7 days
   - **Older** - Memories older than a week
3. Each memory card shows:
   - Time (HH:MM format)
   - Session ID
   - Scene description
   - Object tags with colors
4. **Click any memory card** to expand and see:
   - Original text input
   - Detailed object list with positions
   - Confidence scores
5. Click "🔄 Refresh" to reload the timeline

#### Statistics Tab:
1. Click the "📊 Statistics" tab
2. View comprehensive analytics including:
   - **Summary Cards**: Total memories, objects detected, unique objects, sessions
   - **Timeline Graph**: Visual bar chart showing memory activity over time
   - **Most Common Objects**: Top 10 objects with percentage breakdown and color info
   - **Session Analytics**: Most active sessions with unique object counts
3. Click "🔄 Refresh" to reload statistics
4. Hover over bars in the timeline graph to see detailed counts

#### Flashcards Tab:
1. Click the "🎴 Flashcards" tab
2. Memories load as interactive flashcards
3. Each card shows:
   - Session ID and timestamp
   - Question: "What was in this memory?"
4. **Click the card** to flip and reveal:
   - Scene description
   - Objects with colors
   - Original text summary
5. Use controls to navigate:
   - **← Previous**: Go to previous card
   - **Next →**: Advance to next card
   - **🔀 Shuffle**: Randomize order for better memory training
6. Card counter shows your position (e.g., "3 / 10")

## Storage Management

The interface includes a **🗑️ Clear All Storage** button that:
- Clears all in-memory data
- Clears the vector database
- Requires confirmation before proceeding
- Shows count of cleared items

## Configuration

- **API Base URL**: Change if your API is running on a different host/port
- Default: `http://localhost:8000`

## CORS Note

Make sure your API has CORS enabled (already configured in `api-service/main.py`):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing with Heroku

If you've deployed to Heroku, just update the API Base URL to your Heroku app:

```
https://your-app-name.herokuapp.com
```

