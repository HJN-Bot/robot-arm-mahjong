# Line key constants
LOOK_DONE = "LOOK_DONE"
I_WANT_CHECK = "I_WANT_CHECK"
OK_NO_PROBLEM = "OK_NO_PROBLEM"

# Text content: used as fallback (macOS say) and for edge-tts pre-generation
LINE_TEXT: dict[str, dict[str, str]] = {
    LOOK_DONE: {
        "polite": "好，我看好了。",
        "meme": "哼，给爷看完了。",
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

# Wav filename for each line key (placed under assets/<style>/<filename>)
LINE_WAV: dict[str, str] = {
    LOOK_DONE: "look_done.wav",
    I_WANT_CHECK: "i_want_check.wav",
    OK_NO_PROBLEM: "ok_no_problem.wav",
}
