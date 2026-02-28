import time

# Simulated arm durations — keep these fast for mock testing
# When real arm is connected, replace MockArm with the real HTTP adapter
_PICK_S    = 0.5   # pick tile
_PRESENT_S = 1.0   # present to camera + hold steady
_THROW_S   = 2.0   # throw to discard
_RETURN_S  = 2.0   # return tile

class MockArm:
    def __init__(self, status_store):
        self.status = status_store

    def pick_tile(self, safe: bool = True):
        self.status.log(f"mock_arm: picking tile ({_PICK_S}s)...")
        time.sleep(_PICK_S)
        self.status.log("mock_arm: picked ✓")

    def present_to_camera(self, safe: bool = True):
        self.status.log(f"mock_arm: presenting to camera ({_PRESENT_S}s)...")
        time.sleep(_PRESENT_S)
        self.status.log("mock_arm: presented ✓")

    def throw_to_discard(self, safe: bool = True):
        self.status.log(f"mock_arm: throwing to discard ({_THROW_S}s)...")
        time.sleep(_THROW_S)
        self.status.log("mock_arm: threw ✓")

    def return_tile(self, safe: bool = True):
        self.status.log(f"mock_arm: returning tile ({_RETURN_S}s)...")
        time.sleep(_RETURN_S)
        self.status.log("mock_arm: returned ✓")

    def home(self):
        self.status.log("mock_arm: home")

    def estop(self):
        self.status.log("mock_arm: estop")

    def tap(self, times: int = 3):
        time.sleep(0.1 * times)
        self.status.log(f"mock_arm: tap x{times}")

    def nod(self):
        time.sleep(0.4)
        self.status.log("mock_arm: nod")

    def shake(self):
        time.sleep(0.4)
        self.status.log("mock_arm: shake")
