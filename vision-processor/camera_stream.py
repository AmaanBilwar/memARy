"""
Camera Stream Capture
Captures real-time frames from video stream (webcam or AR glasses)
"""
import cv2
import os
import time
from typing import Optional

class CameraStream:
    """
    Manages video stream capture from camera
    Replace with AR glasses camera API when ready
    """
    
    def __init__(self, camera_id: int = 0, save_dir: str = "/tmp/captures"):
        """
        Initialize camera stream
        
        Args:
            camera_id: Camera device ID (0 = default webcam)
            save_dir: Directory to save captured frames
        """
        self.camera_id = camera_id
        self.save_dir = save_dir
        self.cap = None
        self.is_open = False
        
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
    
    def start(self) -> bool:
        """
        Start the camera stream
        
        Returns:
            True if successful, False otherwise
        """
        if self.is_open:
            print("⚠️  Camera already open")
            return True
        
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                print(f"❌ Failed to open camera {self.camera_id}")
                return False
            
            # Set camera properties for better quality
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.is_open = True
            print(f"✓ Camera {self.camera_id} opened successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error opening camera: {e}")
            return False
    
    def stop(self):
        """Stop the camera stream and release resources"""
        if self.cap is not None:
            self.cap.release()
            self.is_open = False
            print("✓ Camera stream stopped")
    
    def capture_frame(self) -> Optional[str]:
        """
        Capture current frame from stream and save to file
        
        Returns:
            Path to saved image file, or None if capture failed
        """
        if not self.is_open or self.cap is None:
            print("❌ Camera not open. Call start() first.")
            return None
        
        try:
            # Read frame from camera
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                print("❌ Failed to capture frame")
                return None
            
            # Generate unique filename with timestamp
            timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
            filename = f"capture_{timestamp}.jpg"
            filepath = os.path.join(self.save_dir, filename)
            
            # Save frame as JPEG
            success = cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            if not success:
                print(f"❌ Failed to save frame to {filepath}")
                return None
            
            return filepath
            
        except Exception as e:
            print(f"❌ Error capturing frame: {e}")
            return None
    
    def get_frame_preview(self) -> Optional[bytes]:
        """
        Get current frame as bytes (for preview/display)
        
        Returns:
            Frame as JPEG bytes, or None if failed
        """
        if not self.is_open or self.cap is None:
            return None
        
        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                return None
            
            # Encode frame as JPEG
            success, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if success:
                return encoded.tobytes()
            return None
            
        except Exception as e:
            print(f"❌ Error getting preview: {e}")
            return None
    
    def get_info(self) -> dict:
        """Get camera stream information"""
        if not self.is_open or self.cap is None:
            return {"is_open": False}
        
        return {
            "is_open": self.is_open,
            "camera_id": self.camera_id,
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": int(self.cap.get(cv2.CAP_PROP_FPS)),
            "save_dir": self.save_dir
        }
    
    def __enter__(self):
        """Context manager support"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.stop()


# === Example Usage ===

if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("CAMERA STREAM CAPTURE TEST")
    print("="*60)
    
    # Initialize camera
    camera = CameraStream(camera_id=0, save_dir="/tmp/captures")
    
    if not camera.start():
        print("\n❌ Failed to start camera")
        print("\nTroubleshooting:")
        print("1. Check if camera is connected")
        print("2. Check if another app is using the camera")
        print("3. Try a different camera_id (0, 1, 2, etc.)")
        sys.exit(1)
    
    # Show camera info
    info = camera.get_info()
    print(f"\n📷 Camera Info:")
    print(f"   Resolution: {info['width']}x{info['height']}")
    print(f"   FPS: {info['fps']}")
    print(f"   Save directory: {info['save_dir']}")
    
    print("\n🎬 Camera is live! Commands:")
    print("   'c' - Capture frame")
    print("   'i' - Show camera info")
    print("   'q' - Quit")
    print()
    
    try:
        capture_count = 0
        
        while True:
            cmd = input("> ").strip().lower()
            
            if cmd == 'c':
                filepath = camera.capture_frame()
                if filepath:
                    capture_count += 1
                    print(f"✓ Captured #{capture_count}: {filepath}")
                else:
                    print("✗ Capture failed")
            
            elif cmd == 'i':
                info = camera.get_info()
                print(f"\n📷 Camera Info:")
                for key, value in info.items():
                    print(f"   {key}: {value}")
                print()
            
            elif cmd == 'q':
                break
            
            else:
                print("Unknown command. Use 'c', 'i', or 'q'")
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    
    finally:
        camera.stop()
        print(f"✓ Captured {capture_count} frames total")
        print("✓ Shutdown complete")

