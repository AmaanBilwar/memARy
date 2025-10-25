@component
export class WsAviStreamer extends BaseScriptComponent {
  @input
  statusText: Text;
  
  @input
  uiImage: Image;
  
  @input
  websocketUrl: string = "ws://192.168.1.100:8765";
  
  private cameraModule: CameraModule = require('LensStudio:CameraModule');
  private internetModule: InternetModule = require('LensStudio:InternetModule');
  private ws: WebSocket | null = null;
  private cameraTexture: Texture;
  private cameraTextureProvider: CameraTextureProvider;
  
  // Audio playback
  private audioComponent: AudioComponent;
  private audioTrackAsset: AudioTrackAsset;
  
  // State
  private frameCount: number = 0;
  private isEncodingVideo: boolean = false;
  private wsConnected: boolean = false;
  
  onAwake() {
    print("=== WS AVI Streamer Init ===");
    this.createEvent('OnStartEvent').bind(() => this.start());
    this.createEvent('OnDestroyEvent').bind(() => this.stop());
  }
  
  private async start() {
    print("Starting streamer...");
    print(`Connecting to: ${this.websocketUrl}`);
    
    // 1) Open WebSocket using InternetModule
    try {
      this.ws = this.internetModule.createWebSocket(this.websocketUrl);
      this.ws.binaryType = 'blob';
      print("WebSocket object created");
      
      this.ws.onopen = (event: WebSocketEvent) => {
        print("✅ WebSocket CONNECTED!");
        this.wsConnected = true;
        if (this.statusText) {
          this.statusText.text = "🟢 CONNECTED";
        }
      };
      
      this.ws.onmessage = async (event: WebSocketMessageEvent) => {
        print("📨 Received message from server");
        if (event.data instanceof Blob) {
          const bytes = await event.data.bytes();
          this.onInboundAudio(bytes);
        }
      };
      
      this.ws.onclose = (event: WebSocketCloseEvent) => {
        print(`❌ WebSocket closed - code: ${event.code}, clean: ${event.wasClean}`);
        this.wsConnected = false;
        if (this.statusText) {
          this.statusText.text = "🔴 DISCONNECTED";
        }
      };
      
      this.ws.onerror = (event: WebSocketEvent) => {
        print('⚠️ WebSocket ERROR occurred');
        this.wsConnected = false;
        if (this.statusText) {
          this.statusText.text = "⚠️ ERROR";
        }
      };
    } catch (e) {
      print(`Failed to create WebSocket: ${e}`);
      return;
    }
    
    // 2) Setup camera for video frames
    this.setupCamera();
    
    // 3) Setup audio playback
    this.setupAudioPlayback();
    
    print("✅ Streamer started");
  }
  
  private stop() {
    print("Stopping streamer...");
    try { 
      if (this.ws) {
        this.ws.close(); 
      }
    } catch(_) {}
    this.ws = null;
    this.wsConnected = false;
  }
  
  private setupCamera() {
    print("Setting up camera...");
    const cameraRequest = CameraModule.createCameraRequest();
    cameraRequest.cameraId = CameraModule.CameraId.Default_Color;
    cameraRequest.imageSmallerDimension = 640;
    
    this.cameraTexture = this.cameraModule.requestCamera(cameraRequest);
    this.cameraTextureProvider = this.cameraTexture.control as CameraTextureProvider;
    
    print(`Camera: ${this.cameraTexture.getWidth()}x${this.cameraTexture.getHeight()}`);
    
    // Preview
    if (this.uiImage) {
      print("Setting up camera preview");
      this.cameraTextureProvider.onNewFrame.add(() => {
        if (this.uiImage) {
          this.uiImage.mainPass.baseTex = this.cameraTexture;
        }
      });
    }
    
    // Video capture - every 3rd frame (~10fps)
    let videoFrameSkip = 0;
    this.cameraTextureProvider.onNewFrame.add(() => {
      videoFrameSkip++;
      if (videoFrameSkip % 30 === 0) {
        print(`Camera frame #${videoFrameSkip}, connected: ${this.wsConnected}, encoding: ${this.isEncodingVideo}`);
      }
      
      if (videoFrameSkip % 3 === 0 && !this.isEncodingVideo && this.wsConnected) {
        this.captureAndSendVideoFrame();
      }
    });
    
    print("✅ Camera ready");
  }
  
  private setupAudioPlayback() {
    try {
      this.audioComponent = this.getSceneObject().createComponent("Component.AudioComponent") as AudioComponent;
      print("✅ Audio playback ready");
    } catch (e) {
      print("Audio playback setup error: " + e);
    }
  }
  
  // ============================================
  // VIDEO ENCODING & SENDING
  // ============================================
  
  private async captureAndSendVideoFrame() {
    print("🎬 Attempting to capture frame...");
    this.isEncodingVideo = true;
    
    try {
      print("Creating image request...");
      const imageRequest = CameraModule.createImageRequest();
      
      print("Requesting image...");
      const imageFrame = await this.cameraModule.requestImage(imageRequest);
      
      this.frameCount++;
      print(`Got image frame #${this.frameCount}`);
      
      // Encode to JPEG
      print("Encoding to JPEG...");
      const jpegBytes = await this.encodeTextureToJpeg(imageFrame.texture, 0.7);
      print(`Encoded: ${jpegBytes.length} bytes`);
      
      const w = imageFrame.texture.getWidth();
      const h = imageFrame.texture.getHeight();
      
      const header = { t: 'image', ts: Date.now(), w, h, fmt: 'jpeg' };
      print(`Sending frame: ${w}x${h}`);
      this.sendFramed(header, jpegBytes);
      print("✅ Frame sent!");
      
    } catch (error) {
      print(`❌ Video error: ${error}`);
    } finally {
      this.isEncodingVideo = false;
    }
  }
  
  private async encodeTextureToJpeg(texture: Texture, quality: number): Promise<Uint8Array> {
    return new Promise((resolve, reject) => {
      Base64.encodeTextureAsync(
        texture,
        (base64: string) => {
          print(`Base64 encoded: ${base64.length} chars`);
          const jpegBytes = this.base64ToBytes(base64);
          resolve(jpegBytes);
        },
        () => {
          print("❌ Encoding failed!");
          reject(new Error("Failed to encode texture"));
        },
        CompressionQuality.LowQuality,
        quality
      );
    });
  }
  
  // ============================================
  // AUDIO PLAYBACK
  // ============================================
  
  private onInboundAudio(data: Uint8Array) {
    try {
      print(`Processing audio: ${data.length} bytes`);
      
      if (data.length < 4) {
        print("Audio data too short");
        return;
      }
      
      const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
      const headerLen =
        (view.getUint8(0) << 24) |
        (view.getUint8(1) << 16) |
        (view.getUint8(2) << 8) |
        view.getUint8(3);
      
      print(`Header length: ${headerLen}`);
      
      if (4 + headerLen > data.length) {
        print("Incomplete frame");
        return;
      }
      
      const headerBytes = new Uint8Array(data.buffer, data.byteOffset + 4, headerLen);
      const headerStr = new TextDecoder().decode(headerBytes);
      const header = JSON.parse(headerStr);
      
      print(`Header: ${JSON.stringify(header)}`);
      
      const payload = new Uint8Array(data.buffer, data.byteOffset + 4 + headerLen);
      
      if (header.t === 'audio') {
        print(`Playing audio: ${payload.length} bytes`);
        this.playPcm48kMono(payload);
      }
    } catch (e) {
      print(`❌ Error processing inbound audio: ${e}`);
    }
  }
  
  private playPcm48kMono(pcmInt16LE: Uint8Array) {
    print(`Converting ${pcmInt16LE.length} bytes of PCM audio`);
    // For now just log - actual playback TBD
  }
  
  // ============================================
  // WEBSOCKET FRAMING
  // ============================================
  
  private sendFramed(headerObj: any, payload: Uint8Array) {
    print(`📤 sendFramed called - connected: ${this.wsConnected}`);
    
    if (!this.wsConnected || !this.ws) {
      print("❌ WebSocket not ready!");
      return;
    }
    
    print(`Encoding header: ${JSON.stringify(headerObj)}`);
    const headerBytes = new TextEncoder().encode(JSON.stringify(headerObj));
    const headerLen = headerBytes.length;
    print(`Header: ${headerLen} bytes, Payload: ${payload.length} bytes`);
    
    const out = new Uint8Array(4 + headerLen + payload.length);
    
    // 4-byte big-endian header length
    out[0] = (headerLen >>> 24) & 0xff;
    out[1] = (headerLen >>> 16) & 0xff;
    out[2] = (headerLen >>> 8) & 0xff;
    out[3] = headerLen & 0xff;
    
    out.set(headerBytes, 4);
    out.set(payload, 4 + headerLen);
    
    print(`Total message: ${out.length} bytes`);
    
    try {
      print(`Sending to WebSocket (readyState: ${this.ws.readyState})...`);
      this.ws.send(out);
      print("✅ Sent to WebSocket!");
    } catch (e) {
      print(`❌ WebSocket send error: ${e}`);
    }
  }
  
  // ============================================
  // UTILITY FUNCTIONS
  // ============================================
  
  private base64ToBytes(base64: string): Uint8Array {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    const lookup = new Uint8Array(256);
    for (let i = 0; i < chars.length; i++) {
      lookup[chars.charCodeAt(i)] = i;
    }
    
    let paddingLength = 0;
    if (base64.endsWith('==')) paddingLength = 2;
    else if (base64.endsWith('=')) paddingLength = 1;
    
    const length = base64.length;
    const bufferLength = (length * 3) / 4 - paddingLength;
    const bytes = new Uint8Array(bufferLength);
    
    let p = 0;
    for (let i = 0; i < length; i += 4) {
      const encoded1 = lookup[base64.charCodeAt(i)];
      const encoded2 = lookup[base64.charCodeAt(i + 1)];
      const encoded3 = lookup[base64.charCodeAt(i + 2)];
      const encoded4 = lookup[base64.charCodeAt(i + 3)];
      
      bytes[p++] = (encoded1 << 2) | (encoded2 >> 4);
      if (p < bufferLength) bytes[p++] = ((encoded2 & 15) << 4) | (encoded3 >> 2);
      if (p < bufferLength) bytes[p++] = ((encoded3 & 3) << 6) | (encoded4 & 63);
    }
    
    return bytes;
  }
}