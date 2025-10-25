"""
Reka Vision: Image → Keywords + Vectors
Clean implementation for AR glasses memory
"""
import os
import base64
import json
from reka.client import Reka
from reka import ChatMessage
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def analyze_image(image_path: str) -> dict:
    """
    Image → Reka Vision → Structured keywords + objects
    
    Returns:
    {
        "scene_summary": "Brief scene description",
        "objects": [
            {"label": "keys", "confidence": 0.9, "color": "silver", "rel_pos": "on table"}
        ]
    }
    """
    
    # Initialize Reka
    api_key = os.getenv("REKA_API_KEY")
    if not api_key:
        raise ValueError("Set REKA_API_KEY environment variable")
    
    client = Reka(api_key=api_key)
    
    # Encode image
    with open(image_path, "rb") as f:
        img_data = f.read()
    
    base64_img = base64.standard_b64encode(img_data).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{base64_img}"
    
    # Structured extraction prompt
    prompt = """Analyze this image and extract ALL visible objects for AR memory recall.

Return ONLY valid JSON in this format:
{
  "scene_summary": "Brief 1-2 sentence description of the scene",
  "objects": [
    {"label": "object_name", "confidence": 0.9, "color": "color_or_null", "rel_pos": "position_description"}
  ]
}

Detect ANY of these objects if visible: keys, wallet, phone, glasses, eyeglasses, pills, medication, cup, mug, bottle, water bottle, notebook, notepad, pen, pencil, laptop, computer, book, bag, backpack, watch, charger, headphones, mouse, keyboard.

Also detect: hand, person, furniture (table, chair, desk).

For each object provide:
- label: object name
- confidence: 0.5 to 1.0 (estimate based on clarity)
- color: actual color if visible, or null
- rel_pos: position (e.g., "in hand", "on table left side", "center of frame")

Include ALL clearly visible objects."""

    # Call Reka vision
    response = client.chat.create(
        messages=[
            ChatMessage(
                content=[
                    {"type": "image_url", "image_url": data_url},
                    {"type": "text", "text": prompt}
                ],
                role="user",
            )
        ],
        model="reka-core-20240501",
    )
    
    # Parse response
    content = response.responses[0].message.content.strip()
    
    # Extract JSON from response (may have explanatory text)
    json_str = content
    
    # Try to find JSON block in markdown
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        json_str = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        json_str = content[start:end].strip()
    else:
        # Look for JSON object in text
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = content[start:end]
    
    try:
        result = json.loads(json_str)
        
        # Ensure structure
        if "scene_summary" not in result:
            result["scene_summary"] = "Scene captured"
        if "objects" not in result:
            result["objects"] = []
        
        # Add required fields for vector store
        for obj in result["objects"]:
            obj.setdefault("label", "unknown")
            obj.setdefault("confidence", 0.75)
            obj.setdefault("color", None)
            obj.setdefault("rel_pos", None)
            obj["bbox"] = None
            obj["is_person"] = obj["label"].lower() in ["person", "people", "human"]
        
        return result
        
    except json.JSONDecodeError:
        # Fallback
        return {
            "scene_summary": content[:200] if len(content) < 200 else content[:200] + "...",
            "objects": []
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python vision_reka.py <image_path>")
        sys.exit(1)
    
    result = analyze_image(sys.argv[1])
    
    print("\n" + "="*60)
    print("REKA VISION OUTPUT")
    print("="*60)
    print(f"\n📝 Scene: {result['scene_summary']}\n")
    
    if result['objects']:
        print(f"🎯 Keywords/Objects ({len(result['objects'])}):")
        for obj in result['objects']:
            conf = int(obj['confidence'] * 100)
            extra = []
            if obj.get('color'):
                extra.append(f"color: {obj['color']}")
            if obj.get('rel_pos'):
                extra.append(f"at: {obj['rel_pos']}")
            extra_str = f" ({', '.join(extra)})" if extra else ""
            print(f"   • {obj['label']}{extra_str} [{conf}%]")
    else:
        print("⚠️  No objects extracted")
    
    print("\n" + "="*60)
    print("✅ Ready for Vector Store")
    print("="*60)