"""
HTTP adapter for the robotic arm service.

Translates ArmAdapter method calls into HTTP requests to the arm team's server.
Default contract (adjust if the arm team uses different formats):
  Request:  POST /<action>  {"safe": true}
  Response: {"ok": true}    (or {"ok": false, "error": "..."})
"""

import httpx


class HttpArm:
    def __init__(self, status_store, base_url: str = "http://127.0.0.1:9000", timeout: float = 30.0):
        self.status = status_store
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        self.status.log(f"http_arm: POST {path}")
        resp = httpx.post(url, json=payload or {}, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok", True):
            raise RuntimeError(f"arm error on {path}: {data.get('error', 'unknown')}")
        self.status.log(f"http_arm: {path} done")
        return data

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        resp = httpx.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def pick_tile(self, safe: bool = True):
        self._post("/pick_tile", {"safe": safe})

    def present_to_camera(self, safe: bool = True):
        self._post("/present_to_camera", {"safe": safe})

    def throw_to_discard(self, safe: bool = True):
        self._post("/throw_to_discard", {"safe": safe})

    def return_tile(self, safe: bool = True):
        self._post("/return_tile", {"safe": safe})

    def home(self):
        self._post("/home")

    def estop(self):
        self._post("/estop")

    def tap(self, times: int = 3):
        self._post("/tap", {"times": times})

    def nod(self):
        self._post("/nod")

    def shake(self):
        self._post("/shake")

    def get_status(self) -> dict:
        return self._get("/status")
