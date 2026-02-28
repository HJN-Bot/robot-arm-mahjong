"""
KIMI (Moonshot AI) Vision tile classifier.
Uses KIMI's OpenAI-compatible API with multimodal support.
Requires KIMI_API_KEY in software/.env.

No extra dependencies — uses httpx which is already in requirements.txt.
"""
import base64
import os
import httpx
from software.adapters.vision.base import VisionAdapter
from software.orchestrator.contracts import RecognizeResult

LABELS = ["white_dragon", "one_dot"]

_PROMPT = (
    "你是一个麻将牌识别系统。机械臂正在将一张麻将牌举到摄像头前，请识别牌面花色。\n\n"
    "牌只有两种可能：\n"
    "- white_dragon：纯白色的空白方块牌，牌面没有任何图案（白板/发/Haku）\n"
    "- one_dot：牌面中央有一个绿色或彩色圆圈的牌（一筒/一饼/1-circle）\n\n"
    "注意：图片可能有手指、机械臂或背景，请只关注牌面本身。\n\n"
    "只回复以下两个字符串之一，不要有任何其他内容：\n"
    "white_dragon\n"
    "one_dot"
)

KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL   = os.getenv("KIMI_MODEL", "moonshot-v1-8k-vision-preview")


class KimiVision(VisionAdapter):
    def __init__(self, status_store):
        self.status = status_store
        self._api_key = os.getenv("KIMI_API_KEY")
        self._ready   = bool(self._api_key)
        if self._ready:
            self.status.log(f"kimi_vision: ready (model={KIMI_MODEL})")
        else:
            self.status.log("kimi_vision: KIMI_API_KEY not set")

    def identify(self, image_bytes: bytes) -> RecognizeResult:
        if not self._ready:
            return self._mock_result()

        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        payload = {
            "model": KIMI_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "auto",  # auto: 让 KIMI 自动选分辨率，准确率 > 速度
                            },
                        },
                        {"type": "text", "text": _PROMPT},
                    ],
                }
            ],
            "max_tokens": 16,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = httpx.post(KIMI_API_URL, json=payload, headers=headers, timeout=15.0)
            if not resp.is_success:
                self.status.log(f"kimi_vision: HTTP {resp.status_code} — {resp.text[:300]}")
                return self._mock_result()
            raw = resp.json()["choices"][0]["message"]["content"].strip().lower()
            self.status.log(f"kimi_vision: raw='{raw}'")

            label = self._parse_label(raw)
            if label is None:
                self.status.log(f"kimi_vision: unexpected response '{raw}', mock fallback")
                return self._mock_result()

            self.status.log(f"kimi_vision: → {label} (conf=0.95)")
            return RecognizeResult(label=label, confidence=0.95)

        except Exception as e:
            self.status.log(f"kimi_vision: API error: {e}")
            return self._mock_result()

    def _parse_label(self, raw: str) -> str | None:
        for label in LABELS:
            if label in raw:
                return label
        return None

    def recognize_once(self) -> RecognizeResult:
        return self._mock_result()

    def _mock_result(self) -> RecognizeResult:
        import random
        return RecognizeResult(label=random.choice(LABELS), confidence=0.5)
