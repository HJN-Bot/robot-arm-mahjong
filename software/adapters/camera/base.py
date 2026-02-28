from abc import ABC, abstractmethod

class CameraAdapter(ABC):
    @abstractmethod
    def capture_bytes(self) -> bytes | None:
        """Capture one frame. Returns JPEG bytes or None on failure."""
        ...
