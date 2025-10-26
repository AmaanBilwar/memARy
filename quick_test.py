#!/usr/bin/env python3
"""
Quick test script to demonstrate the POST commands
"""

import requests
import json

def test_text_memory():
    """Test text-based memory requests"""
    url = "http://localhost:8000/process"
    
    test_cases = [
        "Remember this picture I am looking at",
        "Save this image as a memory", 
        "I want to remember what I am seeing right now",
        "Store this photo in my memory"
    ]
    
    print("🧪 Testing text-based image memory requests...")
    print("=" * 50)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{text}'")
        
        payload = {
            "text": text,
            "session_id": "test-session"
        }
        
        try:
            response = requests.post(url, json=payload)
            result = response.json()
            
            if result.get('success'):
                print(f"✅ Success: {result.get('message', 'No message')}")
                print(f"🔧 Tool used: {result.get('tool_used', 'No tool')}")
            else:
                print(f"⚠️ Response: {result.get('message', 'No message')}")
                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")

def show_curl_examples():
    """Show curl command examples"""
    print("\n📋 CURL Command Examples:")
    print("=" * 50)
    
    print("\n1️⃣ Text-based image memory request:")
    print('curl -X POST "http://localhost:8000/process" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"text": "Remember this picture", "session_id": "my-session"}\'')
    
    print("\n2️⃣ Direct image upload:")
    print('curl -X POST "http://localhost:8000/process-image" \\')
    print('  -F "file=@your_image.jpg" \\')
    print('  -F "user_context=This is my workspace" \\')
    print('  -F "session_id=my-session"')

if __name__ == "__main__":
    print("🚀 Quick Test for Image Memory POST Commands")
    print("=" * 60)
    
    # Test text-based requests
    test_text_memory()
    
    # Show curl examples
    show_curl_examples()
    
    print("\n✨ Test complete! Your agent is ready to handle image memories.")
