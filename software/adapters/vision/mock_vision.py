import random
from software.orchestrator.contracts import RecognizeResult

class MockVision:
    def __init__(self, status_store):
        self.status = status_store

    def recognize_once(self) -> RecognizeResult:
        # simulate 2-class classification
        label = random.choice(["white_dragon", "one_dot"])
        conf = 0.9
        self.status.log(f"mock_vision: {label}")
        return RecognizeResult(label=label, confidence=conf)
