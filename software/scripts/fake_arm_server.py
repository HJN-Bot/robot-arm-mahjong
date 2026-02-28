"""
Fake arm server for testing HttpArm adapter without physical hardware.

Simulates the arm team's HTTP service on port 9000.
Each endpoint logs, sleeps briefly (simulating movement), and returns {"ok": true}.

Usage:
    python software/scripts/fake_arm_server.py
"""

import time
import uvicorn
from fastapi import FastAPI, Request

app = FastAPI(title="fake-arm-server")


def _simulate(action: str, body: dict, delay: float = 0.5) -> dict:
    safe = body.get("safe", True)
    actual_delay = delay * (1.5 if safe else 1.0)
    print(f"[arm] {action} (safe={safe}) — moving for {actual_delay:.1f}s ...")
    time.sleep(actual_delay)
    print(f"[arm] {action} done")
    return {"ok": True}


@app.post("/pick_tile")
async def pick_tile(request: Request):
    return _simulate("pick_tile", await request.json())


@app.post("/present_to_camera")
async def present_to_camera(request: Request):
    return _simulate("present_to_camera", await request.json())


@app.post("/throw_to_discard")
async def throw_to_discard(request: Request):
    return _simulate("throw_to_discard", await request.json())


@app.post("/return_tile")
async def return_tile(request: Request):
    return _simulate("return_tile", await request.json())


@app.post("/home")
async def home(request: Request):
    return _simulate("home", await request.json(), delay=0.3)


@app.post("/estop")
async def estop(request: Request):
    print("[arm] ESTOP — immediate stop")
    return {"ok": True}


@app.post("/tap")
async def tap(request: Request):
    body = await request.json()
    times = body.get("times", 3)
    print(f"[arm] tap x{times}")
    time.sleep(0.15 * times)
    print(f"[arm] tap done")
    return {"ok": True}


@app.post("/nod")
async def nod(request: Request):
    return _simulate("nod", {}, delay=0.4)


@app.post("/shake")
async def shake(request: Request):
    return _simulate("shake", {}, delay=0.4)


@app.get("/status")
async def status():
    return {"ok": True, "state": "idle"}


if __name__ == "__main__":
    print("Fake arm server starting on http://localhost:9000")
    uvicorn.run(app, host="0.0.0.0", port=9000)
