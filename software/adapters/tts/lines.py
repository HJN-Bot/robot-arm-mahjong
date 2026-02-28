# Line key constants
SCENE_START = "SCENE_START"      # plays at the very start of every scene
I_WANT_CHECK = "I_WANT_CHECK"    # Scene A closing (throw / discard)
OK_NO_PROBLEM = "OK_NO_PROBLEM"  # Scene B closing (return / keep)

# Text content: fallback text when the audio file is missing (macOS say)
LINE_TEXT: dict[str, dict[str, str]] = {
    SCENE_START: {
        "polite": "来！开牌。",
        "meme": "来！开牌！",
    },
    I_WANT_CHECK: {
        "polite": "我要验牌。",
        "meme": "叫验牌！",
    },
    OK_NO_PROBLEM: {
        "polite": "牌没有问题。",
        "meme": "还得练啊。",
    },
}

# Audio file for each line key (placed under assets/<style>/<filename>)
# afplay supports both .wav and .mp3
LINE_WAV: dict[str, str] = {
    SCENE_START: "来！开牌.mp3",
    I_WANT_CHECK: "我要验牌.mp3",
    OK_NO_PROBLEM: "牌没有问题.mp3",
}
