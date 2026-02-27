"""Minimal classifier placeholder: white_dragon vs one_dot.

Tomorrow we can implement either:
- simple template matching
- a tiny on-device model
- or just hardcode based on a printed marker on the tile

This file is intentionally a placeholder.
"""

from software.orchestrator.contracts import RecognizeResult

class Min2Classifier:
    def recognize_once(self) -> RecognizeResult:
        # TODO: implement real capture + classification
        return RecognizeResult(label="white_dragon", confidence=0.5)
