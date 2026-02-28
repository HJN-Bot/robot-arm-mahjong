"""
Integration test script — hits all endpoints and verifies responses.

Usage:
    # Mock mode (default):
    bash software/scripts/dev_run.sh
    python software/scripts/integration_test.py

    # HTTP arm mode (run fake_arm_server.py first):
    python software/scripts/fake_arm_server.py  (terminal 1)
    ARM_ADAPTER=http bash software/scripts/dev_run.sh  (terminal 2)
    python software/scripts/integration_test.py  (terminal 3)
"""

import sys
import time
import httpx

BASE = "http://localhost:8000"
TIMEOUT = 60.0
passed = 0
failed = 0


def test(name: str, method: str, path: str, body: dict | None = None, checks: dict | None = None):
    global passed, failed
    url = f"{BASE}{path}"
    checks = checks or {}
    try:
        if method == "GET":
            r = httpx.get(url, timeout=TIMEOUT)
        else:
            r = httpx.post(url, json=body or {}, timeout=TIMEOUT)

        if r.status_code != 200:
            print(f"  FAIL  {name} — HTTP {r.status_code}")
            failed += 1
            return

        data = r.json()
        for key, expected in checks.items():
            actual = data.get(key)
            if actual != expected:
                print(f"  FAIL  {name} — {key}: expected {expected!r}, got {actual!r}")
                failed += 1
                return

        print(f"  OK    {name}")
        passed += 1

    except httpx.ConnectError:
        print(f"  FAIL  {name} — connection refused (is the server running?)")
        failed += 1
    except Exception as e:
        print(f"  FAIL  {name} — {type(e).__name__}: {e}")
        failed += 1


def main():
    print(f"\nIntegration tests against {BASE}\n")
    print("--- Health & Status ---")
    test("GET /health", "GET", "/health", None, {"all_ok": True})
    test("GET /status", "GET", "/status")

    print("\n--- Scenes ---")
    test("POST /run_scene A", "POST", "/run_scene",
         {"scene": "A", "style": "polite", "safe": True},
         {"ok": True, "scene": "A"})

    test("POST /run_scene B", "POST", "/run_scene",
         {"scene": "B", "style": "meme", "safe": False},
         {"ok": True, "scene": "B"})

    test("POST /run_scene A (pre-recognized)", "POST", "/run_scene",
         {"scene": "A", "style": "polite", "safe": True,
          "recognized_label": "white_dragon", "recognized_conf": 0.95},
         {"ok": True, "scene": "A"})

    print("\n--- Split Flow ---")
    test("POST /arm/start_scene", "POST", "/arm/start_scene?style=polite&safe=true",
         None, {"ok": True})

    test("POST /execute_scene", "POST", "/execute_scene",
         {"scene": "A", "style": "polite", "safe": True,
          "recognized_label": "one_dot", "recognized_conf": 0.88},
         {"ok": True, "scene": "A"})

    print("\n--- Auto Run ---")
    test("POST /auto_run", "POST", "/auto_run",
         {"style": "polite", "safe": True},
         {"ok": True})

    print("\n--- Trigger ---")
    time.sleep(1)  # wait for busy to clear from auto_run
    test("POST /trigger", "POST", "/trigger?style=polite&safe=true",
         None, {"ok": True})

    print("\n--- Arm Gestures ---")
    test("POST /tap", "POST", "/tap", {}, {"ok": True})
    test("POST /nod", "POST", "/nod", {}, {"ok": True})
    test("POST /shake", "POST", "/shake", {}, {"ok": True})
    test("POST /home", "POST", "/home", {}, {"ok": True})
    test("POST /estop", "POST", "/estop", {}, {"ok": True})

    print("\n--- Vision ---")
    test("POST /capture_frame", "POST", "/capture_frame",
         {"image": "aGVsbG8="},
         {"ok": True})

    test("GET /calibrate (status)", "GET", "/calibrate")

    print("\n--- Voice ---")
    test("POST /voice_trigger (scene A)", "POST", "/voice_trigger",
         {"text": "scene A"},
         {"ok": True, "action": "scene_a"})

    test("POST /voice_trigger (tap)", "POST", "/voice_trigger",
         {"text": "tap"},
         {"ok": True, "action": "tap"})

    test("POST /voice_trigger (unknown)", "POST", "/voice_trigger",
         {"text": "hello"},
         {"ok": True, "action": None})

    print("\n--- Brain Callbacks ---")
    test("POST /session/start", "POST", "/session/start",
         {},
         {"ok": True})

    test("POST /brain/input", "POST", "/brain/input",
         {"session_id": "test", "label": "white_dragon", "confidence": 0.92},
         {"ok": True})

    test("POST /brain/decision (throw)", "POST", "/brain/decision",
         {"session_id": "test", "action": "throw", "line_key": "LOOK_DONE", "ui_text": "throwing"},
         {"ok": True, "action": "throw"})

    test("POST /brain/decision (return)", "POST", "/brain/decision",
         {"session_id": "test", "action": "return", "line_key": "OK_NO_PROBLEM", "ui_text": "returning"},
         {"ok": True, "action": "return"})

    print("\n--- Final Status ---")
    test("GET /status (final)", "GET", "/status")

    # Summary
    total = passed + failed
    print(f"\n{'='*40}")
    print(f"  {passed}/{total} passed, {failed} failed")
    print(f"{'='*40}\n")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
