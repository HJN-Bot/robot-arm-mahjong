from dataclasses import dataclass, field
from typing import Optional, List
from software.orchestrator.contracts import RecognizeResult

@dataclass
class StatusStore:
    busy: bool = False
    last_scene: Optional[str] = None
    last_error: Optional[str] = None
    last_recognized: Optional[RecognizeResult] = None
    trigger_pending: bool = False   # set by POST /trigger, cleared after frontend reads it
    logs: List[str] = field(default_factory=list)

    def set_busy(self, v: bool):
        self.busy = v

    def log(self, msg: str):
        self.logs.append(msg)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
