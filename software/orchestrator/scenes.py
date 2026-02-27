from typing import Literal

SceneName = Literal["A", "B"]

SCENE_A = "A"  # throw away
SCENE_B = "B"  # return back

# Scene semantics:
# A: pick -> present -> recognize -> tts -> throw
# B: pick -> present -> recognize -> tts -> return
