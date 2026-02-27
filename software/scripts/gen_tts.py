"""
Pre-generate all voice pack wav files using edge-tts.

Usage:
    pip install edge-tts
    python -m software.scripts.gen_tts

Output:
    software/adapters/tts/assets/polite/*.wav
    software/adapters/tts/assets/meme/*.wav

Voice used: zh-CN-XiaoxiaoNeural (female, warm, natural Chinese)
Alternative: zh-CN-YunxiNeural (male)
"""

import asyncio
import os
import edge_tts
from software.adapters.tts.lines import LINE_TEXT, LINE_WAV

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "adapters", "tts", "assets")

VOICE_MAP = {
    "polite": "zh-CN-XiaoxiaoNeural",
    "meme": "zh-CN-YunxiNeural",
}


async def generate_line(line_key: str, style: str, text: str, voice: str):
    out_dir = os.path.join(ASSETS_DIR, style)
    os.makedirs(out_dir, exist_ok=True)
    wav_name = LINE_WAV.get(line_key, f"{line_key.lower()}.wav")
    out_path = os.path.join(out_dir, wav_name)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)
    print(f"  [{style}] {line_key} -> {wav_name}")


async def main():
    print("Generating voice packs...")
    tasks = []
    for line_key, styles in LINE_TEXT.items():
        for style, text in styles.items():
            voice = VOICE_MAP.get(style, VOICE_MAP["polite"])
            tasks.append(generate_line(line_key, style, text, voice))
    await asyncio.gather(*tasks)
    print("Done. Files saved to adapters/tts/assets/")


if __name__ == "__main__":
    asyncio.run(main())
