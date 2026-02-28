from dataclasses import dataclass
from typing import Optional, Literal

SceneName = Literal["A", "B"]
StyleName = Literal["polite", "meme"]

@dataclass
class RecognizeResult:
    label: str                 # e.g. "white_dragon" | "one_dot"
    confidence: float

@dataclass
class RunRequest:
    scene: SceneName
    style: StyleName = "polite"
    safe: bool = True
    # Pre-identified result from frontend; if set, orchestrator skips its own recognize step
    pre_recognized: Optional[RecognizeResult] = None

@dataclass
class RunResult:
    ok: bool
    scene: SceneName
    duration_ms: int
    error_code: Optional[str] = None
    recognized: Optional[RecognizeResult] = None
