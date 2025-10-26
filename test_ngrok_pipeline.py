#!/usr/bin/env python3
"""
Test Memary API Pipeline via Ngrok
Run this from ANY device with internet access!
"""
import requests
import json
import base64
import sys

# Your public ngrok URL
API_URL = "https://memary-chromadb.ngrok-free.app"

def test_text_pipeline():
    """Test: Text Summary -> Analyze -> Store"""
    print("🧪 Testing Text Pipeline...")
    print("-" * 60)
    
    response = requests.post(
        f"{API_URL}/store_text",
        json={
            "text_summary": "I see a red mug on the wooden desk next to my keys",
            "session_id": "test-session"
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Text stored successfully!")
        print(f"   Scene: {data['extracted_json']['scene']}")
        print(f"   Objects found: {len(data['extracted_json']['objects'])}")
        for obj in data['extracted_json']['objects']:
            print(f"      - {obj['label']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return False

def test_image_pipeline(image_path=None):
    """Test: Image -> Analyze -> Store"""
    print("\n🧪 Testing Image Pipeline...")
    print("-" * 60)
    
    if not image_path:
        print("⚠️  No image provided, skipping image test")
        print("   Usage: python test_ngrok_pipeline.py /path/to/image.jpg")
        return None
    
    try:
        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ Failed to read image: {e}")
        return False
    
    print(f"   Uploading image: {image_path}")
    
    response = requests.post(
        f"{API_URL}/store",
        json={
            "image_base64": image_b64,
            "session_id": "test-session"
        },
        timeout=60
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Image analyzed and stored successfully!")
        print(f"   Scene: {data['analysis']['scene']}")
        print(f"   Objects found: {len(data['analysis']['objects'])}")
        for obj in data['analysis']['objects'][:5]:  # Show first 5
            print(f"      - {obj['label']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return False

def test_search():
    """Test: Search memories"""
    print("\n🧪 Testing Search...")
    print("-" * 60)
    
    response = requests.get(
        f"{API_URL}/search",
        params={"query": "red mug"},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Search successful!")
        print(f"   Answer: {data['answer']}")
        print(f"   Matches: {data['matches']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        return False

def test_memories():
    """Test: Get all memories"""
    print("\n🧪 Testing Get Memories...")
    print("-" * 60)
    
    response = requests.get(f"{API_URL}/memories", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Memories retrieved!")
        print(f"   Total memories: {data['total']}")
        if data['memories']:
            print(f"   Most recent: {data['memories'][0]['scene']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        return False

def test_statistics():
    """Test: Get statistics"""
    print("\n🧪 Testing Statistics...")
    print("-" * 60)
    
    response = requests.get(f"{API_URL}/statistics", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Statistics retrieved!")
        print(f"   Total memories: {data['total_memories']}")
        print(f"   Total objects: {data['total_objects']}")
        print(f"   Storage mode: {data['storage_info']['mode']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        return False

def main():
    print("=" * 60)
    print("🌐 MEMARY NGROK API PIPELINE TEST")
    print("=" * 60)
    print(f"API URL: {API_URL}")
    print("=" * 60)
    print()
    
    # Check if image path provided
    image_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run all tests
    results = []
    
    results.append(("Text Pipeline", test_text_pipeline()))
    results.append(("Image Pipeline", test_image_pipeline(image_path)))
    results.append(("Search", test_search()))
    results.append(("Get Memories", test_memories()))
    results.append(("Statistics", test_statistics()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    for test_name, result in results:
        if result is True:
            icon = "✅"
        elif result is False:
            icon = "❌"
        else:
            icon = "⏭️"
        print(f"{icon} {test_name}")
    
    print(f"\nPassed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    if failed == 0 and passed > 0:
        print("\n🎉 All tests passed! Your pipeline is working!")
        print("\n📱 You can now use this API from:")
        print("   • Any phone/tablet")
        print("   • Other computers")
        print("   • IoT devices")
        print("   • Web/mobile apps")
        print(f"\n📖 See NGROK_API_USAGE.md for examples")
    elif failed > 0:
        print("\n⚠️  Some tests failed. Check:")
        print("   1. Is ngrok running? (./deploy_ngrok.sh)")
        print("   2. Is the URL correct?")
        print("   3. Check logs: tail -f logs/*.log")
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  Tests interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

