from fastapi import FastAPI
from software.services.models import RunSceneRequest, RunSceneResponse, StatusResponse, RecognizeOut
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
