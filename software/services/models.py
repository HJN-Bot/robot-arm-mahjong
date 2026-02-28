from pydantic import BaseModel
from typing import Literal, Optional

class RunSceneRequest(BaseModel):
    scene: Literal["A", "B"]
    style: Literal["polite", "meme"] = "polite"
    safe: bool = True

class RecognizeOut(BaseModel):
    label: str
    confidence: float

class RunSceneResponse(BaseModel):
    ok: bool
    scene: Literal["A", "B"]
    duration_ms: int
    error_code: Optional[str] = None
    recognized: Optional[RecognizeOut] = None

class StatusResponse(BaseModel):
    busy: bool
    last_scene: Optional[str] = None
    last_error: Optional[str] = None
    recognized: Optional[RecognizeOut] = None
    logs: list[str]

class CaptureFrameRequest(BaseModel):
    image: str  # base64 JPEG

class CaptureFrameResponse(BaseModel):
    ok: bool
    recognized: Optional[RecognizeOut] = None
    error: Optional[str] = None

class VoiceTriggerRequest(BaseModel):
    text: str

class VoiceTriggerResponse(BaseModel):
    ok: bool
    action: Optional[str] = None
    reply: str
