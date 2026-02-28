"""
Claude Vision tile classifier (zero-shot, no calibration needed).

Sends the tile image to claude-haiku-4-5 via Anthropic API and asks it
to classify the tile as white_dragon or one_dot.

Requires ANTHROPIC_API_KEY in environment (software/.env or system env).
Falls back to mock if the key is missing or the call fails.
"""
import base64
import os
from software.adapters.vision.base import VisionAdapter
from software.orchestrator.contracts import RecognizeResult

LABELS = ["white_dragon", "one_dot"]

_PROMPT = (
    "You are a mahjong tile classifier. "
    "Look at this image and identify which mahjong tile is shown.\n\n"
    "The tile is one of exactly two options:\n"
    "- white_dragon: a completely blank white tile (白板 / Haku)\n"
    "- one_dot: a tile showing a single circle/dot (一筒 / 一饼)\n\n"
    "Reply with ONLY one of these two exact strings, nothing else:\n"
    "white_dragon\n"
    "one_dot"
)


class ClaudeVision(VisionAdapter):
    """
    Zero-shot classifier using Claude claude-haiku-4-5.
    No calibration required — works out of the box with ANTHROPIC_API_KEY.
    """

    def __init__(self, status_store):
        self.status = status_store
        self._client = None
        self._ready = False
        self._init_client()

    def _init_client(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            self.status.log("claude_vision: ANTHROPIC_API_KEY not set — will use mock fallback")
            return
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            self._ready = True
            self.status.log("claude_vision: ready (claude-haiku-4-5)")
        except ImportError:
            self.status.log("claude_vision: anthropic package not installed — run: pip install anthropic")

    def identify(self, image_bytes: bytes) -> RecognizeResult:
        if not self._ready or self._client is None:
            self.status.log("claude_vision: not ready, using mock fallback")
            return self._mock_result()

        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        try:
            message = self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=16,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": _PROMPT},
                        ],
                    }
                ],
            )
            raw = message.content[0].text.strip().lower()
            self.status.log(f"claude_vision: raw response = '{raw}'")

            label = self._parse_label(raw)
            if label is None:
                self.status.log(f"claude_vision: unexpected response '{raw}', using mock fallback")
                return self._mock_result()

            self.status.log(f"claude_vision: → {label} (conf=0.95)")
            return RecognizeResult(label=label, confidence=0.95)

        except Exception as e:
            self.status.log(f"claude_vision: API error: {e}")
            return self._mock_result()

    def _parse_label(self, raw: str) -> str | None:
        for label in LABELS:
            if label in raw:
                return label
        return None

    def recognize_once(self) -> RecognizeResult:
        """Orchestrator fallback — no image available."""
        return self._mock_result()

    def _mock_result(self) -> RecognizeResult:
        import random
        return RecognizeResult(label=random.choice(LABELS), confidence=0.5)
