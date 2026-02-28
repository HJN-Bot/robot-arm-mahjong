class VisionAdapter:
    def recognize_once(self):
        """Return RecognizeResult — used by orchestrator state machine."""
        raise NotImplementedError

    def identify(self, image_bytes: bytes):
        """Return RecognizeResult from raw image bytes — used by /capture_frame."""
        # Default: ignore the image, fall back to recognize_once
        return self.recognize_once()
