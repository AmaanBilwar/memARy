import asyncio
import json
import logging
import struct
from contextlib import suppress
from typing import Optional, Set

from livekit import rtc

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except Exception:  # pragma: no cover
    websockets = None  # type: ignore
    WebSocketServerProtocol = object  # type: ignore

try:
    from PIL import Image
    import io
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    io = None  # type: ignore

logger = logging.getLogger("ws_ingest")


class _ConnectionState:
    """Holds LiveKit track state for a single WS connection."""

    def __init__(self) -> None:
        self.audio_source: Optional[rtc.AudioSource] = None
        self.audio_track_pub: Optional[rtc.TrackPublication] = None
        self.sample_rate: int = 48000
        self.num_channels: int = 1

        self.video_source: Optional[rtc.VideoSource] = None
        self.video_track_pub: Optional[rtc.TrackPublication] = None
        self.width: Optional[int] = None
        self.height: Optional[int] = None


class WSIngestServer:
    """WebSocket server to accept multiplexed audio/image frames from Spectacles.

    Message framing (single socket for A/V):
    - 4-byte big-endian uint32 header_len
    - header_len bytes: UTF-8 JSON header
      { "t": "audio"|"image", "ts": <ms>, ... }
        audio: { "sr": 48000, "ch": 1, "spp": 960 }
        image: { "w": <int>, "h": <int>, "fmt": "jpeg" }
    - payload bytes: PCM s16le for audio, JPEG bytes for image
    """

    def __init__(self, room: rtc.Room) -> None:
        self._room = room
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: Set[WebSocketServerProtocol] = set()
        self._lock = asyncio.Lock()

    async def start(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        if websockets is None:
            logger.error("websockets not installed; cannot start WS server")
            return

        async def _handler(ws: WebSocketServerProtocol):
            conn = _ConnectionState()
            self._clients.add(ws)
            try:
                await self._handle_connection(ws, conn)
            except Exception as e:  # pragma: no cover
                logger.exception("WS connection error: %s", e)
            finally:
                self._clients.discard(ws)
                await self._teardown(conn)

        self._server = await websockets.serve(_handler, host, port, max_size=None)
        logger.info("WS ingest server listening on %s:%d", host, port)

    async def aclose(self) -> None:
        if self._server:
            self._server.close()
            with suppress(Exception):
                await self._server.wait_closed()
            self._server = None

    async def _handle_connection(self, ws: WebSocketServerProtocol, conn: _ConnectionState) -> None:
        while True:
            raw = await ws.recv()  # bytes
            if not isinstance(raw, (bytes, bytearray)):
                continue
            parsed = parse_framed_message(bytes(raw))
            if parsed is None:
                continue
            header, payload = parsed

            t = header.get("t")
            if t == "audio":
                await self._handle_audio(payload, header, conn)
            elif t == "image":
                await self._handle_image(payload, header, conn)
            else:
                logger.debug("Unknown frame type: %s", t)

    async def _ensure_audio_track(self, conn: _ConnectionState) -> None:
        if conn.audio_source is not None:
            return
        conn.audio_source = rtc.AudioSource(conn.sample_rate, conn.num_channels)
        track = rtc.LocalAudioTrack.create_audio_track("glasses-mic", conn.audio_source)
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        conn.audio_track_pub = await self._room.local_participant.publish_track(track, options)
        logger.info("Published audio track from WS connection")

    async def _handle_audio(self, payload: bytes, header: dict, conn: _ConnectionState) -> None:
        conn.sample_rate = int(header.get("sr", 48000))
        conn.num_channels = int(header.get("ch", 1))
        samples_per_channel = int(header.get("spp", 960))
        await self._ensure_audio_track(conn)
        assert conn.audio_source is not None

        frame = rtc.AudioFrame.create(conn.sample_rate, conn.num_channels, samples_per_channel)
        mv = memoryview(frame.data)
        if len(payload) != len(mv):
            # Expected exact PCM frame size (int16)
            if len(payload) * 2 == len(mv):
                # If payload is int16 array length not bytes (unlikely), adjust
                pcm_bytes = payload
            else:
                logger.debug("Dropping mismatched audio payload size: %d != %d", len(payload), len(mv))
                return
        mv[:] = payload
        await conn.audio_source.capture_frame(frame)

    async def _ensure_video_track(self, width: int, height: int, conn: _ConnectionState) -> None:
        if conn.video_source is not None:
            return
        conn.width = width
        conn.height = height
        conn.video_source = rtc.VideoSource(width, height)
        track = rtc.LocalVideoTrack.create_video_track("glasses-cam", conn.video_source)
        options = rtc.TrackPublishOptions(
            source=rtc.TrackSource.SOURCE_CAMERA,
            simulcast=True,
            video_encoding=rtc.VideoEncoding(max_framerate=30, max_bitrate=3_000_000),
            video_codec=rtc.VideoCodec.H264,
        )
        conn.video_track_pub = await self._room.local_participant.publish_track(track, options)
        logger.info("Published video track from WS connection %dx%d", width, height)

    async def _handle_image(self, payload: bytes, header: dict, conn: _ConnectionState) -> None:
        if Image is None or io is None:
            logger.error("Pillow not installed; cannot decode JPEG frames")
            return
        width = int(header.get("w", 0))
        height = int(header.get("h", 0))
        await self._ensure_video_track(width, height, conn)
        assert conn.video_source is not None

        try:
            img = Image.open(io.BytesIO(payload)).convert("RGBA")
            w, h = img.size
            rgba = img.tobytes()
            frame = rtc.VideoFrame(w, h, rtc.VideoBufferType.RGBA, rgba)
            conn.video_source.capture_frame(frame)
        except Exception as e:
            logger.debug("Failed to decode image: %s", e)

    async def broadcast_tts_frame(self, frame: rtc.AudioFrame) -> None:
        if not self._clients:
            return
        header = {
            "t": "audio",
            "ts": 0,
            "sr": frame.sample_rate,
            "ch": frame.num_channels,
            "spp": frame.samples_per_channel,
        }
        header_bytes = json.dumps(header).encode("utf-8")
        prefix = struct.pack(">I", len(header_bytes))
        blob = prefix + header_bytes + bytes(frame.data)
        await asyncio.gather(
            *(self._safe_send(ws, blob) for ws in list(self._clients)), return_exceptions=True
        )

    async def _safe_send(self, ws: WebSocketServerProtocol, data: bytes) -> None:
        with suppress(Exception):
            await ws.send(data)


_server_singleton: Optional[WSIngestServer] = None


async def start(room: rtc.Room, host: str = "0.0.0.0", port: int = 8765) -> None:
    global _server_singleton
    if _server_singleton is not None:
        return
    srv = WSIngestServer(room)
    await srv.start(host=host, port=port)
    _server_singleton = srv


async def aclose() -> None:
    global _server_singleton
    if _server_singleton is None:
        return
    await _server_singleton.aclose()
    _server_singleton = None


async def broadcast_tts_frame(frame: rtc.AudioFrame) -> None:
    if _server_singleton is not None:
        await _server_singleton.broadcast_tts_frame(frame)


def parse_framed_message(raw: bytes) -> Optional[tuple[dict, bytes]]:
    """Parse a framed WS message into (header dict, payload bytes).

    Returns None if invalid.
    """
    if len(raw) < 4:
        return None
    (header_len,) = struct.unpack(">I", raw[:4])
    if 4 + header_len > len(raw):
        return None
    header_bytes = raw[4 : 4 + header_len]
    payload = raw[4 + header_len :]
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(header, dict):
        return None
    return header, payload

