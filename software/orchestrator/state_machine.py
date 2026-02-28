import time
from software.orchestrator.contracts import RunRequest, RunResult, RecognizeResult
from software.orchestrator import errors

class Orchestrator:
    def __init__(self, arm, vision, tts, status_store, camera=None):
        self.arm = arm
        self.vision = vision
        self.tts = tts
        self.status = status_store
        self.camera = camera

    def run_scene(self, req: RunRequest) -> RunResult:
        if self.status.busy:
            return RunResult(ok=False, scene=req.scene, duration_ms=0, error_code=errors.ERR_BUSY)

        self.status.set_busy(True)
        t0 = time.time()
        recognized: RecognizeResult | None = None
        try:
            self.status.log(f"scene={req.scene} start style={req.style} safe={req.safe}")

            # 1) opening tts: 来！开牌
            self.status.log("tts.say SCENE_START")
            self.tts.say(line_key="SCENE_START", style=req.style)

            # 2) pick
            self.status.log("arm.pick")
            self.arm.pick_tile(safe=req.safe)

            # 3) present to camera
            self.status.log("arm.present_to_camera")
            self.arm.present_to_camera(safe=req.safe)

            # 4) recognize — use pre-identified result from frontend if available
            if req.pre_recognized is not None:
                recognized = req.pre_recognized
                self.status.log(f"vision.pre_recognized label={recognized.label} conf={recognized.confidence:.2f}")
            else:
                self.status.log("vision.recognize_once")
                recognized = self.vision.recognize_once()
                self.status.log(f"vision.result label={recognized.label} conf={recognized.confidence:.2f}")
            self.status.last_recognized = recognized

            # 5) action
            if req.scene == "A":
                self.status.log("arm.throw_to_discard")
                self.arm.throw_to_discard(safe=req.safe)
            else:
                self.status.log("arm.return_tile")
                self.arm.return_tile(safe=req.safe)

            # 6) closing tts: Scene A → 我要验牌 / Scene B → 牌没有问题
            closing = "I_WANT_CHECK" if req.scene == "A" else "OK_NO_PROBLEM"
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

    def prepare_scene(self, style: str = "polite", safe: bool = True) -> dict:
        """
        Step 1 of split flow: TTS(来！开牌) → pick → present.
        Returns when arm is stable and tile is in front of camera.
        Frontend should then capture a frame and call execute_scene().
        """
        if self.status.busy:
            return {"ok": False, "error": "busy"}

        self.status.set_busy(True)
        self.status.last_recognized = None  # clear stale result so UI resets
        try:
            self.status.log("prepare_scene: SCENE_START TTS")
            self.tts.say(line_key="SCENE_START", style=style)
            self.status.log("prepare_scene: arm.pick")
            self.arm.pick_tile(safe=safe)
            self.status.log("prepare_scene: arm.present_to_camera")
            self.arm.present_to_camera(safe=safe)
            self.status.log("prepare_scene: ready — waiting for browser capture")
            return {"ok": True}
        except Exception as e:
            self.status.log(f"prepare_scene: error {e}")
            return {"ok": False, "error": str(e)}
        finally:
            self.status.set_busy(False)

    def execute_scene(self, scene: str, style: str, safe: bool, recognized: RecognizeResult) -> RunResult:
        """
        Step 2 of split flow: arm action + closing TTS, using pre-identified tile.
        Called after frontend has captured and identified the tile.
        """
        if self.status.busy:
            return RunResult(ok=False, scene=scene, duration_ms=0, error_code=errors.ERR_BUSY)

        self.status.set_busy(True)
        t0 = time.time()
        self.status.last_recognized = recognized
        try:
            if scene == "A":
                self.status.log("execute_scene: arm.throw_to_discard")
                self.arm.throw_to_discard(safe=safe)
            else:
                self.status.log("execute_scene: arm.return_tile")
                self.arm.return_tile(safe=safe)

            closing = "I_WANT_CHECK" if scene == "A" else "OK_NO_PROBLEM"
            self.status.log(f"execute_scene: tts {closing}")
            self.tts.say(line_key=closing, style=style)

            dt = int((time.time() - t0) * 1000)
            self.status.log(f"execute_scene: done scene={scene} dt={dt}ms")
            return RunResult(ok=True, scene=scene, duration_ms=dt, recognized=recognized)
        except Exception as e:
            dt = int((time.time() - t0) * 1000)
            self.status.log(f"execute_scene: error {e}")
            return RunResult(ok=False, scene=scene, duration_ms=dt, error_code=errors.ERR_UNKNOWN, recognized=recognized)
        finally:
            self.status.set_busy(False)

    def auto_run_scene(self, style: str = "polite", safe: bool = True):
        """
        Full auto flow:
          TTS(来！开牌) → pick → present → capture → identify
          → white_dragon: Scene A → throw(15s) → TTS(我要验牌)
          → one_dot:      Scene B → return(15s) → TTS(牌没有问题)
        """
        if self.status.busy:
            return RunResult(ok=False, scene="A", duration_ms=0, error_code=errors.ERR_BUSY)

        self.status.set_busy(True)
        t0 = time.time()
        recognized = None
        scene = "A"
        try:
            # 1) opening tts: 来！开牌 (blocking — plays fully before arm moves)
            self.status.log("auto_run: tts SCENE_START → 来！开牌")
            self.tts.say(line_key="SCENE_START", style=style)

            # 2) arm: pick tile
            self.arm.pick_tile(safe=safe)

            # 3) arm: present tile to camera and hold steady
            self.arm.present_to_camera(safe=safe)

            # 4) capture frame AFTER arm is stable in front of camera
            self.status.log("auto_run: 📸 等待稳定 1s...")
            time.sleep(1)
            self.status.log("auto_run: 📸 CAPTURING!")
            frame_bytes = None
            if self.camera is not None:
                frame_bytes = self.camera.capture_bytes()

            if frame_bytes and hasattr(self.vision, "identify"):
                recognized = self.vision.identify(frame_bytes)
                self.status.log(f"auto_run: vision.identify → {recognized.label} conf={recognized.confidence:.2f}")
            else:
                recognized = self.vision.recognize_once()
                self.status.log(f"auto_run: vision.fallback → {recognized.label} conf={recognized.confidence:.2f}")

            self.status.last_recognized = recognized

            # 5) route scene: white_dragon → A (throw), anything else → B (return)
            scene = "A" if recognized.label == "white_dragon" else "B"
            self.status.log(
                f"auto_run: ROUTE label={recognized.label} conf={recognized.confidence:.2f} → Scene {scene}"
                + (" (扔出 → 我要验牌)" if scene == "A" else " (放回 → 牌没有问题)")
            )

            # 6) execute arm action (blocking, ~15s)
            if scene == "A":
                self.arm.throw_to_discard(safe=safe)
            else:
                self.arm.return_tile(safe=safe)

            # 7) closing tts AFTER arm finishes:
            #    Scene A → 我要验牌.mp3  |  Scene B → 牌没有问题.mp3
            closing = "I_WANT_CHECK" if scene == "A" else "OK_NO_PROBLEM"
            self.status.log(f"auto_run: tts {closing}")
            self.tts.say(line_key=closing, style=style)

            dt = int((time.time() - t0) * 1000)
            self.status.log(f"auto_run: done scene={scene} dt={dt}ms")
            return RunResult(ok=True, scene=scene, duration_ms=dt, recognized=recognized)

        except Exception as e:
            dt = int((time.time() - t0) * 1000)
            self.status.log(f"auto_run: error {type(e).__name__}: {e}")
            return RunResult(ok=False, scene=scene, duration_ms=dt, error_code=errors.ERR_UNKNOWN, recognized=recognized)
        finally:
            self.status.set_busy(False)
