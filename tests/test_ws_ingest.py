import json
import struct

from ws_ingest import parse_framed_message


def _frame_msg(header: dict, payload: bytes) -> bytes:
    hb = json.dumps(header).encode("utf-8")
    return struct.pack(">I", len(hb)) + hb + payload


def test_parse_framed_message_audio_ok():
    header = {"t": "audio", "sr": 48000, "ch": 1, "spp": 960, "ts": 1}
    payload = b"\x00\x00" * 960  # 960 samples mono int16
    raw = _frame_msg(header, payload)
    parsed = parse_framed_message(raw)
    assert parsed is not None
    h, p = parsed
    assert h["t"] == "audio"
    assert p == payload


def test_parse_framed_message_image_ok():
    header = {"t": "image", "w": 640, "h": 480, "fmt": "jpeg", "ts": 1}
    payload = b"\xff\xd8\xff\xd9"  # minimal bogus jpeg markers
    raw = _frame_msg(header, payload)
    parsed = parse_framed_message(raw)
    assert parsed is not None
    h, p = parsed
    assert h["t"] == "image"
    assert p == payload


def test_parse_framed_message_invalid_short():
    assert parse_framed_message(b"\x00\x00\x00") is None


