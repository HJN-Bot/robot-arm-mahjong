import time
from software.orchestrator.contracts import RunRequest, RunResult, RecognizeResult
from software.orchestrator import errors

class Orchestrator:
    def __init__(self, arm, vision, tts, status_store):
        self.arm = arm
        self.vision = vision
        self.tts = tts
        self.status = status_store

    def run_scene(self, req: RunRequest) -> RunResult:
        if self.status.busy:
            return RunResult(ok=False, scene=req.scene, duration_ms=0, error_code=errors.ERR_BUSY)

        self.status.set_busy(True)
        t0 = time.time()
        recognized: RecognizeResult | None = None
        try:
            self.status.log(f"scene={req.scene} start style={req.style} safe={req.safe}")

            # 1) pick
            self.status.log("arm.pick")
            self.arm.pick_tile(safe=req.safe)

            # 2) present to camera
            self.status.log("arm.present_to_camera")
            self.arm.present_to_camera(safe=req.safe)

            # 3) recognize
            self.status.log("vision.recognize_once")
            recognized = self.vision.recognize_once()
            self.status.last_recognized = recognized
            self.status.log(f"vision.result label={recognized.label} conf={recognized.confidence:.2f}")

            # 4) tts say
            # Minimal lines for tomorrow
            line_key = "LOOK_DONE"
            self.status.log(f"tts.say {line_key}")
            self.tts.say(line_key=line_key, style=req.style)

            # 5) action
            if req.scene == "A":
                self.status.log("arm.throw_to_discard")
                self.arm.throw_to_discard(safe=req.safe)
            else:
                self.status.log("arm.return_tile")
                self.arm.return_tile(safe=req.safe)

            # 6) closing tts
            closing = "I_WANT_CHECK"
            self.status.log(f"tts.say {closing}")
            self.tts.say(line_key=closing, style=req.style)

            dt = int((time.time() - t0) * 1000)
            self.status.log(f"scene={req.scene} done dt={dt}ms")
            return RunResult(ok=True, scene=req.scene, duration_ms=dt, recognized=recognized)

        except TimeoutError:
            dt = int((time.time() - t0) * 1000)
            self.status.log("error timeout")
            return RunResult(ok=False, scene=req.scene, duration_ms=dt, error_code=errors.ERR_TIMEOUT, recognized=recognized)
        except Exception as e:
            dt = int((time.time() - t0) * 1000)
            self.status.log(f"error {type(e).__name__}: {e}")
            return RunResult(ok=False, scene=req.scene, duration_ms=dt, error_code=errors.ERR_UNKNOWN, recognized=recognized)
        finally:
            self.status.set_busy(False)
