"""
Pydantic schemas for request validation with devil's-advocate safeguards
"""
from pydantic import BaseModel, Field
from typing import Optional
import os

# Safeguard: Hallucination guard - confidence threshold & whitelist
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.8"))
TRACKED_OBJECTS = {
    "keys", "wallet", "phone", "glasses", "mug", "bottle",
    "pill_bottle", "pills", "medication", "tablet_box"
}

# --- Request Models ---

class DetectedObject(BaseModel):
    """Object detected in a frame"""
    label: str
    confidence: float = Field(ge=0, le=1)
    bbox: Optional[list[float]] = None  # [x, y, w, h]
    color: Optional[str] = None
    rel_pos: Optional[str] = None  # relative position description
    relationship_hint: Optional[str] = None  # for people only (privacy safeguard)
    is_person: bool = False

class FrameIngestRequest(BaseModel):
    """
    Ingest a frame captured every ~5 seconds.
    LLM has already converted vision → text summary + structured objects.
    """
    tenant_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    frame_ts: int = Field(ge=0)  # unix timestamp
    tz: Optional[str] = None
    lat_lon_hash: Optional[str] = None  # geohash for privacy
    scene_summary: str = Field(min_length=1)  # LLM text summary
    objects: list[DetectedObject] = Field(default_factory=list)

class NoteIngestRequest(BaseModel):
    """User-provided note (voice or typed 'remember this')"""
    tenant_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    modality: str = Field(default="typed", pattern="^(voice|typed)$")
    priority: str = Field(default="med", pattern="^(low|med|high)$")
    tags: list[str] = Field(default_factory=list)
    linked_entity: Optional[str] = None  # e.g., "keys@home"

class SearchLastSeenRequest(BaseModel):
    """Search for last-seen location of an object"""
    tenant_id: str = Field(min_length=1)
    canonical_key: str = Field(min_length=1)  # e.g., "keys@home"

class SearchSemanticRequest(BaseModel):
    """Semantic search across collections"""
    tenant_id: str = Field(min_length=1)
    query_text: str = Field(min_length=1)
    collections: list[str] = Field(default_factory=lambda: ["entities_stream_v1", "user_notes_v1"])
    n_results: int = Field(default=5, ge=1, le=100)

class SearchTimeWindowRequest(BaseModel):
    """Search frames in a time window"""
    tenant_id: str = Field(min_length=1)
    start_ts: int = Field(ge=0)
    end_ts: int = Field(ge=0)
    n_results: int = Field(default=10, ge=1, le=100)

class CurateToLTMRequest(BaseModel):
    """
    User curates what to keep after session.
    This is the key to cost control - only persist what matters.
    """
    tenant_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    items: list[dict] = Field(default_factory=list)  # [{origin, origin_id, text}]
    tags: list[str] = Field(default_factory=list)

class CompactRequest(BaseModel):
    """TTL enforcement - remove old ephemeral data"""
    tenant_id: str = Field(min_length=1)
    ttl_hours: int = Field(default=72, gt=0)
