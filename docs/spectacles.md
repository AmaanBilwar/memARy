# Snap Spectacles → LiveKit WebSocket spec

This doc is a handoff for implementing Spectacles streaming to our backend over a single WebSocket. The backend publishes incoming audio/video to LiveKit and sends the agent's speech back over the same socket.

## Endpoint

- Dev: `ws://<agent-host>:8765`
- Prod: `wss://<agent-host>:8765`

No special handshake is required; you can begin sending framed binary messages once connected.

## Message framing (single socket for images + audio)

Each binary WebSocket message = header + payload:

1) 4-byte big-endian uint32: `header_len`
2) `header_len` bytes: UTF-8 JSON header
   - Image header: `{ "t": "image", "ts": <ms>, "w": <int>, "h": <int>, "fmt": "jpeg" }`
   - Audio header: `{ "t": "audio", "ts": <ms>, "sr": 48000, "ch": 1, "spp": 960 }`
3) payload bytes
   - Image payload: JPEG bytes
   - Audio payload: PCM s16le (little-endian int16) 48 kHz mono, exactly 960 samples per frame (20 ms)

Guidance:
- Keep audio cadence near 20 ms. The server buffers ~50 ms but expects steady frames.
- Send camera frames around 10–15 FPS. Use smallerDimension ≈ 640 for reasonable bandwidth.
- `ts` can be device time in ms; strict A/V sync is not required by the server.

## Back-channel (agent → glasses)

The server will send binary messages back using the same framing for `t: "audio"`:
- Header: `{ "t": "audio", "ts": <ms>, "sr": 48000, "ch": 1, "spp": 960 }`
- Payload: PCM s16le 48 kHz mono (20 ms). Play out continuously to the device speaker.

## Lens Studio sketch (pseudocode)

This shows the exact framing and flow. Replace the three helper functions with Spectacles/Lens APIs:

```typescript
// PSEUDOCODE — adapt to actual Lens Studio/Spectacles APIs
//@component
export class WsAviStreamer extends BaseScriptComponent {
  private cameraModule = require('LensStudio:CameraModule');
  private ws: WebSocket | null = null;

  onAwake() {
    this.createEvent('OnStartEvent').bind(this.start);
    this.createEvent('OnDestroyEvent').bind(this.stop);
  }

  private async start() {
    // 1) Open WS
    this.ws = new WebSocket('wss://your-agent-host:8765');
    this.ws.binaryType = 'arraybuffer';
    this.ws.onmessage = (ev) => this.onInboundAudio(ev.data);

    // 2) Camera frames
    const req = this.cameraModule.createCameraRequest();
    req.cameraId = this.cameraModule.CameraId.Default_Color;
    const cameraTex = this.cameraModule.requestCamera(req);
    const provider = cameraTex.control; // CameraTextureProvider
    provider.onNewFrame.add(async () => {
      // Convert Texture -> JPEG bytes (Uint8Array)
      const jpegBytes = await this.encodeTextureToJpeg(cameraTex, /*quality=*/0.7);
      const w = cameraTex.getWidth ? cameraTex.getWidth() : 640;
      const h = cameraTex.getHeight ? cameraTex.getHeight() : 480;

      const header = { t: 'image', ts: Date.now(), w, h, fmt: 'jpeg' };
      this.sendFramed(header, jpegBytes);
    });

    // 3) Microphone frames (20 ms PCM s16le @ 48k mono)
    // Capture 960-sample int16 LE buffers and send every 20 ms
    this.startMicCapture((pcmInt16LE /* Uint8Array length=1920 */) => {
      const header = { t: 'audio', ts: Date.now(), sr: 48000, ch: 1, spp: 960 };
      this.sendFramed(header, pcmInt16LE);
    });
  }

  private stop() {
    try { this.ws?.close(); } catch(_) {}
    this.ws = null;
  }

  private sendFramed(headerObj: any, payload: Uint8Array) {
    if (!this.ws || this.ws.readyState !== this.ws.OPEN) return;
    const headerBytes = new TextEncoder().encode(JSON.stringify(headerObj));
    const headerLen = headerBytes.length;
    const out = new Uint8Array(4 + headerLen + payload.length);
    // 4-byte big-endian header length
    out[0] = (headerLen >>> 24) & 0xff;
    out[1] = (headerLen >>> 16) & 0xff;
    out[2] = (headerLen >>> 8) & 0xff;
    out[3] = headerLen & 0xff;
    out.set(headerBytes, 4);
    out.set(payload, 4 + headerLen);
    this.ws.send(out.buffer);
  }

  private onInboundAudio(data: ArrayBuffer) {
    // Decode framed message and if header.t === 'audio', play PCM 48k mono
    const view = new DataView(data);
    if (view.byteLength < 4) return;
    const headerLen =
      (view.getUint8(0) << 24) |
      (view.getUint8(1) << 16) |
      (view.getUint8(2) << 8) |
      view.getUint8(3);
    if (4 + headerLen > view.byteLength) return;

    const headerBytes = new Uint8Array(data, 4, headerLen);
    const header = JSON.parse(new TextDecoder().decode(headerBytes));
    const payload = new Uint8Array(data, 4 + headerLen);

    if (header.t === 'audio') {
      this.playPcm48kMono(payload);
    }
  }

  // Implement with Spectacles/Lens APIs
  private async encodeTextureToJpeg(_texture: any, _quality: number): Promise<Uint8Array> {
    throw new Error('encodeTextureToJpeg not implemented');
  }
  private startMicCapture(_onFrame: (pcmInt16LE: Uint8Array) => void) {
    throw new Error('startMicCapture not implemented');
  }
  private playPcm48kMono(_pcmInt16LE: Uint8Array) {
    throw new Error('playPcm48kMono not implemented');
  }
}
```

## Checklist for Spectacles implementation

- Enable Extended Permissions to use camera frames and open internet together.
- Connect to `ws(s)://<agent-host>:8765`.
- Send images as JPEG with `w`, `h`, `fmt: "jpeg"` in header; ~10–15 FPS.
- Send audio as PCM s16le 48 kHz mono, 960 samples (20 ms) per message.
- Keep 20 ms audio cadence steady.
- Play back inbound `t: "audio"` frames (PCM 48k mono) continuously.

## References

- Snap Camera Module (Extended Permissions requirement):
  - `https://developers.snap.com/spectacles/about-spectacles-features/apis/camera-module`
- LiveKit publishing audio/video:
  - `https://docs.livekit.io/home/client/tracks/publish`
  - `https://docs.livekit.io/home/client/tracks/raw-tracks`
- LLM vision overview:
  - `https://docs.livekit.io/agents/models/llm`
