@component
export class NewScript extends BaseScriptComponent {
  private ImageQuality = CompressionQuality.HighQuality;
  private ImageEncoding = EncodingType.Jpg;
  private internetModule = require("LensStudio:InternetModule");
  private cameraModule = require('LensStudio:CameraModule');

  private url = "https://snaptest-one.vercel.app/api/upload";
  private cameraTexture: Texture;
  private hasProcessedWakeFrame = false;

  onAwake() {
    // Set up camera request outside of onAwake timing
    const delayEvent = this.createEvent("DelayedCallbackEvent");
    delayEvent.bind(this.setupCamera.bind(this));
    delayEvent.reset(0.1);
  }

  setupCamera() {
    // Create camera request for left color camera
    const cameraRequest = this.cameraModule.createCameraRequest();
    cameraRequest.cameraId = this.cameraModule.CameraId.Left_Color;

    // Request camera and get texture
    this.cameraTexture = this.cameraModule.requestCamera(cameraRequest);

    // Get CameraTextureProvider and listen for new frames
    const cameraTextureProvider: CameraTextureProvider = this.cameraTexture.control;
    const onNewFrame = cameraTextureProvider.onNewFrame;
    const registration = onNewFrame.add((frame) => {
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
        print("Base64 length: " + base64String.length);
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