#!/usr/bin/env python3
"""
Test the API endpoints with the simple memory store.
"""
import requests
import base64
from PIL import Image
import io

def test_image_processing():
    """Test the /process-image endpoint."""
    print("Testing /process-image endpoint...")
    
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='green')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    base64_data = base64.b64encode(img_data).decode('utf-8')
    
    # Test the /process-image endpoint
    url = 'http://localhost:8000/process-image'
    payload = {
        'base64_image': f'data:image/png;base64,{base64_data}',
        'user_context': 'This is a test green square',
        'session_id': 'api-test-session'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Message: {result['message'][:100]}...")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_memories_listing():
    """Test the /memories endpoint."""
    print("\nTesting /memories endpoint...")
    
    try:
        response = requests.get('http://localhost:8000/memories')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Count: {result['count']}")
            print(f"Memories: {len(result['memories'])} found")
            
            for i, memory in enumerate(result['memories'][:2]):
                print(f"  {i+1}. {memory['description'][:50]}...")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_text_memory():
    """Test storing a text memory via the agent."""
    print("\nTesting text memory storage...")
    
    url = 'http://localhost:8000/process'
    payload = {
        'text': 'I want to remember that I bought milk today',
        'session_id': 'api-test-session'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Message: {result['message']}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    print("Testing memARy API with simple memory store...")
    
    # Test image processing
    image_success = test_image_processing()
    
    # Test text memory
    text_success = test_text_memory()
    
    # Test memory listing
    list_success = test_memories_listing()
    
    print(f"\nResults:")
    print(f"Image processing: {'PASS' if image_success else 'FAIL'}")
    print(f"Text memory: {'PASS' if text_success else 'FAIL'}")
    print(f"Memory listing: {'PASS' if list_success else 'FAIL'}")
    
    if all([image_success, text_success, list_success]):
        print("\nAll tests passed! Memory operations are working correctly.")
    else:
        print("\nSome tests failed. Check the errors above.")
