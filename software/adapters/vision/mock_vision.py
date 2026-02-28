import random
from software.adapters.vision.base import VisionAdapter
from software.orchestrator.contracts import RecognizeResult

class MockVision(VisionAdapter):
    def __init__(self, status_store):
        self.status = status_store

    def recognize_once(self) -> RecognizeResult:
        label = random.choice(["white_dragon", "one_dot"])
        conf = 0.9
        self.status.log(f"mock_vision: {label}")
        return RecognizeResult(label=label, confidence=conf)

    def identify(self, image_bytes: bytes) -> RecognizeResult:
        # Mock: ignore image, return random result
        # Real impl will send image_bytes to OpenClaw Vision API
        return self.recognize_once()
