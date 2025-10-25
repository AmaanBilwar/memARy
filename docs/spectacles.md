# Snap Spectacles streaming via WebSocket

This project supports streaming camera frames and microphone audio from Snap Spectacles to the agent over a single WebSocket. Frames are published to LiveKit from the backend, and agent speech is sent back over the same socket as PCM.

Framing (single socket for A/V):
- 4-byte big-endian uint32 `header_len`
- `header_len` bytes of UTF-8 JSON header: `{ "t": "audio"|"image", "ts": <ms>, ... }`
  - Audio: `{ "sr": 48000, "ch": 1, "spp": 960 }` and payload is PCM s16le
  - Image: `{ "w": <int>, "h": <int>, "fmt": "jpeg" }` and payload is JPEG bytes

Spectacles permissions
- Accessing camera frames disables open internet by default. For development and testing, request Extended Permissions to use the camera frame API and WebSocket networking together.
- See Snap docs: https://developers.snap.com/spectacles/about-spectacles-features/apis/camera-module

LiveKit references
- Publishing audio/video from Python: https://docs.livekit.io/home/client/tracks/publish
- Processing raw tracks: https://docs.livekit.io/home/client/tracks/raw-tracks
- LLM vision overview: https://docs.livekit.io/agents/models/llm
