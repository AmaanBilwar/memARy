@component
export class NewScript extends BaseScriptComponent {
  private ImageQuality = CompressionQuality.LowQuality; // Changed from HighQuality
  private ImageEncoding = EncodingType.Jpg;
  private internetModule = require("LensStudio:InternetModule");
  private CameraModule = require('LensStudio:CameraModule');

  private url = "https://snaptest-one.vercel.app/api/upload";
  private cameraTexture: Texture;
  private hasProcessedWakeFrame = false;

  onAwake() {
    // Set up camera request outside of onAwake timing
    const delayedStart = this.createEvent("DelayedCallbackEvent");
    delayedStart.bind(() => {
      this.setupCamera();
    });
    delayedStart.reset(0.1);
  }

  setupCamera() {
    print("Setting up camera...");
    
    // Create camera request for left color camera with smaller resolution
    const cameraRequest = CameraModule.createCameraRequest();
    cameraRequest.cameraId = CameraModule.CameraId.Left_Color;
    cameraRequest.imageSmallerDimension = 320; // Add this - reduces resolution to 320px

    // Request camera and get texture
    this.cameraTexture = this.CameraModule.requestCamera(cameraRequest);
    
    // Cast to CameraTextureProvider to access onNewFrame
    const provider = this.cameraTexture.control as CameraTextureProvider;

    // Listen for new frames
    provider.onNewFrame.add((frame) => {
      this.onCameraFrame(frame);
    });

    print("Camera setup complete");
  }

  onCameraFrame(frame) {
    // Capture and post on first frame after wake
    if (!this.hasProcessedWakeFrame) {
      this.hasProcessedWakeFrame = true;
      print("Glasses awake - capturing and posting frame");
      this.captureAndPost();
    }
  }

  captureAndPost() {
    if (this.cameraTexture) {
      this.makeImageRequest(this.cameraTexture, "Glasses wake capture", (response) => {
        if (response) {
          print("Upload successful: " + JSON.stringify(response));
        } else {
          print("Upload failed");
        }
      });
    }
  }

  makeImageRequest(imageTex: Texture, prompt: string, callback) {
    print("Making image request...");
    Base64.encodeTextureAsync(
      imageTex,
      (base64String) => {
        print("Image encode Success!");
        print("Base64 length: " + base64String.length + " chars");
        
        // Calculate approximate size in KB
        const sizeKB = Math.round((base64String.length * 3 / 4) / 1024);
        print("Approximate image size: " + sizeKB + " KB");
        
        this.sendPOSTRequest({ prompt, base64String }, callback);
      },
      () => {
        print("Image encoding failed!");
        callback(null);
      },
      this.ImageQuality,
      this.ImageEncoding
    );
  }

  sendPOSTRequest(data: any, callback) {
    print("Sending POST request to: " + this.url);
    this.internetModule
      .fetch(this.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          "base64_image": data.base64String,
          "prompt": data.prompt
        })
      })
      .then((response) => {
        print("Response status: " + response.status);
        return response.json();
      })
      .then((data) => {
        print("Response data: " + JSON.stringify(data));
        callback(data);
      })
      .catch((e) => {
        print("Network error: " + e);
        callback(null);
      });
  }
}