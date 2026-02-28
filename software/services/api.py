import base64
import re
import uuid
from fastapi import FastAPI
from software.services.models import (
    RunSceneRequest, RunSceneResponse, StatusResponse, RecognizeOut,
    CaptureFrameRequest, CaptureFrameResponse,
    VoiceTriggerRequest, VoiceTriggerResponse,
    BrainInputRequest, BrainDecisionRequest, SessionStartResponse,
)
from software.services.status_store import StatusStore
from software.orchestrator.contracts import RunRequest
from software.orchestrator.state_machine import Orchestrator
from software.adapters.arm.mock_arm import MockArm
from software.adapters.vision.mock_vision import MockVision
from software.adapters.tts.player_local import LocalPlayerTTS

app = FastAPI(title="robot-arm-mahjong software")

status = StatusStore()
arm = MockArm(status)
vision = MockVision(status)
tts = LocalPlayerTTS(status)
orch = Orchestrator(arm=arm, vision=vision, tts=tts, status_store=status)

@app.get("/status", response_model=StatusResponse)
def get_status():
    rec = status.last_recognized
    rec_out = RecognizeOut(label=rec.label, confidence=rec.confidence) if rec else None
    return StatusResponse(
        busy=status.busy,
        last_scene=status.last_scene,
        last_error=status.last_error,
        recognized=rec_out,
        logs=status.logs,
    )

@app.post("/run_scene", response_model=RunSceneResponse)
def run_scene(req: RunSceneRequest):
    status.last_scene = req.scene
    rr = orch.run_scene(RunRequest(scene=req.scene, style=req.style, safe=req.safe))
    rec = rr.recognized
    rec_out = RecognizeOut(label=rec.label, confidence=rec.confidence) if rec else None
    return RunSceneResponse(ok=rr.ok, scene=rr.scene, duration_ms=rr.duration_ms, error_code=rr.error_code, recognized=rec_out)

@app.post("/estop")
def estop():
    status.log("ESTOP")
    try:
        arm.estop()
    except Exception:
        pass
    return {"ok": True}

@app.post("/stop")
def stop():
    status.log("STOP")
    return {"ok": True}

@app.post("/home")
def home():
    status.log("HOME")
    try:
        arm.home()
    except Exception:
        pass
    return {"ok": True}

@app.post("/tap")
def tap():
    status.log("TAP3")
    if hasattr(arm, "tap"):
        arm.tap(times=3)
    return {"ok": True}

@app.post("/nod")
def nod():
    status.log("NOD")
    if hasattr(arm, "nod"):
        arm.nod()
    return {"ok": True}

@app.post("/shake")
def shake():
    status.log("SHAKE")
    if hasattr(arm, "shake"):
        arm.shake()
    return {"ok": True}


@app.post("/capture_frame", response_model=CaptureFrameResponse)
def capture_frame(req: CaptureFrameRequest):
    """接收前端截帧（base64 JPEG），交给视觉适配器识别牌面。"""
    try:
        image_bytes = base64.b64decode(req.image)
    except Exception as e:
        status.log(f"CAPTURE_FRAME decode error: {e}")
        return CaptureFrameResponse(ok=False, error="base64 decode failed")

    status.log("CAPTURE_FRAME received")
    try:
        result = vision.identify(image_bytes)
        rec_out = RecognizeOut(label=result.label, confidence=result.confidence)
        status.last_recognized = result
        status.log(f"CAPTURE_FRAME result: {result.label} ({result.confidence:.2f})")
        return CaptureFrameResponse(ok=True, recognized=rec_out)
    except Exception as e:
        status.log(f"CAPTURE_FRAME vision error: {e}")
        return CaptureFrameResponse(ok=False, error=str(e))


# Simple keyword rules for voice commands
_VOICE_RULES = [
    (r"场景\s*[Aa]|scene\s*[Aa]|[Aa]\s*场景", "scene_a", "好，执行场景 A！"),
    (r"场景\s*[Bb]|scene\s*[Bb]|[Bb]\s*场景", "scene_b", "好，执行场景 B！"),
    (r"点三点|tap",                             "tap",     "好，点三点！"),
    (r"点头|nod|没问题",                         "nod",     "点头 ✅"),
    (r"摇头|shake|不行",                         "shake",   "摇头 ❌"),
    (r"回零|回家|home",                           "home",    "回零位！"),
    (r"急停|estop|停止",                          "estop",   "紧急停止！"),
]

@app.post("/voice_trigger", response_model=VoiceTriggerResponse)
def voice_trigger(req: VoiceTriggerRequest):
    """解析语音文本，触发对应动作。"""
    text = req.text.strip()
    status.log(f"VOICE: {text}")

    for pattern, action, reply in _VOICE_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            status.log(f"VOICE matched: {action}")
            # Fire-and-forget style: trigger action via existing endpoints logic
            if action == "scene_a":
                orch.run_scene(RunRequest(scene="A", style="polite", safe=True))
            elif action == "scene_b":
                orch.run_scene(RunRequest(scene="B", style="polite", safe=True))
            elif action == "tap" and hasattr(arm, "tap"):
                arm.tap(times=3)
            elif action == "nod" and hasattr(arm, "nod"):
                arm.nod()
            elif action == "shake" and hasattr(arm, "shake"):
                arm.shake()
            elif action == "home":
                arm.home()
            elif action == "estop":
                arm.estop()
            return VoiceTriggerResponse(ok=True, action=action, reply=reply)

    return VoiceTriggerResponse(ok=True, action=None, reply="听到了，但不确定要做什么 🤔")


# ===== Brain Callbacks (OpenClaw EC2 → Mac) =====

@app.post("/session/start", response_model=SessionStartResponse)
def session_start():
    """Brain 发起新对局，Mac 返回 session_id。"""
    sid = str(uuid.uuid4())[:8]
    status.log(f"SESSION_START: {sid}")
    return SessionStartResponse(session_id=sid, ok=True)


@app.post("/brain/input")
def brain_input(req: BrainInputRequest):
    """Brain 把 Mac 的识别结果接收回去（供 Brain 记忆/决策）。

    实际上 Mac 在 capture_frame 里已经识别，这个端点给 Brain 推送确认。
    Brain 拿到后自己决策，再通过 /brain/decision 回调 Mac。
    """
    status.log(f"BRAIN_INPUT: session={req.session_id} label={req.label} conf={req.confidence:.2f}")
    return {"ok": True, "session_id": req.session_id}


@app.post("/brain/decision")
def brain_decision(req: BrainDecisionRequest):
    """Brain 的决策结果推回 Mac，Mac 执行动作 + TTS。"""
    status.log(f"BRAIN_DECISION: session={req.session_id} action={req.action} line={req.line_key}")

    scene = "A" if req.action == "throw" else "B"
    rr = orch.run_scene(RunRequest(scene=scene, style="polite", safe=True))

    # TTS：播放 line_key 对应台词，如果没有则说 ui_text
    try:
        tts.say(req.line_key)
    except Exception:
        tts.say_text(req.ui_text)

    return {
        "ok": rr.ok,
        "session_id": req.session_id,
        "action": req.action,
        "error_code": rr.error_code,
    }
