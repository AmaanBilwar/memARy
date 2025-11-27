"""
Integration test demonstrating microservice communication
Shows how to test service-to-service calls
"""
import requests
import time

# Service URLs
VECTOR_STORE_URL = "http://localhost:8001"
QUERY_SERVICE_URL = "http://localhost:8002"


def test_health_checks():
    """Test both services are running"""
    print("Testing health checks...")
    
    # Check vector store
    resp = requests.get(f"{VECTOR_STORE_URL}/healthz")
    assert resp.status_code == 200, "Vector store not healthy"
    print("✓ Vector store is healthy")
    
    # Check query service
    resp = requests.get(f"{QUERY_SERVICE_URL}/health")
    assert resp.status_code == 200, "Query service not healthy"
    print("✓ Query service is healthy")
    
    data = resp.json()
    assert data["vector_store"] == "connected", "Query service can't reach vector store"
    print("✓ Query service connected to vector store")


def test_store_and_retrieve():
    """Test complete flow: Store → Query → Retrieve"""
    print("\nTesting store and retrieve flow...")
    
    # Step 1: Store data directly in vector store
    print("1. Storing frame in vector store...")
    frame_data = {
        "tenant_id": "test_user",
        "device_id": "test_device",
        "session_id": "test_session",
        "frame_ts": int(time.time()),
        "scene_summary": "Office desk with silver keys on the left side",
        "objects": [
            {
                "label": "keys",
                "confidence": 0.95,
                "color": "silver",
                "rel_pos": "left side of desk",
                "is_person": False
            }
        ]
    }
    
    resp = requests.post(f"{VECTOR_STORE_URL}/add_frame", json=frame_data)
    assert resp.status_code == 200, f"Failed to store frame: {resp.text}"
    result = resp.json()
    print(f"✓ Frame stored: {result['frame_id']}")
    
    # Step 2: Query through the query service
    print("2. Querying through query service...")
    query_data = {
        "user_id": "test_user",
        "object_name": "keys"
    }
    
    resp = requests.post(f"{QUERY_SERVICE_URL}/where-is", json=query_data)
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    result = resp.json()
    
    print(f"✓ Query successful!")
    print(f"   Found: {result['found']}")
    if result['found']:
        print(f"   Location: {result.get('location', 'N/A')}")
        print(f"   Confidence: {result.get('confidence', 'N/A')}")
    
    assert result['found'] == True, "Object should be found"


def test_semantic_search():
    """Test semantic search through query service"""
    print("\nTesting semantic search...")
    
    search_data = {
        "user_id": "test_user",
        "query": "silver keys on desk",
        "limit": 5
    }
    
    resp = requests.post(f"{QUERY_SERVICE_URL}/search", json=search_data)
    assert resp.status_code == 200, f"Search failed: {resp.text}"
    result = resp.json()
    
    print(f"✓ Search completed")
    print(f"   Query: {result['query']}")
    print(f"   Results: {len(result['results'])}")
    
    if result['results']:
        print(f"   Top result: {result['results'][0]['text'][:50]}...")
        print(f"   Relevance: {result['results'][0]['relevance_score']:.2f}")


def test_recent_memories():
    """Test recent memories endpoint"""
    print("\nTesting recent memories...")
    
    resp = requests.get(f"{QUERY_SERVICE_URL}/user/test_user/recent?limit=5")
    assert resp.status_code == 200, f"Recent memories failed: {resp.text}"
    result = resp.json()
    
    print(f"✓ Retrieved recent memories")
    if "results" in result:
        print(f"   Found: {len(result['results'])} results")


def main():
    """Run all integration tests"""
    print("="*60)
    print("MICROSERVICE INTEGRATION TESTS")
    print("="*60)
    print()
    print("Make sure both services are running:")
    print("  - Vector Store: http://localhost:8001")
    print("  - Query Service: http://localhost:8002")
    print()
    
    try:
        test_health_checks()
        test_store_and_retrieve()
        test_semantic_search()
        test_recent_memories()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nYour microservices are communicating correctly! 🎉")
        
    except AssertionError as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        return 1
    
    except requests.exceptions.ConnectionError as e:
        print("\n" + "="*60)
        print(f"❌ CONNECTION ERROR: {e}")
        print("="*60)
        print("\nMake sure services are running:")
        print("  Terminal 1: cd vector-store && python app.py")
        print("  Terminal 2: cd example-client-service && python query_service.py")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

