import base64
import os
import re
import uuid
from fastapi import FastAPI
from dotenv import load_dotenv
from software.services.models import (
    RunSceneRequest, RunSceneResponse, StatusResponse, RecognizeOut,
    CaptureFrameRequest, CaptureFrameResponse,
    RECOGNITION_SUCCESS_THRESHOLD,
    VoiceTriggerRequest, VoiceTriggerResponse,
    BrainInputRequest, BrainDecisionRequest, SessionStartResponse,
    AutoRunRequest, AutoRunResponse,
)
from software.services.status_store import StatusStore
from software.orchestrator.contracts import RunRequest, RecognizeResult
from software.orchestrator.state_machine import Orchestrator
from software.adapters.arm.mock_arm import MockArm
from software.adapters.arm.http_arm import HttpArm
from software.adapters.tts.player_local import LocalPlayerTTS

load_dotenv(dotenv_path="software/.env", override=False)

app = FastAPI(title="robot-arm-mahjong software")

status = StatusStore()

# Arm adapter: read from ARM_ADAPTER env var (default: mock)
arm_adapter = os.getenv("ARM_ADAPTER", "mock")
if arm_adapter == "http":
    arm_url = os.getenv("ARM_HTTP_BASE_URL", "http://127.0.0.1:9000")
    arm = HttpArm(status, base_url=arm_url)
    status.log(f"arm adapter: http -> {arm_url}")
else:
    arm = MockArm(status)
    status.log("arm adapter: mock")

# Vision adapter: controlled by VISION_ADAPTER env var
# Values: kimi | claude | histogram | mock  (default: kimi)
_vision_adapter = os.getenv("VISION_ADAPTER", "kimi").lower()

if _vision_adapter == "kimi":
    from software.adapters.vision.kimi_vision import KimiVision
    vision = KimiVision(status)
    if not vision._ready:
        status.log("vision: KimiVision not ready, falling back to histogram")
        try:
            from software.adapters.vision.histogram_vision import HistogramVision
            vision = HistogramVision(status)
        except ImportError:
            from software.adapters.vision.mock_vision import MockVision
            vision = MockVision(status)

elif _vision_adapter == "claude":
    from software.adapters.vision.claude_vision import ClaudeVision
    vision = ClaudeVision(status)
    if not vision._ready:
        status.log("vision: ClaudeVision not ready, falling back to histogram")
        try:
            from software.adapters.vision.histogram_vision import HistogramVision
            vision = HistogramVision(status)
        except ImportError:
            from software.adapters.vision.mock_vision import MockVision
            vision = MockVision(status)

elif _vision_adapter == "histogram":
    try:
        from software.adapters.vision.histogram_vision import HistogramVision
        vision = HistogramVision(status)
    except ImportError:
        from software.adapters.vision.mock_vision import MockVision
        vision = MockVision(status)

else:
    from software.adapters.vision.mock_vision import MockVision
    vision = MockVision(status)

status.log(f"vision adapter: {type(vision).__name__}")

tts = LocalPlayerTTS(status)

# Camera: try CV2Camera, fall back to MockCamera
try:
    from software.adapters.camera.cv2_camera import CV2Camera
    camera = CV2Camera(status)
    status.log("camera: CV2Camera ready")
except ImportError:
    from software.adapters.camera.mock_camera import MockCamera
    camera = MockCamera(status)
    status.log("camera: MockCamera (opencv not installed)")

orch = Orchestrator(arm=arm, vision=vision, tts=tts, status_store=status, camera=camera)

@app.get("/status", response_model=StatusResponse)
def get_status():
    rec = status.last_recognized
    rec_out = RecognizeOut(label=rec.label, confidence=rec.confidence) if rec else None
    recognition_ok = (rec.confidence >= RECOGNITION_SUCCESS_THRESHOLD) if rec else None
    # Read-and-clear: frontend consumes flags in one poll cycle
    trigger  = status.trigger_pending
    activate = status.activate_pending
    if trigger:  status.trigger_pending  = False
    if activate: status.activate_pending = False
    return StatusResponse(
        busy=status.busy,
        last_scene=status.last_scene,
        last_error=status.last_error,
        recognized=rec_out,
        recognition_ok=recognition_ok,
        trigger_pending=trigger,
        activate_pending=activate,
        logs=status.logs,
    )

@app.post("/run_scene", response_model=RunSceneResponse)
def run_scene(req: RunSceneRequest):
    status.last_scene = req.scene
    # Use pre-identified result from frontend if provided (avoids double recognition)
    pre = None
    if req.recognized_label:
        pre = RecognizeResult(label=req.recognized_label, confidence=req.recognized_conf or 0.0)
    rr = orch.run_scene(RunRequest(scene=req.scene, style=req.style, safe=req.safe, pre_recognized=pre))
    rec = rr.recognized
    rec_out = RecognizeOut(label=rec.label, confidence=rec.confidence) if rec else None
    rec_ok = (rec.confidence >= RECOGNITION_SUCCESS_THRESHOLD) if rec else None
    return RunSceneResponse(ok=rr.ok, scene=rr.scene, duration_ms=rr.duration_ms, error_code=rr.error_code, recognized=rec_out, recognition_ok=rec_ok)

@app.post("/arm/start_scene")
def arm_start_scene(style: str = "polite", safe: bool = True):
    """Step 1 of split flow: TTS(来！开牌) → pick → present.
    Blocks until arm is stable with tile in front of camera.
    Frontend should then capture a frame and call /execute_scene.
    """
    return orch.prepare_scene(style=style, safe=safe)


@app.post("/execute_scene", response_model=RunSceneResponse)
def execute_scene(req: RunSceneRequest):
    """Step 2 of split flow: arm action + closing TTS, with pre-identified tile.
    Expects recognized_label (and optionally recognized_conf) to determine scene.
    """
    if not req.recognized_label:
        from software.services.models import RunSceneResponse as R
        return R(ok=False, scene=req.scene, duration_ms=0, error_code="NO_RECOGNIZED_LABEL")
    recognized = RecognizeResult(label=req.recognized_label, confidence=req.recognized_conf or 0.0)
    rr = orch.execute_scene(scene=req.scene, style=req.style, safe=req.safe, recognized=recognized)
    rec = rr.recognized
    rec_out = RecognizeOut(label=rec.label, confidence=rec.confidence) if rec else None
    rec_ok = (rec.confidence >= RECOGNITION_SUCCESS_THRESHOLD) if rec else None
    return RunSceneResponse(ok=rr.ok, scene=rr.scene, duration_ms=rr.duration_ms, error_code=rr.error_code, recognized=rec_out, recognition_ok=rec_ok)


@app.post("/auto_run", response_model=AutoRunResponse)
def auto_run(req: AutoRunRequest):
    """Capture frame -> identify -> auto-route Scene A (white_dragon) or B (one_dot)."""
    rr = orch.auto_run_scene(style=req.style, safe=req.safe)
    rec = rr.recognized
    return AutoRunResponse(
        ok=rr.ok,
        scene=rr.scene,
        label=rec.label if rec else None,
        confidence=rec.confidence if rec else None,
        duration_ms=rr.duration_ms,
        error_code=rr.error_code,
    )

@app.post("/activate")
def activate_frontend():
    """远程激活前端：前端轮询检测到 activate_pending=True 后自动开摄像头 + 启动 AutoLoop。
    由 OpenClaw 在每局开始时调用一次，替代操作员手动点击「开始自动识别」。
    """
    status.activate_pending = True
    status.log("ACTIVATE set: frontend will auto-start camera + AutoLoop")
    return {"ok": True}


@app.post("/trigger")
def trigger_once(style: str = "polite", safe: bool = True):
    """外部触发一次开牌（OpenClaw / 语音 / 物理按钮 → 前端 Watch Mode 执行）。
    设置 trigger_pending=True，前端 800ms 轮询检测到后自动执行一次 autoLoopTick。
    """
    if status.busy:
        status.log("TRIGGER rejected: busy")
        return {"ok": False, "error": "busy"}
    status.trigger_pending = True
    status.log(f"TRIGGER set: style={style} safe={safe}")
    return {"ok": True, "queued": True}


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


@app.post("/quick_identify", response_model=CaptureFrameResponse)
def quick_identify():
    """服务器直接用 CV2Camera 截帧 + 识别，省去浏览器上传图片的延迟。
    比 /capture_frame 快 ~200-400ms（无浏览器编码/上传开销）。
    arm/present_to_camera 返回后立即调用此接口。
    """
    frame_bytes = camera.capture_bytes()
    if not frame_bytes:
        status.log("QUICK_IDENTIFY: camera capture failed")
        return CaptureFrameResponse(ok=False, error="camera capture failed")

    status.log("QUICK_IDENTIFY: captured, identifying...")
    try:
        result = vision.identify(frame_bytes)
        rec_out = RecognizeOut(label=result.label, confidence=result.confidence)
        status.last_recognized = result
        recognition_ok = result.confidence >= RECOGNITION_SUCCESS_THRESHOLD
        status.log(f"QUICK_IDENTIFY: {result.label} ({result.confidence:.2f}) ok={recognition_ok}")
        return CaptureFrameResponse(ok=True, recognized=rec_out, recognition_ok=recognition_ok)
    except Exception as e:
        status.log(f"QUICK_IDENTIFY: error: {e}")
        return CaptureFrameResponse(ok=False, error=str(e))


@app.get("/health")
def health():
    """Check connectivity to all subsystems."""
    checks = {"api": True, "arm_adapter": arm_adapter}

    # Arm: try to reach the arm service (only meaningful in http mode)
    if arm_adapter == "http":
        try:
            arm.get_status()
            checks["arm_reachable"] = True
        except Exception as e:
            checks["arm_reachable"] = False
            checks["arm_error"] = str(e)
    else:
        checks["arm_reachable"] = True  # mock is always "reachable"

    # Vision
    checks["vision_adapter"] = type(vision).__name__

    # TTS: check if voice assets exist
    import os
    assets_path = os.path.join(os.path.dirname(__file__), "..", "adapters", "tts", "assets", "polite")
    checks["tts_assets"] = os.path.isdir(assets_path) and len(os.listdir(assets_path)) > 0

    checks["all_ok"] = checks["arm_reachable"] and checks["api"]
    return checks


@app.post("/capture_frame", response_model=CaptureFrameResponse)
def capture_frame(req: CaptureFrameRequest):
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
        recognition_ok = result.confidence >= RECOGNITION_SUCCESS_THRESHOLD
        status.log(f"CAPTURE_FRAME result: {result.label} ({result.confidence:.2f}) ok={recognition_ok}")
        return CaptureFrameResponse(ok=True, recognized=rec_out, recognition_ok=recognition_ok)
    except Exception as e:
        status.log(f"CAPTURE_FRAME vision error: {e}")
        return CaptureFrameResponse(ok=False, error=str(e))


@app.post("/calibrate")
def calibrate(req: CaptureFrameRequest, label: str):
    """保存参考帧到 histogram_vision（标定用）。
    label 参数: white_dragon 或 one_dot
    用法: POST /calibrate?label=white_dragon  body: { image: base64 }
    """
    if not hasattr(vision, "calibrate"):
        return {"ok": False, "error": "Vision adapter does not support calibration"}
    try:
        image_bytes = base64.b64decode(req.image)
    except Exception:
        return {"ok": False, "error": "base64 decode failed"}

    ok = vision.calibrate(label, image_bytes)
    cal_status = vision.calibration_status() if hasattr(vision, "calibration_status") else {}
    return {"ok": ok, "label": label, "calibration": cal_status}


@app.get("/calibrate")
def calibrate_status():
    """查询标定状态（哪些 label 已有参考图）。"""
    if hasattr(vision, "calibration_status"):
        return {"calibration": vision.calibration_status()}
    return {"calibration": {}}


@app.post("/calibrate/from_camera")
def calibrate_from_camera(label: str):
    """直接从服务器摄像头截帧并标定 —— 无需前端上传图片。
    用法: POST /calibrate/from_camera?label=white_dragon
    将牌放到摄像头前再调用此接口。
    """
    if not hasattr(vision, "calibrate"):
        return {"ok": False, "error": "Vision adapter does not support calibration"}
    frame_bytes = camera.capture_bytes()
    if not frame_bytes:
        return {"ok": False, "error": "Camera capture failed — check camera connection"}
    ok = vision.calibrate(label, frame_bytes)
    cal_status = vision.calibration_status() if hasattr(vision, "calibration_status") else {}
    status.log(f"CALIBRATE from_camera: label={label} ok={ok}")
    return {"ok": ok, "label": label, "calibration": cal_status}


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
    text = req.text.strip()
    status.log(f"VOICE: {text}")

    for pattern, action, reply in _VOICE_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            status.log(f"VOICE matched: {action}")
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
    sid = str(uuid.uuid4())[:8]
    status.log(f"SESSION_START: {sid}")
    return SessionStartResponse(session_id=sid, ok=True)


@app.post("/brain/input")
def brain_input(req: BrainInputRequest):
    status.log(f"BRAIN_INPUT: session={req.session_id} label={req.label} conf={req.confidence:.2f}")
    return {"ok": True, "session_id": req.session_id}


@app.post("/brain/decision")
def brain_decision(req: BrainDecisionRequest):
    status.log(f"BRAIN_DECISION: session={req.session_id} action={req.action} line={req.line_key}")

    scene = "A" if req.action == "throw" else "B"
    rr = orch.run_scene(RunRequest(scene=scene, style="polite", safe=True))

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
