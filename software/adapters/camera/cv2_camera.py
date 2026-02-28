"""
OpenCV webcam capture adapter.
CAMERA_INDEX env var (default 0) selects the webcam device.
"""
import os
import cv2
from software.adapters.camera.base import CameraAdapter

class CV2Camera(CameraAdapter):
    def __init__(self, status_store, index: int | None = None):
        self.status = status_store
        self._index = index if index is not None else int(os.getenv("CAMERA_INDEX", "0"))
        self._cap = None

    def _open(self):
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self._index)
            if not self._cap.isOpened():
                self.status.log(f"cv2_camera: failed to open device {self._index}")

    def capture_bytes(self) -> bytes | None:
        self._open()
        if self._cap is None or not self._cap.isOpened():
            return None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            self.status.log("cv2_camera: frame capture failed")
            return None
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            return None
        return bytes(buf)

    def release(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None
