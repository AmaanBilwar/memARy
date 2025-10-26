#!/usr/bin/env python3
"""
Test script for image memory functionality
This script demonstrates how to use the new image memory features.
"""

import requests
import json
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_IMAGE_PATH = "test_image.jpg"  # Replace with path to a test image

def test_image_upload():
    """Test uploading an image and storing it as memory"""
    
    # Check if test image exists
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"❌ Test image not found at {TEST_IMAGE_PATH}")
        print("Please place a test image file at this location or update TEST_IMAGE_PATH")
        return False
    
    # Prepare the request
    url = f"{API_BASE_URL}/process-image"
    
    with open(TEST_IMAGE_PATH, 'rb') as image_file:
        files = {'file': (TEST_IMAGE_PATH, image_file, 'image/jpeg')}
        data = {
            'user_context': 'This is a test image for memory storage',
            'session_id': 'test-session'
        }
        
        print(f"📤 Uploading image: {TEST_IMAGE_PATH}")
        print(f"🔗 API endpoint: {url}")
        
        try:
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Image uploaded successfully!")
                print(f"📝 Description: {result.get('message', 'No description')}")
                
                if 'data' in result:
                    data = result['data']
                    print(f"🤖 AI Description: {data.get('image_description', 'No AI description')}")
                    print(f"👤 User Context: {data.get('user_context', 'No user context')}")
                
                return True
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return False

def test_text_based_image_memory():
    """Test storing image memory through text-based agent"""
    
    url = f"{API_BASE_URL}/process"
    
    # Test cases for different ways users might ask to save images
    test_cases = [
        "Remember this picture I'm looking at",
        "Save this image as a memory",
        "I want to remember what I'm seeing right now",
        "Store this photo in my memory"
    ]
    
    print("\n🧪 Testing text-based image memory requests...")
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{test_text}'")
        
        payload = {
            "text": test_text,
            "session_id": "test-session"
        }
        
        try:
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Agent response: {result.get('message', 'No message')}")
                    print(f"🔧 Tool used: {result.get('tool_used', 'No tool')}")
                else:
                    print(f"⚠️ Agent response: {result.get('message', 'No message')}")
                    if 'error' in result:
                        print(f"❌ Error: {result['error']}")
            else:
                print(f"❌ Request failed with status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")

def main():
    """Main test function"""
    print("🚀 Testing Image Memory Functionality")
    print("=" * 50)
    
    # Test 1: Direct image upload
    print("\n1️⃣ Testing direct image upload...")
    test_image_upload()
    
    # Test 2: Text-based image memory requests
    print("\n2️⃣ Testing text-based image memory requests...")
    test_text_based_image_memory()
    
    print("\n" + "=" * 50)
    print("🏁 Testing complete!")
    
    print("\n📋 How to use image memory:")
    print("1. Direct upload: POST /process-image with image file")
    print("2. Text request: POST /process with text like 'remember this picture'")
    print("3. The agent will use store_image_memory tool automatically")

if __name__ == "__main__":
    main()
