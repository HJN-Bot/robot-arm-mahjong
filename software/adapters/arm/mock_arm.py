import time

class MockArm:
    def __init__(self, status_store):
        self.status = status_store

    def pick_tile(self, safe: bool = True):
        time.sleep(0.2 if not safe else 0.4)
        self.status.log("mock_arm: picked")

    def present_to_camera(self, safe: bool = True):
        time.sleep(0.2 if not safe else 0.4)
        self.status.log("mock_arm: presented")

    def throw_to_discard(self, safe: bool = True):
        time.sleep(0.2 if not safe else 0.4)
        self.status.log("mock_arm: threw")

    def return_tile(self, safe: bool = True):
        time.sleep(0.2 if not safe else 0.4)
        self.status.log("mock_arm: returned")

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
