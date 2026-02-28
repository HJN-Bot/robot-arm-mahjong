"""
Enhanced histogram-based tile classifier (2-class: white_dragon vs one_dot).

Pipeline:
  1. Calibrate: POST /calibrate with reference image per tile class
     - Saves histogram + color feature stats to refs/
  2. Identify:
     a. Auto-detect tile ROI (white rectangle) → fall back to center crop
     b. Compute HSV histogram + saturation/color features
     c. Fuse histogram score + color feature score
     d. Return best label with combined confidence

Key insight: white_dragon is mostly white+black (low saturation), while
one_dot has a green ring + red center (high saturation). This saturation
contrast is a robust secondary discriminator that complements the histogram.

No external ML model needed. Works offline. ~8ms per call.
"""
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

# HSV histogram: H+S channels
H_BINS, S_BINS = 36, 32
HIST_SIZE = [H_BINS, S_BINS]
HIST_RANGES = [0, 180, 0, 256]
CHANNELS = [0, 1]

# Fusion weights: histogram vs color-feature score
# Raise FEAT_WEIGHT when tile ROI is reliably detected; lower it when relying on center crop
HIST_WEIGHT = 0.55
FEAT_WEIGHT = 0.45


# ── Image helpers ───────────────────────────────────────────────────────────

def _bytes_to_bgr(image_bytes: bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _center_crop(img, ratio=0.5):
    h, w = img.shape[:2]
    ch, cw = int(h * ratio), int(w * ratio)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return img[y0:y0+ch, x0:x0+cw]


def _find_tile_roi(bgr_img):
    """Detect the tile face (white rectangle) to remove background contamination.

    Looks for the largest bright, approximately-rectangular region.
    Returns cropped tile image or None if detection is not confident.
    """
    h, w = bgr_img.shape[:2]
    gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)

    # Bright region = tile face (V > 200 in HSV ≈ gray > 190)
    _, thresh = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY)

    # Close small gaps (tile design holes)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    frame_area = h * w

    best, best_score = None, 0.0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Tile must be 5%-75% of the total frame
        if area < frame_area * 0.05 or area > frame_area * 0.75:
            continue
        bx, by, bw, bh = cv2.boundingRect(cnt)
        rect_area = bw * bh
        if rect_area == 0:
            continue
        # Rectangularity: how close to a perfect rectangle
        rectangularity = area / rect_area
        # Aspect ratio: mahjong tiles are roughly 0.6–0.9 wide/tall
        aspect = min(bw, bh) / max(bw, bh) if max(bw, bh) > 0 else 0
        if rectangularity < 0.55 or aspect < 0.45:
            continue
        score = area * rectangularity
        if score > best_score:
            best_score = score
            best = (bx, by, bw, bh)

    if best is None:
        return None

    bx, by, bw, bh = best
    pad = 8
    x1 = max(0, bx - pad)
    y1 = max(0, by - pad)
    x2 = min(w, bx + bw + pad)
    y2 = min(h, by + bh + pad)
    roi = bgr_img[y1:y2, x1:x2]
    # Reject if ROI is suspiciously small
    if roi.shape[0] < 40 or roi.shape[1] < 40:
        return None
    return roi


# ── Feature extraction ──────────────────────────────────────────────────────

def _compute_hist(bgr_img):
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], CHANNELS, None, HIST_SIZE, HIST_RANGES)
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    return hist


def _compute_color_features(bgr_img) -> dict:
    """Extract saturation and hue features from an image region.

    white_dragon tile face: mostly white+black → very low saturation
    one_dot tile face:      green ring + red center → high saturation

    Returns a dict with float values (all in [0, 1]).
    """
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    h_ch, s_ch, v_ch = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
    total = bgr_img.shape[0] * bgr_img.shape[1]

    sat_mean = float(s_ch.mean()) / 255.0

    # Colorful pixels: S > 40 and V > 40 (avoids counting shadow/black as "colorful")
    colorful_mask = (s_ch > 40) & (v_ch > 40)
    colorful_ratio = float(colorful_mask.sum()) / total

    # Green-range pixels (H: 25–90 in OpenCV, the range for this tile's green design)
    green_mask = cv2.inRange(hsv, (25, 20, 30), (90, 255, 255))
    green_ratio = float(green_mask.sum()) / 255 / total

    return {
        "sat_mean":      sat_mean,
        "colorful_ratio": colorful_ratio,
        "green_ratio":   green_ratio,
    }


def _feature_score(query_feat: dict, ref_feat: dict) -> float:
    """Compute similarity score [0, 1] between query and reference color features."""
    # Weighted L1 distance across features; smaller distance = higher score
    weights = {"sat_mean": 0.5, "colorful_ratio": 0.35, "green_ratio": 0.15}
    dist = sum(
        weights[k] * abs(query_feat[k] - ref_feat[k])
        for k in weights
        if k in query_feat and k in ref_feat
    )
    # Map distance to score: dist=0 → 1.0, dist=0.5 → 0.0
    return float(np.clip(1.0 - dist * 2.0, 0.0, 1.0))


# ── Classifier ──────────────────────────────────────────────────────────────

class HistogramVision(VisionAdapter):
    """
    2-class tile classifier using fused histogram + color features.
    Call calibrate() once per tile before use.
    Falls back to mock random when no references are saved.
    """

    def __init__(self, status_store):
        self.status = status_store
        self._hists: dict[str, np.ndarray] = {}
        self._feats: dict[str, dict] = {}   # color feature refs per label
        self._load_refs()

    # ── Calibration ────────────────────────────────────────────────────────

    def calibrate(self, label: str, image_bytes: bytes) -> bool:
        """Save reference histogram + color features for the given label."""
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

        analysis, source = self._get_analysis_region(img)
        self._hists[label] = _compute_hist(analysis)
        self._feats[label] = _compute_color_features(analysis)

        # Save raw image for debugging / re-calibration
        cv2.imwrite(str(REFS_DIR / f"{label}.jpg"), img)
        self._save_refs()

        feat = self._feats[label]
        self.status.log(
            f"histogram_vision: calibrated '{label}' via {source}"
            f"  sat={feat['sat_mean']:.2f}"
            f"  colorful={feat['colorful_ratio']:.2f}"
            f"  green={feat['green_ratio']:.2f} ✅"
        )
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

        analysis, source = self._get_analysis_region(img)

        # ── Histogram scores ──
        query_hist = _compute_hist(analysis)
        hist_scores = {
            label: cv2.compareHist(ref_hist, query_hist, cv2.HISTCMP_CORREL)
            for label, ref_hist in self._hists.items()
        }

        # ── Color feature scores ──
        use_feats = len(self._feats) == 2
        if use_feats:
            query_feat = _compute_color_features(analysis)
            feat_scores = {
                label: _feature_score(query_feat, ref_feat)
                for label, ref_feat in self._feats.items()
            }
        else:
            feat_scores = {label: 0.5 for label in LABELS}

        # ── Fuse scores ──
        fused = {
            label: HIST_WEIGHT * hist_scores[label] + FEAT_WEIGHT * feat_scores[label]
            for label in LABELS
        }

        sorted_labels = sorted(fused, key=fused.__getitem__, reverse=True)
        best_label  = sorted_labels[0]
        second_best = sorted_labels[1]
        margin = fused[best_label] - fused[second_best]

        confidence = float(np.clip(0.5 + margin * 2.5, 0.0, 1.0))

        feat_str = ""
        if use_feats:
            qf = query_feat
            feat_str = (
                f"  sat={qf['sat_mean']:.2f}"
                f"  colorful={qf['colorful_ratio']:.2f}"
                f"  feat_margin={feat_scores[best_label]-feat_scores[second_best]:.3f}"
            )

        self.status.log(
            f"histogram_vision [{source}]: {best_label}"
            f"  hist={hist_scores[best_label]:.3f}/{hist_scores[second_best]:.3f}"
            f"  fused_margin={margin:.3f}  conf={confidence:.2f}"
            f"{feat_str}"
        )
        return RecognizeResult(label=best_label, confidence=confidence)

    def recognize_once(self) -> RecognizeResult:
        """Used by orchestrator — no image available, fall back to mock."""
        return self._mock_result()

    # ── Internal helpers ────────────────────────────────────────────────────

    def _get_analysis_region(self, bgr_img):
        """Return (analysis_img, source_name) using ROI detection or center crop."""
        roi = _find_tile_roi(bgr_img)
        if roi is not None:
            return roi, "roi"
        return _center_crop(bgr_img, ratio=0.55), "center_crop"

    # ── Persistence ─────────────────────────────────────────────────────────

    def _save_refs(self):
        with open(HIST_FILE, "wb") as f:
            pickle.dump({"hists": self._hists, "feats": self._feats}, f)

    def _load_refs(self):
        if HIST_FILE.exists():
            try:
                with open(HIST_FILE, "rb") as f:
                    data = pickle.load(f)
                # Support both old format (plain dict of hists) and new format
                if isinstance(data, dict) and "hists" in data:
                    self._hists = data.get("hists", {})
                    self._feats = data.get("feats", {})
                else:
                    self._hists = data   # legacy format
                    self._feats = {}
                self.status.log(
                    f"histogram_vision: loaded refs for {list(self._hists.keys())}"
                    f"  feats={'yes' if self._feats else 'no (legacy, will recompute)'}"
                )
            except Exception as e:
                self.status.log(f"histogram_vision: failed to load refs: {e}")
                self._hists = {}
                self._feats = {}

        missing_hists = [l for l in LABELS if l not in self._hists]
        if missing_hists and _CV2_OK:
            self._auto_calibrate_from_refs_jpg(missing_hists)
        elif _CV2_OK and len(self._feats) < len(self._hists):
            # Recompute missing feature stats from existing ref jpegs
            self._recompute_feats_from_jpgs()

    def _auto_calibrate_from_refs_jpg(self, labels=None):
        """Load histogram + color features from refs/*.jpg files on startup."""
        if not _CV2_OK:
            return
        if labels is None:
            labels = LABELS
        calibrated = []
        for label in labels:
            jpg_path = REFS_DIR / f"{label}.jpg"
            if not jpg_path.exists():
                self.status.log(f"histogram_vision: no ref jpg for '{label}'")
                continue
            try:
                img = cv2.imread(str(jpg_path))
                if img is None:
                    self.status.log(f"histogram_vision: failed to read {jpg_path.name}")
                    continue
                analysis, source = self._get_analysis_region(img)
                self._hists[label] = _compute_hist(analysis)
                self._feats[label] = _compute_color_features(analysis)
                calibrated.append(label)
                self.status.log(
                    f"histogram_vision: auto-calibrated '{label}' from {jpg_path.name}"
                    f" via {source} ✅"
                )
            except Exception as e:
                self.status.log(f"histogram_vision: auto-calib error for '{label}': {e}")
        if calibrated:
            self._save_refs()

    def _recompute_feats_from_jpgs(self):
        """Recompute color feature stats for labels that have hists but no feats."""
        missing = [l for l in self._hists if l not in self._feats]
        updated = []
        for label in missing:
            jpg_path = REFS_DIR / f"{label}.jpg"
            if not jpg_path.exists():
                continue
            try:
                img = cv2.imread(str(jpg_path))
                if img is None:
                    continue
                analysis, _ = self._get_analysis_region(img)
                self._feats[label] = _compute_color_features(analysis)
                updated.append(label)
            except Exception:
                pass
        if updated:
            self._save_refs()
            self.status.log(f"histogram_vision: recomputed color feats for {updated}")

    def _mock_result(self) -> RecognizeResult:
        import random
        label = random.choice(LABELS)
        return RecognizeResult(label=label, confidence=0.5)
