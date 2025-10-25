# Timeline Feature Implementation

## 📅 Overview

The Timeline View allows users to browse all their memories organized chronologically with automatic date grouping.

## ✨ Features Implemented

### 1. **New API Endpoint**
- **Endpoint**: `GET /memories`
- **Parameters**: 
  - `session_id` (optional) - Filter by session
  - `limit` (default: 100) - Max number of results
- **Returns**: Memories sorted by timestamp (newest first)

### 2. **Timeline Tab in Web Interface**
- New tab alongside "Text to JSON" and "Search"
- Auto-loads when clicked
- Manual refresh button

### 3. **Smart Date Grouping**
Memories automatically organized into:
- **Today** - Current day
- **Yesterday** - Previous day  
- **Last Week** - Past 7 days
- **Older** - Everything else

Empty groups are automatically hidden.

### 4. **Memory Cards**
Each memory displays as an interactive card with:
- **Header**: Time (HH:MM) + Session badge
- **Scene**: Description of what was seen
- **Objects**: Color-coded tags for each detected object
- **Click to expand**: Shows full details

### 5. **Expandable Details**
Clicking any card reveals:
- Original text input
- Complete object list with:
  - Object name
  - Color (if detected)
  - Position/location
  - Confidence percentage

## 🎨 UI Design

### Visual Elements
- **Timeline Groups**: Purple headers with underline
- **Memory Cards**: Light gray background, purple left border
- **Hover Effect**: Slides right with shadow
- **Object Tags**: Gradient purple badges
- **Session Badges**: Light purple background

### Responsive Design
- Cards adapt to content
- Smooth animations
- Mobile-friendly layout

## 📝 Code Structure

### Backend (api-service/main.py)
```python
@app.get("/memories")
def get_all_memories(session_id: Optional[str] = None, limit: int = 100):
    # Filter by session if specified
    # Sort by timestamp (newest first)
    # Return limited results
```

### Frontend (web-test/index.html)

#### Key Functions
1. **`loadTimeline()`** - Fetches memories from API
2. **`displayTimeline(memories)`** - Renders grouped cards
3. **`groupMemoriesByDate(memories)`** - Organizes by date
4. **`formatTime(timestamp)`** - Converts to HH:MM format
5. **`toggleMemoryDetails(id)`** - Expands/collapses cards

#### Date Grouping Logic
```javascript
const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() / 1000;
const yesterdayStart = todayStart - 86400;
const lastWeekStart = todayStart - (7 * 86400);

// Group memories based on timestamp ranges
```

## 🚀 Usage Example

### Adding Memories
```bash
curl -X POST http://localhost:8000/store_text \
  -H "Content-Type: application/json" \
  -d '{"text_summary":"yellow key on the table","session_id":"morning"}'
```

### Viewing Timeline
1. Open web interface
2. Click "📅 Timeline" tab
3. See grouped memories
4. Click any card to see details

### Filtering by Session
```bash
curl http://localhost:8000/memories?session_id=morning
```

## 💡 Future Enhancements

Possible improvements:
1. **Date Range Filter** - Select specific date range
2. **Search within Timeline** - Filter by keyword
3. **Export Timeline** - Download as PDF/JSON
4. **Session Filtering** - Dropdown to filter by session
5. **Infinite Scroll** - Load more as you scroll
6. **Calendar View** - Visual calendar with memory counts
7. **Statistics** - Chart showing memories over time
8. **Bulk Actions** - Select multiple to delete/export

## 📊 Technical Details

### Data Flow
```
User clicks Timeline tab
    ↓
loadTimeline() fetches from /memories
    ↓
groupMemoriesByDate() organizes data
    ↓
displayTimeline() renders HTML
    ↓
User clicks card → toggleMemoryDetails()
```

### Performance
- **Efficient Sorting**: Done server-side
- **Lazy Rendering**: Only rendered when tab is clicked
- **Minimal Re-renders**: Smart DOM updates
- **Memory Limit**: Configurable (default 100)

## 🎯 Benefits

1. **Easy Browsing**: See all memories at a glance
2. **Time Context**: Know when things happened
3. **Session Organization**: Separate by sessions
4. **Quick Details**: Expand any memory instantly
5. **Visual Appeal**: Beautiful, modern design

---

**Status**: ✅ Fully Implemented and Tested  
**Files Modified**: 
- `api-service/main.py` (new endpoint)
- `web-test/index.html` (new tab + functions)
- `web-test/README.md` (documentation)

**Date**: October 25, 2025


