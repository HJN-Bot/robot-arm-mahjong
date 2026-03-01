"""
HTTP adapter for the SODA OS robotic arm service.

Maps ArmAdapter methods to the SODA OS Shell mahjong endpoints:
  /mahjong/observe  — detect tiles via AprilTag
  /mahjong/pick     — grab a tile by AprilTag ID
  /mahjong/show     — present tile to laptop camera
  /mahjong/discard  — throw tile to discard area
  /mahjong/keep     — return tile to keep area
  /robot/home       — move to home position
  /robot/stop       — emergency stop
"""

import httpx


class HttpArm:
    def __init__(self, status_store, base_url: str = "http://127.0.0.1:9000", timeout: float = 30.0):
        self.status = status_store
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._last_observed_tile_id: int | None = None

    def _post(self, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        self.status.log(f"http_arm: POST {path}")
        if payload:
            resp = httpx.post(url, json=payload, timeout=self.timeout)
        else:
            resp = httpx.post(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if "success" in data and not data["success"]:
            raise RuntimeError(f"arm error on {path}: {data.get('message', 'unknown')}")
        self.status.log(f"http_arm: {path} done")
        return data

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        resp = httpx.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def pick_tile(self, safe: bool = True):
        # First observe to detect tiles
        obs = self._post("/mahjong/observe")
        tiles = obs.get("tiles", [])
        if not tiles:
            raise RuntimeError("No tiles detected by arm camera")
        # Pick the first detected tile
        tile_id = tiles[0]["id"]
        self._last_observed_tile_id = tile_id
        self.status.log(f"http_arm: picking tile id={tile_id}")
        self._post("/mahjong/pick", {"tile_id": tile_id})

    def present_to_camera(self, safe: bool = True):
        self._post("/mahjong/show")

    def throw_to_discard(self, safe: bool = True):
        self._post("/mahjong/discard")

    def return_tile(self, safe: bool = True):
        self._post("/mahjong/keep")

    def home(self):
        self._post("/robot/home")

    def estop(self):
        self._post("/robot/stop")

    def tap(self, times: int = 3):
        self.status.log("http_arm: tap not supported by SODA OS, skipping")

    def nod(self):
        self.status.log("http_arm: nod not supported by SODA OS, skipping")

    def shake(self):
        self.status.log("http_arm: shake not supported by SODA OS, skipping")

    def get_status(self) -> dict:
        return self._get("/mahjong/status")
