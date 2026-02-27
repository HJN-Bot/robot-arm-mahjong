import os
from software.adapters.tts import lines

class LocalPlayerTTS:
    def __init__(self, status_store, assets_dir: str | None = None):
        self.status = status_store
        self.assets_dir = assets_dir or os.path.join(os.path.dirname(__file__), "assets")

    def say(self, line_key: str, style: str = "polite"):
        # Placeholder: tomorrow implement actual playback on mac:
        # - afplay <file.wav>
        # - or play via python library
        self.status.log(f"tts({style}): {line_key}")

    def _resolve_path(self, line_key: str, style: str):
        fname = {
            lines.LOOK_DONE: "look_done.wav",
            lines.I_WANT_CHECK: "i_want_check.wav",
            lines.OK_NO_PROBLEM: "ok_no_problem.wav",
        }.get(line_key, "unknown.wav")
        return os.path.join(self.assets_dir, style, fname)
