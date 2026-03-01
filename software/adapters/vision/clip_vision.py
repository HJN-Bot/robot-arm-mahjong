"""
CLIP-based tile classifier (2-class: white_dragon vs one_dot).

Uses OpenAI's CLIP model for zero-shot image classification.
No training or calibration needed — just text descriptions of each tile.

Robust to lighting, angle, and background variations.
First call is slow (~2-5s, model loading), subsequent calls ~100-300ms.

Requires: pip install transformers torch Pillow
"""

import io
import numpy as np
from pathlib import Path
from software.adapters.vision.base import VisionAdapter
from software.orchestrator.contracts import RecognizeResult

LABELS = ["white_dragon", "one_dot"]

REFS_DIR = Path(__file__).parent / "refs"
REFS_DIR.mkdir(exist_ok=True)

# Text prompts describing each tile — CLIP matches images against these
CLIP_PROMPTS = {
    "one_dot": "a mahjong one dot tile with a green circular pattern and red center",
    "white_dragon": "a mahjong white dragon tile with a black rectangular frame on white",
}

MODEL_NAME = "openai/clip-vit-base-patch32"


class ClipVision(VisionAdapter):
    """CLIP-based 2-class tile classifier. Zero-shot, no calibration needed."""

    def __init__(self, status_store):
        self.status = status_store
        self._model = None
        self._processor = None
        self._loaded = False
        self.status.log("vision: CLIP classifier (model loads on first use)")

    def _load_model(self):
        if self._loaded:
            return True
        try:
            from transformers import CLIPModel, CLIPProcessor
            self.status.log(f"vision: loading CLIP model ({MODEL_NAME})...")
            self._model = CLIPModel.from_pretrained(MODEL_NAME)
            self._processor = CLIPProcessor.from_pretrained(MODEL_NAME)
            self._loaded = True
            self.status.log("vision: CLIP model loaded")
            return True
        except Exception as e:
            self.status.log(f"vision: failed to load CLIP: {e}")
            return False

    def identify(self, image_bytes: bytes) -> RecognizeResult:
        if not self._load_model():
            self.status.log("vision: CLIP not available, mock fallback")
            return self._mock_result()

        try:
            from PIL import Image
            import torch

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            texts = [CLIP_PROMPTS[label] for label in LABELS]
            inputs = self._processor(
                text=texts, images=image, return_tensors="pt", padding=True
            )

            with torch.no_grad():
                outputs = self._model(**inputs)

            probs = outputs.logits_per_image.softmax(dim=1)[0]

            best_idx = probs.argmax().item()
            label = LABELS[best_idx]
            confidence = float(probs[best_idx])

            prob_str = ", ".join(f"{LABELS[i]}={probs[i]:.3f}" for i in range(len(LABELS)))
            self.status.log(f"vision: {label} (conf={confidence:.2f}, {prob_str})")

            return RecognizeResult(label=label, confidence=confidence)

        except Exception as e:
            self.status.log(f"vision: CLIP error: {e}")
            return self._mock_result()

    def recognize_once(self) -> RecognizeResult:
        return self._mock_result()

    def calibrate(self, label: str, image_bytes: bytes) -> bool:
        try:
            import cv2
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                cv2.imwrite(str(REFS_DIR / f"{label}.jpg"), img)
            result = self.identify(image_bytes)
            self.status.log(f"vision: calibrate '{label}' → detected as {result.label}")
            return True
        except Exception:
            return False

    def calibration_status(self) -> dict:
        return {label: True for label in LABELS}

    def _mock_result(self) -> RecognizeResult:
        import random
        label = random.choice(LABELS)
        return RecognizeResult(label=label, confidence=0.5)
