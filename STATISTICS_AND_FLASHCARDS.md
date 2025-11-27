# Statistics and Flashcards Features

## Overview

The Remembar web interface now includes two powerful new features to help visualize memory data and reinforce recall:

1. **📊 Statistics Dashboard** - Comprehensive analytics and insights about your stored memories
2. **🎴 Flashcards** - Interactive memory training to reinforce recall

---

## 📊 Statistics Dashboard

The Statistics tab provides comprehensive analytics about your memory data with beautiful visualizations.

### Features

#### Summary Cards
- **Total Memories**: Number of memories stored
- **Objects Detected**: Total count of all objects across memories
- **Unique Objects**: Number of distinct object types
- **Sessions**: Number of different recording sessions

#### Timeline Graph
- Visual bar chart showing memory activity over time
- Automatically grouped by:
  - **Today**: Hourly buckets
  - **Yesterday**: Daily summary
  - **Last Week**: Daily breakdown
  - **Older**: Weekly grouping
- Hover to see exact counts for each time period

#### Most Common Objects
- Top 10 most frequently detected objects
- Percentage breakdown
- Color information (what colors each object appeared in)
- Visual bar chart with gradients

#### Session Analytics
- Top 5 most active sessions
- Memory count per session
- Unique objects in each session
- Last activity timestamp

### API Endpoint

```
GET /statistics
```

**Response Format:**
```json
{
  "ok": true,
  "total_memories": 10,
  "total_objects": 25,
  "unique_objects": 8,
  "sessions": 2,
  "most_common_objects": [
    {
      "object": "key",
      "count": 5,
      "percentage": 20.0,
      "common_colors": [
        {"color": "yellow", "count": 3},
        {"color": "silver", "count": 2}
      ]
    }
  ],
  "session_stats": [
    {
      "session_id": "test-session",
      "memory_count": 8,
      "duration_seconds": 3600,
      "unique_objects": 6,
      "last_active": 1730000000
    }
  ],
  "timeline_data": [
    {
      "timestamp": 1730000000,
      "label": "14:00",
      "count": 3,
      "type": "hour"
    }
  ],
  "storage_info": {
    "mode": "in_memory",
    "total_memories": 10,
    "estimated_size_kb": 5.2
  }
}
```

---

## 🎴 Flashcards Feature

Interactive flashcards help reinforce memory recall through active testing.

### How It Works

1. **Load Flashcards**: Automatically loads all stored memories
2. **Question Mode**: Each card asks "What was in this memory?"
3. **Flip to Reveal**: Click the card to see the answer
4. **Navigate**: Use Previous/Next buttons or shuffle for random order

### Flashcard Display

Each flashcard shows:
- **Session ID** (top-left badge)
- **Timestamp** (top-right)
- **Scene Summary** (when flipped)
- **Objects List** with colors (when flipped)
- **Full Text Summary** (when flipped)

### Controls

- **← Previous**: Go to previous card
- **Next →**: Advance to next card
- **🔀 Shuffle**: Randomize card order
- **Card Counter**: Shows current position (e.g., "3 / 10")

### Interactive Features

- **Click to Flip**: Click anywhere on the card to reveal the answer
- **Visual Feedback**: Card changes gradient when flipped
- **Hover Effect**: Card lifts slightly on hover
- **Smooth Transitions**: All interactions have smooth animations

### Use Cases

1. **Memory Training**: Test recall of past observations
2. **Pattern Recognition**: See what objects frequently appear together
3. **Session Review**: Review all memories from a specific time period
4. **Active Recall**: Strengthen memory through active testing

---

## Usage Guide

### Accessing the Features

1. **Start the API Server**:
   ```bash
   cd api-service
   python3 main.py
   ```

2. **Open Web Interface**:
   ```bash
   open web-test/index.html
   ```

3. **Navigate to Tabs**:
   - Click **📊 Statistics** for analytics
   - Click **🎴 Flashcards** for memory training

### Workflow Example

```
1. Add Memories (Text to JSON tab)
   ↓
2. View Statistics (see patterns and trends)
   ↓
3. Use Flashcards (test your recall)
   ↓
4. Review Timeline (see chronological view)
```

---

## Technical Details

### Statistics Algorithm

- **Object Tracking**: Counts all objects across memories with color analysis
- **Session Duration**: Calculated from first to last memory timestamp
- **Time Grouping**: Intelligent bucketing based on recency
- **Percentage Calculation**: Based on total object count

### Flashcard Algorithm

- **Shuffle**: Uses Fisher-Yates algorithm for true randomization
- **State Management**: Maintains current card index and flipped state
- **Navigation**: Circular array traversal (loops back to start/end)

### Performance

- **Statistics**: Computed on-demand, O(n) complexity
- **Flashcards**: Loads all memories once, instant navigation
- **Timeline Graph**: Dynamically scaled based on max count

---

## Visual Design

### Color Scheme

- **Primary Gradient**: #667eea → #764ba2
- **Cards**: White backgrounds with colored borders
- **Charts**: Gradient-filled bars and interactive elements
- **Flashcards**: Full gradient backgrounds with white text

### Responsive Design

- **Grid Layout**: Automatically adjusts to screen size
- **Mobile Friendly**: Cards stack vertically on smaller screens
- **Touch Support**: All interactions work with touch gestures

---

## Future Enhancements

Potential improvements:

1. **Statistics**:
   - Export data to CSV/JSON
   - Filtering by date range
   - Custom time period selection
   - More chart types (pie charts, scatter plots)

2. **Flashcards**:
   - Spaced repetition algorithm
   - Marking cards as "mastered"
   - Quiz mode with multiple choice
   - Progress tracking over time
   - Custom card creation

3. **Integration**:
   - Voice input for flashcard answers
   - Share statistics via image export
   - Collaborative sessions
   - Real-time sync across devices

---

## Troubleshooting

### Statistics Not Loading

- **Check API Connection**: Ensure `http://localhost:8000` is running
- **Check Console**: Look for JavaScript errors in browser console
- **Verify Data**: Use "Text to JSON" tab to add some memories first

### Flashcards Empty

- **Add Memories First**: Need at least one memory to create flashcards
- **Check Memory Store**: Use Timeline tab to verify memories exist
- **Refresh**: Click the refresh button or reload the page

### Timeline Graph Not Showing

- **Need Multiple Memories**: Graph requires 2+ memories for visualization
- **Check Timestamps**: Ensure memories have valid timestamps
- **Browser Compatibility**: Requires modern browser with ES6 support

---

## API Integration

### Using Statistics in Your App

```javascript
// Fetch statistics
const response = await fetch('http://localhost:8000/statistics');
const stats = await response.json();

// Access data
console.log(`Total memories: ${stats.total_memories}`);
console.log(`Most common: ${stats.most_common_objects[0].object}`);

// Render timeline
stats.timeline_data.forEach(point => {
  console.log(`${point.label}: ${point.count} memories`);
});
```

### Using Memories for Flashcards

```javascript
// Fetch memories
const response = await fetch('http://localhost:8000/memories?limit=100');
const data = await response.json();

// Create flashcards
data.memories.forEach(memory => {
  console.log(`Question: What was in ${memory.session_id}?`);
  console.log(`Answer: ${memory.scene}`);
  console.log(`Objects: ${memory.objects.map(o => o.label).join(', ')}`);
});
```

---

## Conclusion

The Statistics and Flashcards features transform Remembar from a simple memory storage system into a comprehensive memory training and analysis platform. Use statistics to understand patterns in your observations, and use flashcards to strengthen recall through active testing.

**Happy Memory Training! 🧠✨**


