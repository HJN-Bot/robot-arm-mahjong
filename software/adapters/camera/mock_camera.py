"""Mock camera: loads a random ref image from vision/refs/ for testing."""
import random
from pathlib import Path
from software.adapters.camera.base import CameraAdapter

REFS_DIR = Path(__file__).parent.parent / "vision" / "refs"

class MockCamera(CameraAdapter):
    def __init__(self, status_store):
        self.status = status_store

    def capture_bytes(self) -> bytes | None:
        jpegs = list(REFS_DIR.glob("*.jpg"))
        if not jpegs:
            self.status.log("mock_camera: no ref images found")
            return None
        chosen = random.choice(jpegs)
        self.status.log(f"mock_camera: serving {chosen.name}")
        return chosen.read_bytes()
