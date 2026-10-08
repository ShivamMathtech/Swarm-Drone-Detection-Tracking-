from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "runtime"
DATA.mkdir(exist_ok=True)
(DATA / "uploads").mkdir(exist_ok=True)

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    model_path: str = "weights/drone_detector.pt"
    confidence_threshold: float = Field(.40, ge=.05, le=.99)
    iou_threshold: float = Field(.50, ge=.1, le=.95)
    image_size: int = Field(1280, ge=320, le=1920)
    device: str = "cpu"
    tracker: Literal["bytetrack", "botsort"] = "bytetrack"
    track_buffer: int = Field(30, ge=1, le=300)
    match_threshold: float = Field(.8, ge=.1, le=.99)
    target_fps: int = Field(30, ge=1, le=60)
    frame_skip: int = Field(0, ge=0, le=10)
    max_frame_width: int = Field(1280, ge=320, le=1920)
    jpeg_quality: int = Field(80, ge=40, le=95)
    trajectory_length: int = Field(50, ge=2, le=300)
    line_thickness: float = Field(1, ge=.5, le=4)
    fade_points: bool = True
    show_boxes: bool = True
    show_ids: bool = True
    show_confidence: bool = True
    show_trajectory: bool = True
    show_crosshair: bool = True
    show_seeker: bool = True
    zoom: Literal[2, 3, 4] = 3
    debug: bool = False
    research_mode: bool = True
    @field_validator("image_size")
    @classmethod
    def divisible(cls, v):
        if v % 32: raise ValueError("Image size must be divisible by 32")
        return v
    @field_validator("device")
    @classmethod
    def valid_device(cls, v):
        if v != "cpu" and not v.isdigit():
            raise ValueError("Use cpu or a CUDA device index such as 0")
        return v

class StartRequest(BaseModel):
    source: Literal["demo", "webcam", "video", "rtsp"] = "demo"
    camera_index: int = Field(0, ge=0, le=10)
    upload_id: str | None = None
    rtsp_alias: str = "CAM_RTSP_URL"
