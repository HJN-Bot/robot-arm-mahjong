"""
Histogram-based tile classifier (2-class: white_dragon vs one_dot).

Workflow:
  1. Calibrate: capture one reference frame per tile class via POST /calibrate
     - PUT reference image bytes → saved to adapters/vision/refs/
  2. Identify: compare new frame's HSV histogram against both refs
     - Returns the class with higher correlation score

No external ML model needed. Works offline. ~5ms per call.
"""
import io
import os
import pickle
import numpy as np
from pathlib import Path
from software.adapters.vision.base import VisionAdapter
from software.orchestrator.contracts import RecognizeResult

try:
    import cv2
    _CV2_OK = True
except ImportError:
    _CV2_OK = False

REFS_DIR = Path(__file__).parent / "refs"
REFS_DIR.mkdir(exist_ok=True)

LABELS = ["white_dragon", "one_dot"]
HIST_FILE = REFS_DIR / "histograms.pkl"

# HSV histogram settings
H_BINS, S_BINS = 36, 32
HIST_SIZE = [H_BINS, S_BINS]
HIST_RANGES = [0, 180, 0, 256]
CHANNELS = [0, 1]


def _compute_hist(bgr_img):
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], CHANNELS, None, HIST_SIZE, HIST_RANGES)
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    return hist


def _bytes_to_bgr(image_bytes: bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _center_crop(img, ratio=0.5):
    """Crop the center region to reduce background interference."""
    h, w = img.shape[:2]
    ch, cw = int(h * ratio), int(w * ratio)
    y0 = (h - ch) // 2
    x0 = (w - cw) // 2
    return img[y0:y0+ch, x0:x0+cw]


class HistogramVision(VisionAdapter):
    """
    2-class histogram matcher. Call calibrate() once per tile before use.
    Falls back to mock random when no references are saved.
    """

    def __init__(self, status_store):
        self.status = status_store
        self._hists: dict[str, np.ndarray] = {}
        self._load_refs()

    # ── Calibration ────────────────────────────────────────────────────────

    def calibrate(self, label: str, image_bytes: bytes) -> bool:
        """Save a reference histogram for the given label."""
        if not _CV2_OK:
            self.status.log("histogram_vision: opencv not installed")
            return False
        if label not in LABELS:
            self.status.log(f"histogram_vision: unknown label '{label}'")
            return False

        img = _bytes_to_bgr(image_bytes)
        if img is None:
            self.status.log("histogram_vision: failed to decode calibration image")
            return False

        cropped = _center_crop(img, ratio=0.6)
        hist = _compute_hist(cropped)
        self._hists[label] = hist

        # Also save the raw reference image for debugging
        ref_img_path = REFS_DIR / f"{label}.jpg"
        cv2.imwrite(str(ref_img_path), img)

        self._save_refs()
        self.status.log(f"histogram_vision: calibrated '{label}' ✅")
        return True

    def calibration_status(self) -> dict:
        return {label: label in self._hists for label in LABELS}

    # ── Identification ──────────────────────────────────────────────────────

    def identify(self, image_bytes: bytes) -> RecognizeResult:
        if not _CV2_OK:
            self.status.log("histogram_vision: opencv missing, falling back to mock")
            return self._mock_result()

        if len(self._hists) < 2:
            missing = [l for l in LABELS if l not in self._hists]
            self.status.log(f"histogram_vision: missing refs for {missing}, use mock")
            return self._mock_result()

        img = _bytes_to_bgr(image_bytes)
        if img is None:
            self.status.log("histogram_vision: failed to decode frame")
            return self._mock_result()

        cropped = _center_crop(img, ratio=0.6)
        query_hist = _compute_hist(cropped)

        scores = {}
        for label, ref_hist in self._hists.items():
            score = cv2.compareHist(ref_hist, query_hist, cv2.HISTCMP_CORREL)
            scores[label] = score

        sorted_labels = sorted(scores, key=scores.__getitem__, reverse=True)
        best_label  = sorted_labels[0]
        best_score  = scores[best_label]
        second_best = sorted_labels[1]
        margin = best_score - scores[second_best]

        # Confidence = margin amplified: 0 margin → 0.5, full margin (1.0) → 1.0
        # This makes confidence represent "how clearly it won" rather than absolute score
        confidence = float(np.clip(0.5 + margin * 2.0, 0.0, 1.0))

        self.status.log(
            f"histogram_vision: {best_label}={best_score:.3f}  {second_best}={scores[second_best]:.3f}"
            f"  margin={margin:.3f}  conf={confidence:.2f}"
        )
        return RecognizeResult(label=best_label, confidence=confidence)

    def recognize_once(self) -> RecognizeResult:
        """Used by orchestrator — no image available, fall back to mock."""
        return self._mock_result()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _save_refs(self):
        with open(HIST_FILE, "wb") as f:
            pickle.dump(self._hists, f)

    def _load_refs(self):
        if HIST_FILE.exists():
            try:
                with open(HIST_FILE, "rb") as f:
                    self._hists = pickle.load(f)
                self.status.log(
                    f"histogram_vision: loaded refs for {list(self._hists.keys())}"
                )
            except Exception as e:
                self.status.log(f"histogram_vision: failed to load refs: {e}")
                self._hists = {}

        # If any label is missing, try to auto-calibrate from existing ref jpg files
        missing = [l for l in LABELS if l not in self._hists]
        if missing and _CV2_OK:
            self._auto_calibrate_from_refs_jpg(missing)

    def _auto_calibrate_from_refs_jpg(self, labels=None):
        """Load reference histograms from existing refs/*.jpg files.

        Called on startup when histograms.pkl is absent or incomplete.
        Each jpg was saved previously via the /calibrate endpoint.
        """
        if not _CV2_OK:
            return
        if labels is None:
            labels = LABELS
        calibrated = []
        for label in labels:
            jpg_path = REFS_DIR / f"{label}.jpg"
            if not jpg_path.exists():
                self.status.log(f"histogram_vision: no ref jpg for '{label}' at {jpg_path}")
                continue
            try:
                img = cv2.imread(str(jpg_path))
                if img is None:
                    self.status.log(f"histogram_vision: failed to read {jpg_path.name}")
                    continue
                cropped = _center_crop(img, ratio=0.6)
                hist = _compute_hist(cropped)
                self._hists[label] = hist
                calibrated.append(label)
                self.status.log(f"histogram_vision: auto-calibrated '{label}' from {jpg_path.name} ✅")
            except Exception as e:
                self.status.log(f"histogram_vision: auto-calib error for '{label}': {e}")
        if calibrated:
            self._save_refs()
            self.status.log(f"histogram_vision: auto-calib complete → {calibrated}")

    def _mock_result(self) -> RecognizeResult:
        import random
        label = random.choice(LABELS)
        return RecognizeResult(label=label, confidence=0.5)
