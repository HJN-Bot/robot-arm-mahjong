"""
One-time calibration from reference photos.

Usage:
  cd /Users/eva/Desktop/majong
  software/.venv/bin/python software/scripts/calibrate_refs.py

Reads White.jpg (white_dragon) and OneBing.jpg (one_dot) from the project root,
computes HSV histograms, and saves them to adapters/vision/refs/histograms.pkl.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from software.adapters.vision.histogram_vision import HistogramVision
from software.services.status_store import StatusStore

REFS = {
    "white_dragon": ROOT / "White.jpg",
    "one_dot":      ROOT / "OneBing.jpg",
}

status = StatusStore()
vision = HistogramVision(status)

for label, path in REFS.items():
    if not path.exists():
        print(f"[ERROR] {path} not found")
        sys.exit(1)
    image_bytes = path.read_bytes()
    ok = vision.calibrate(label, image_bytes)
    print(f"  {'✅' if ok else '❌'}  {label}  ← {path.name}")

print()
print("Calibration status:", vision.calibration_status())
print("Done — histograms saved to adapters/vision/refs/histograms.pkl")
