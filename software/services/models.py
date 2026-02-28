from pydantic import BaseModel
from typing import Literal, Optional

class RunSceneRequest(BaseModel):
    scene: Literal["A", "B"]
    style: Literal["polite", "meme"] = "polite"
    safe: bool = True
    # Optional: pass pre-identified label + confidence from frontend capture_frame
    # so orchestrator skips its internal recognize step
    recognized_label: Optional[str] = None
    recognized_conf: Optional[float] = None

class RecognizeOut(BaseModel):
    label: str
    confidence: float

class RunSceneResponse(BaseModel):
    ok: bool
    scene: Literal["A", "B"]
    duration_ms: int
    error_code: Optional[str] = None
    recognized: Optional[RecognizeOut] = None
    recognition_ok: Optional[bool] = None  # 与 Status/CaptureFrame 一致

# 与前端 CONF_DISPLAY_SUCCESS 一致，仅当置信度 >= 此值视为「识别成功」
RECOGNITION_SUCCESS_THRESHOLD = 0.0   # 有识别结果即视为成功，不设置置信度门槛

class StatusResponse(BaseModel):
    busy: bool
    last_scene: Optional[str] = None
    last_error: Optional[str] = None
    recognized: Optional[RecognizeOut] = None
    recognition_ok: Optional[bool] = None  # 置信度 >= threshold 时为 True，供 UI 显示「识别成功」
    trigger_pending: bool = False           # 外部触发开牌信号，前端读取后清零
    activate_pending: bool = False          # 远程激活前端摄像头+AutoLoop，前端读取后清零
    logs: list[str]

class CaptureFrameRequest(BaseModel):
    image: str  # base64 JPEG

class CaptureFrameResponse(BaseModel):
    ok: bool
    recognized: Optional[RecognizeOut] = None
    recognition_ok: Optional[bool] = None  # 置信度 >= RECOGNITION_SUCCESS_THRESHOLD 时为 True
    error: Optional[str] = None

class VoiceTriggerRequest(BaseModel):
    text: str

class VoiceTriggerResponse(BaseModel):
    ok: bool
    action: Optional[str] = None
    reply: str

# Brain callbacks (OpenClaw EC2 → Mac)
class BrainInputRequest(BaseModel):
    session_id: str
    label: str
    confidence: float
    frame_id: Optional[str] = None

class BrainDecisionRequest(BaseModel):
    session_id: str
    action: Literal["throw", "return"]
    line_key: str          # e.g. "LOOK_DONE", "I_WANT_CHECK"
    ui_text: str           # display text for Web UI
    sfx: Optional[str] = None

class SessionStartResponse(BaseModel):
    session_id: str
    ok: bool

class AutoRunRequest(BaseModel):
    style: Literal["polite", "meme"] = "polite"
    safe: bool = True

class AutoRunResponse(BaseModel):
    ok: bool
    scene: Optional[Literal["A", "B"]] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    duration_ms: int
    error_code: Optional[str] = None
