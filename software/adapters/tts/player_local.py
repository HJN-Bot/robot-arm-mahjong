"""
TTS player for macOS.

Priority:
  1. Pre-recorded wav: assets/<style>/<line>.wav  -> afplay (no deps)
  2. Dynamic text fallback: macOS `say` command
"""

import os
import subprocess
from software.adapters.tts import lines as L


class LocalPlayerTTS:
    def __init__(self, status_store, assets_dir: str | None = None):
        self.status = status_store
        self.assets_dir = assets_dir or os.path.join(os.path.dirname(__file__), "assets")

    def say(self, line_key: str, style: str = "polite"):
        wav_path = self._resolve_path(line_key, style)
        if os.path.isfile(wav_path):
            self.status.log(f"tts({style}): playing {os.path.basename(wav_path)}")
            self._play_wav(wav_path)
        else:
            text = L.LINE_TEXT.get(line_key, {}).get(style) or L.LINE_TEXT.get(line_key, {}).get("polite", line_key)
            self.status.log(f"tts({style}): say fallback -> {text}")
            self._say_text(text)

    def say_text(self, text: str):
        """Speak arbitrary text via macOS say (for dynamic lines)."""
        self.status.log(f"tts(dynamic): {text}")
        self._say_text(text)

    def _resolve_path(self, line_key: str, style: str) -> str:
        fname = L.LINE_WAV.get(line_key, "unknown.wav")
        return os.path.join(self.assets_dir, style, fname)

    def _play_wav(self, path: str):
        subprocess.Popen(["afplay", path])

    def _say_text(self, text: str, voice: str = "Meijia"):
        # Meijia is a high-quality Mandarin voice bundled with macOS
        subprocess.Popen(["say", "-v", voice, text])
