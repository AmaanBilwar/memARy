#!/usr/bin/env python3
"""
Comprehensive test suite for AR Glasses Vector Memory Store.
Run server first: python app.py
Then run this: python test_api.py
"""
import requests
import time
from colorama import init, Fore, Style

init(autoreset=True)

BASE_URL = "http://localhost:8001"
TENANT = "test_user_1"

def print_test(name):
    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}{Style.RESET_ALL}")

def print_pass(msg):
    print(f"{Fore.GREEN}✓ {msg}{Style.RESET_ALL}")

def print_fail(msg):
    print(f"{Fore.RED}✗ {msg}{Style.RESET_ALL}")

def test_health():
    print_test("Health Check")
    try:
        r = requests.get(f"{BASE_URL}/healthz")
        data = r.json()
        if data.get("ok"):
            print_pass("Health check passed")
            print(f"Collections: {data.get('collections')}")
            return True
        print_fail("Health check failed")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        return False

def test_add_frame_kitchen():
    print_test("Add Frame - Kitchen Scene")
    ts = int(time.time())
    payload = {
        "tenant_id": TENANT,
        "device_id": "glasses_01",
        "session_id": "session_001",
        "frame_ts": ts,
        "tz": "America/Los_Angeles",
        "lat_lon_hash": "9q8yy",
        "scene_summary": "Kitchen table in view. Red mug on left, silver keys near edge.",
        "objects": [
            {
                "label": "mug",
                "confidence": 0.88,
                "bbox": [0.12, 0.34, 0.08, 0.12],
                "color": "red",
                "rel_pos": "left side"
            },
            {
                "label": "keys",
                "confidence": 0.93,
                "bbox": [0.42, 0.61, 0.13, 0.08],
                "color": "silver",
                "rel_pos": "near edge"
            }
        ]
    }
    try:
        r = requests.post(f"{BASE_URL}/add_frame", json=payload)
        data = r.json()
        if data.get("ok"):
            print_pass("Frame added successfully")
            print(f"Frame ID: {data['frame_id']}")
            print(f"Entity IDs: {data['entity_ids']}")
            print(f"Latest upserted: {data['latest_upserted']}")
            return True, ts
        print_fail(f"Failed: {data}")
        return False, None
    except Exception as e:
        print_fail(f"Error: {e}")
        return False, None

def test_add_frame_with_person():
    print_test("Add Frame - Person Detection (Privacy Safeguard)")
    ts = int(time.time()) + 10
    payload = {
        "tenant_id": TENANT,
        "device_id": "glasses_01",
        "session_id": "session_001",
        "frame_ts": ts,
        "scene_summary": "Living room. Person on couch with phone.",
        "objects": [
            {
                "label": "person",
                "confidence": 0.95,
                "is_person": True,
                "relationship_hint": "mom"
            },
            {
                "label": "phone",
                "confidence": 0.89,
                "color": "black",
                "rel_pos": "in hand"
            }
        ]
    }
    try:
        r = requests.post(f"{BASE_URL}/add_frame", json=payload)
        data = r.json()
        if data.get("ok"):
            print_pass("Person detection with privacy safeguard passed")
            print(f"Phone upserted to latest: {data['latest_upserted']}")
            return True
        print_fail(f"Failed: {data}")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        return False

def test_low_confidence_filter():
    print_test("Low Confidence Filter (Hallucination Guard)")
    ts = int(time.time()) + 20
    payload = {
        "tenant_id": TENANT,
        "device_id": "glasses_01",
        "session_id": "session_001",
        "frame_ts": ts,
        "scene_summary": "Blurry table scene.",
        "objects": [
            {
                "label": "wallet",
                "confidence": 0.45,  # Below threshold
                "color": "brown"
            }
        ]
    }
    try:
        r = requests.post(f"{BASE_URL}/add_frame", json=payload)
        data = r.json()
        if data.get("ok") and len(data.get("latest_upserted", [])) == 0:
            print_pass("Low confidence correctly NOT upserted to latest")
            return True
        print_fail("Low confidence safeguard failed")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        return False

def test_add_note():
    print_test("Add User Note ('Remember This')")
    payload = {
        "tenant_id": TENANT,
        "text": "Mom's pills are in the left kitchen cabinet, top shelf.",
        "modality": "voice",
        "priority": "high",
        "tags": ["medication", "important"],
        "linked_entity": "pills@home"
    }
    try:
        r = requests.post(f"{BASE_URL}/add_note", json=payload)
        data = r.json()
        if data.get("ok"):
            print_pass("Note added successfully")
            print(f"Note ID: {data['note_id']}")
            return True, data['note_id']
        print_fail(f"Failed: {data}")
        return False, None
    except Exception as e:
        print_fail(f"Error: {e}")
        return False, None

def test_search_last_seen():
    print_test("Search Last Seen - 'Where are my keys?'")
    payload = {
        "tenant_id": TENANT,
        "canonical_key": "keys@home"
    }
    try:
        r = requests.post(f"{BASE_URL}/search_last_seen", json=payload)
        data = r.json()
        if data.get("ok") and data.get("found"):
            print_pass("Found keys location")
            print(f"Document: {data['document']}")
            print(f"Last seen: {data['metadata']['last_frame_ts']}")
            return True
        print_fail(f"Keys not found: {data}")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        return False

def test_search_semantic():
    print_test("Semantic Search - 'When did I see the red mug?'")
    payload = {
        "tenant_id": TENANT,
        "query_text": "red mug",
        "collections": ["entities_stream_v1"],
        "n_results": 3
    }
    try:
        r = requests.post(f"{BASE_URL}/search_semantic", json=payload)
        data = r.json()
        if data.get("ok"):
            print_pass(f"Found {len(data['results'])} results")
            for res in data['results'][:2]:
                print(f"  - {res['document']} (distance: {res['distance']:.3f})")
            return True
        print_fail(f"Failed: {data}")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        return False

def test_search_time_window(start_ts):
    print_test("Time Window Search - 'What happened around timestamp?'")
    payload = {
        "tenant_id": TENANT,
        "start_ts": start_ts - 100,
        "end_ts": start_ts + 100,
        "n_results": 10
    }
    try:
        r = requests.post(f"{BASE_URL}/search_time_window", json=payload)
        data = r.json()
        if data.get("ok"):
            print_pass(f"Found {len(data['results'])} frames in window")
            for res in data['results'][:2]:
                print(f"  - {res['metadata']['frame_ts']}: {res['document'][:60]}...")
            return True
        print_fail(f"Failed: {data}")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        return False

def test_curate_to_ltm():
    print_test("Curate to Long-Term Memory (Session Review)")
    payload = {
        "tenant_id": TENANT,
        "session_id": "session_001",
        "items": [
            {
                "origin": "note",
                "origin_id": f"{TENANT}:note:test1",
                "text": "Spare keys are in the blue bowl by the front door."
            },
            {
                "origin": "manual",
                "origin_id": "manual_1",
                "text": "Mom prefers her pills with breakfast."
            }
        ],
        "tags": ["curated", "important"]
    }
    try:
        r = requests.post(f"{BASE_URL}/curate_to_ltm", json=payload)
        data = r.json()
        if data.get("ok"):
            print_pass(f"Curated {data['curated']} items to LTM")
            return True
        print_fail(f"Failed: {data}")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        return False

def test_compact():
    print_test("Compact (TTL Enforcement)")
    payload = {
        "tenant_id": TENANT,
        "ttl_hours": 1  # Would delete anything older than 1 hour
    }
    try:
        r = requests.post(f"{BASE_URL}/compact", json=payload)
        data = r.json()
        if data.get("ok"):
            print_pass(f"Compaction ran successfully")
            print(f"Cutoff timestamp: {data['cutoff_ts']}")
            return True
        print_fail(f"Failed: {data}")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        return False

def main():
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"AR GLASSES VECTOR MEMORY STORE - TEST SUITE")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    
    results = {}
    
    # Run tests
    results["Health"] = test_health()
    time.sleep(0.5)
    
    success, first_ts = test_add_frame_kitchen()
    results["Add Frame (Kitchen)"] = success
    time.sleep(0.5)
    
    results["Add Frame (Person)"] = test_add_frame_with_person()
    time.sleep(0.5)
    
    results["Low Confidence Filter"] = test_low_confidence_filter()
    time.sleep(0.5)
    
    note_success, note_id = test_add_note()
    results["Add Note"] = note_success
    time.sleep(0.5)
    
    results["Search Last Seen"] = test_search_last_seen()
    time.sleep(0.5)
    
    results["Semantic Search"] = test_search_semantic()
    time.sleep(0.5)
    
    if first_ts:
        results["Time Window Search"] = test_search_time_window(first_ts)
        time.sleep(0.5)
    
    results["Curate to LTM"] = test_curate_to_ltm()
    time.sleep(0.5)
    
    results["Compact"] = test_compact()
    
    # Summary
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        status = f"{Fore.GREEN}✓ PASS" if success else f"{Fore.RED}✗ FAIL"
        print(f"{status} - {name}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Result: {passed}/{total} tests passed{Style.RESET_ALL}")
    
    if passed == total:
        print(f"{Fore.GREEN}\n🎉 All tests passed! Architecture working perfectly.{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.YELLOW}\n⚠️  Some tests failed. Check server logs.{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
