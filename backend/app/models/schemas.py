from typing import Any, Literal
from pydantic import BaseModel, Field

class TrackingMessage(BaseModel):
    type: Literal['frame'] = 'frame'
    timestamp: float
    captured_at: float
    session_id: str
    frame_id: int
    source_frame: int
    source_time: float
    width: int
    height: int
    fps: float
    inference_ms: float
    tracker_ms: float
    pipeline_ms: float
    demo: bool
    model: str
    targets: list[dict[str, Any]]
    raw_detections: list[list[float]] = Field(default_factory=list)
    stats: dict[str, Any]
    events: list[dict[str, Any]]

class EvaluationReport(BaseModel):
    schema_version: Literal[1]=1
    model: str
    dataset: str
    split: Literal['val','test']
    precision: float = Field(ge=0,le=1)
    recall: float = Field(ge=0,le=1)
    map50: float = Field(ge=0,le=1)
    map50_95: float = Field(ge=0,le=1)
