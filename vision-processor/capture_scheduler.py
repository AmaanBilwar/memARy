"""
Smart Capture Scheduler: 30-second intervals + trigger events
Optimized for storage savings while maintaining responsiveness
"""
import os
import time
import threading
from typing import Callable, Optional
from dotenv import load_dotenv
from integration_reka import process_image_to_memory
from camera_stream import CameraStream

load_dotenv()

# Configuration
CAPTURE_INTERVAL = int(os.getenv("CAPTURE_INTERVAL_SECONDS", "30"))  # 30 seconds default
MIN_TRIGGER_GAP = int(os.getenv("MIN_TRIGGER_GAP_SECONDS", "3"))    # Debounce triggers

class CaptureScheduler:
    """
    Manages image capture timing:
    - Automatic: Every 30 seconds
    - Manual: On trigger events (user button, motion detection, etc.)
    """
    
    def __init__(
        self, 
        capture_func: Callable,
        interval: int = CAPTURE_INTERVAL,
        min_trigger_gap: int = MIN_TRIGGER_GAP
    ):
        self.capture_func = capture_func
        self.interval = interval
        self.min_trigger_gap = min_trigger_gap
        
        self.running = False
        self.last_capture_time = 0
        self.session_id = f"session_{int(time.time())}"
        self.capture_count = 0
        
        self._thread = None
        self._lock = threading.Lock()
    
    def start(self):
        """Start automatic capture loop"""
        if self.running:
            print("⚠️  Scheduler already running")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print(f"✓ Capture scheduler started (interval: {self.interval}s)")
    
    def stop(self):
        """Stop capture loop"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("✓ Capture scheduler stopped")
    
    def trigger_capture(self, reason: str = "manual_trigger") -> dict:
        """
        Manually trigger a capture (user button, motion detected, etc.)
        Debounced: Ignores triggers within MIN_TRIGGER_GAP seconds
        """
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_capture_time
            
            # Debounce: Prevent rapid-fire triggers
            if time_since_last < self.min_trigger_gap:
                return {
                    "ok": False,
                    "reason": "debounced",
                    "wait_seconds": self.min_trigger_gap - time_since_last
                }
            
            # Execute capture
            result = self._execute_capture(reason=reason)
            return result
    
    def _capture_loop(self):
        """Background thread for automatic periodic captures"""
        print(f"🔄 Starting automatic capture every {self.interval}s")
        
        while self.running:
            try:
                # Wait for interval
                time.sleep(self.interval)
                
                if not self.running:
                    break
                
                # Execute capture
                with self._lock:
                    self._execute_capture(reason="scheduled")
                    
            except Exception as e:
                print(f"❌ Capture loop error: {e}")
                time.sleep(5)  # Brief pause on error
    
    def _execute_capture(self, reason: str = "scheduled") -> dict:
        """
        Internal: Execute single capture
        (Called by both scheduled loop and manual triggers)
        """
        try:
            # Call the provided capture function (e.g., take photo from camera)
            image_path = self.capture_func()
            
            if not image_path or not os.path.exists(image_path):
                return {"ok": False, "error": "capture_failed"}
            
            # Process through vision pipeline
            result = process_image_to_memory(
                image_path=image_path,
                session_id=self.session_id
            )
            
            # Update state
            self.last_capture_time = time.time()
            self.capture_count += 1
            
            print(f"📸 Capture #{self.capture_count} ({reason}): {result['ok']}")
            
            return {
                "ok": result["ok"],
                "reason": reason,
                "capture_number": self.capture_count,
                "result": result
            }
            
        except Exception as e:
            print(f"❌ Capture execution error: {e}")
            return {"ok": False, "error": str(e)}
    
    def get_stats(self) -> dict:
        """Get capture statistics"""
        return {
            "running": self.running,
            "session_id": self.session_id,
            "capture_count": self.capture_count,
            "last_capture_ago": time.time() - self.last_capture_time if self.last_capture_time else None,
            "interval_seconds": self.interval
        }


# === Camera Integration ===

# Global camera instance (shared across captures)
_camera = None

def get_camera() -> CameraStream:
    """Get or initialize camera stream"""
    global _camera
    if _camera is None:
        camera_id = int(os.getenv("CAMERA_ID", "0"))
        save_dir = os.getenv("CAPTURE_SAVE_DIR", "/tmp/captures")
        _camera = CameraStream(camera_id=camera_id, save_dir=save_dir)
        if not _camera.start():
            raise RuntimeError("Failed to start camera stream")
        print(f"✓ Camera stream initialized: {_camera.get_info()}")
    return _camera

def live_camera_capture() -> str:
    """
    Capture live frame from camera stream
    Uses webcam by default, replace with AR glasses camera API
    """
    try:
        camera = get_camera()
        frame_path = camera.capture_frame()
        
        if frame_path:
            return frame_path
        else:
            print("⚠️  Camera capture returned None, falling back to test image")
            return "test_images/desk_scene.jpg"
            
    except Exception as e:
        print(f"❌ Camera error: {e}, falling back to test image")
        return "test_images/desk_scene.jpg"

def dummy_camera_capture() -> str:
    """
    Test mode: uses static test image
    Use this for testing without camera
    """
    return "test_images/desk_scene.jpg"


if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("CAPTURE SCHEDULER - 30s Intervals + Triggers")
    print("="*60)
    
    # Check for test mode flag
    use_test_mode = "--test" in sys.argv
    
    if use_test_mode:
        print("\n🧪 TEST MODE: Using static test image")
        capture_func = dummy_camera_capture
    else:
        print("\n📷 LIVE MODE: Using camera stream")
        capture_func = live_camera_capture
    
    # Create scheduler
    scheduler = CaptureScheduler(
        capture_func=capture_func,
        interval=30,  # 30 seconds
        min_trigger_gap=3  # 3 second debounce
    )
    
    # Start automatic captures
    scheduler.start()
    
    print("\nScheduler running. Commands:")
    print("  't' - Trigger manual capture")
    print("  's' - Show statistics")
    print("  'q' - Quit")
    print()
    
    try:
        while True:
            cmd = input("> ").strip().lower()
            
            if cmd == 't':
                result = scheduler.trigger_capture(reason="user_button")
                if result["ok"]:
                    print(f"✓ Triggered capture #{result['capture_number']}")
                else:
                    print(f"✗ {result.get('reason', 'failed')}")
                    if "wait_seconds" in result:
                        print(f"  Wait {result['wait_seconds']:.1f}s")
            
            elif cmd == 's':
                stats = scheduler.get_stats()
                print("\n📊 Statistics:")
                print(f"  Running: {stats['running']}")
                print(f"  Captures: {stats['capture_count']}")
                print(f"  Last capture: {stats['last_capture_ago']:.1f}s ago" if stats['last_capture_ago'] else "  Last capture: Never")
                print(f"  Interval: {stats['interval_seconds']}s\n")
            
            elif cmd == 'q':
                break
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    
    finally:
        scheduler.stop()
        
        # Cleanup camera if it was initialized
        global _camera
        if _camera is not None:
            _camera.stop()
            _camera = None
        
        print("✓ Shutdown complete")

