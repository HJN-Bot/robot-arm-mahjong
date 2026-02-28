"""
TTS player — cross-platform.

Priority:
  1. Pre-recorded wav/mp3: assets/<style>/<line>.wav
  2. Dynamic text fallback: espeak (Linux) or macOS `say`
  3. Silent log if no TTS tool is available
"""

import os
import shutil
import subprocess
import sys
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
        """Speak arbitrary text (for dynamic lines)."""
        self.status.log(f"tts(dynamic): {text}")
        self._say_text(text)

    def _resolve_path(self, line_key: str, style: str) -> str:
        fname = L.LINE_WAV.get(line_key, "unknown.wav")
        return os.path.join(self.assets_dir, style, fname)

    def _play_wav(self, path: str):
        # run() blocks until audio finishes — ensures sequential TTS + arm flow
        if sys.platform == "darwin":
            subprocess.run(["afplay", path], check=False)
        elif shutil.which("ffplay"):
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path], check=False)
        elif shutil.which("mpv"):
            subprocess.run(["mpv", "--no-video", path], check=False)
        elif shutil.which("aplay"):
            subprocess.run(["aplay", "-q", path], check=False)
        elif shutil.which("paplay"):
            subprocess.run(["paplay", path], check=False)
        else:
            self.status.log("tts: no audio player found, skipping playback")

    def _say_text(self, text: str, voice: str = "Meijia"):
        if sys.platform == "darwin":
            subprocess.run(["say", "-v", voice, text], check=False)
        elif shutil.which("espeak"):
            subprocess.run(["espeak", text], check=False)
        elif shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", text], check=False)
        else:
            self.status.log(f"tts: no speech tool available, would say: {text}")
