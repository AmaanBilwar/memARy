"""
Reka Vision: Image → Text Summary → JSON
Two-stage pipeline for AR glasses memory
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

def image_to_text_summary(image_path: str) -> str:
    """
    Stage 1: Image → Natural language text summary
    
    Returns: Rich text description of the scene and visible objects
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
    
    # Natural language description prompt
    prompt = """Describe this image in detail for AR memory recall purposes.

Provide a comprehensive description that includes:
1. The overall scene and setting
2. ALL visible objects, with their colors and positions
3. Any notable details about the objects

Focus on objects like: keys, wallet, phone, glasses, pills, medication, cup, mug, bottle, notebook, pen, laptop, computer, book, bag, watch, charger, headphones, mouse, keyboard, and any furniture.

Be specific about colors, positions (like "on the left side of the table", "in hand", "near the edge"), and spatial relationships between objects.

Write a natural, flowing description as if you're helping someone remember what they saw."""

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
    
    # Return text description
    text_summary = response.responses[0].message.content.strip()
    return text_summary


def text_summary_to_json(text_summary: str) -> dict:
    """
    Stage 2: Text summary → Structured JSON with objects
    
    Parses natural language text to extract:
    - scene_summary
    - objects with labels, colors, positions, confidence
    """
    
    # Initialize Reka for text processing
    api_key = os.getenv("REKA_API_KEY")
    if not api_key:
        raise ValueError("Set REKA_API_KEY environment variable")
    
    client = Reka(api_key=api_key)
    
    # Structured extraction prompt
    prompt = f"""Given this text description of a scene, extract ALL objects mentioned into a structured JSON format.

Text description:
{text_summary}

Return ONLY valid JSON in this format:
{{
  "scene_summary": "Brief 1-2 sentence description of the scene",
  "objects": [
    {{"label": "object_name", "confidence": 0.9, "color": "color_or_null", "rel_pos": "position_description"}}
  ]
}}

For each object mentioned in the text:
- label: object name (e.g., "keys", "notebook", "phone")
- confidence: 0.7 to 1.0 (use 1.0 for explicitly mentioned objects, 0.7-0.9 for implied)
- color: actual color if mentioned, or null
- rel_pos: position description from the text (e.g., "on table left side", "in hand", "near edge")

Extract ALL objects mentioned. Return ONLY the JSON, no explanations."""

    # Call Reka for structured extraction
    response = client.chat.create(
        messages=[
            ChatMessage(
                content=prompt,
                role="user",
            )
        ],
        model="reka-core-20240501",
    )
    
    # Parse response
    content = response.responses[0].message.content.strip()
    
    # Extract JSON from response
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
            "scene_summary": text_summary[:200] if len(text_summary) < 200 else text_summary[:200] + "...",
            "objects": []
        }


def analyze_image(image_path: str) -> dict:
    """
    Complete 2-stage pipeline:
    1. Image → Text summary (natural language description)
    2. Text summary → JSON (structured objects)
    
    Returns:
    {
        "scene_summary": "Brief scene description",
        "objects": [
            {"label": "keys", "confidence": 0.9, "color": "silver", "rel_pos": "on table"}
        ],
        "text_summary": "The original text description"
    }
    """
    
    # Stage 1: Image to text
    print("📸 Stage 1: Converting image to text summary...")
    text_summary = image_to_text_summary(image_path)
    print(f"✓ Text summary generated ({len(text_summary)} chars)")
    
    # Stage 2: Text to JSON
    print("📝 Stage 2: Extracting structured data from text...")
    json_result = text_summary_to_json(text_summary)
    print(f"✓ Extracted {len(json_result['objects'])} objects")
    
    # Include original text summary for reference
    json_result["text_summary"] = text_summary
    
    return json_result

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python vision_reka.py <image_path>")
        sys.exit(1)
    
    result = analyze_image(sys.argv[1])
    
    print("\n" + "="*60)
    print("REKA VISION OUTPUT (2-STAGE PIPELINE)")
    print("="*60)
    
    # Show the intermediate text summary
    print("\n📄 Text Summary:")
    print("-" * 60)
    print(result.get('text_summary', 'N/A'))
    print("-" * 60)
    
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