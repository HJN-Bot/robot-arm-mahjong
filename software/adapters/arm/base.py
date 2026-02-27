class ArmAdapter:
    def pick_tile(self, safe: bool = True):
        raise NotImplementedError

    def present_to_camera(self, safe: bool = True):
        raise NotImplementedError

    def throw_to_discard(self, safe: bool = True):
        raise NotImplementedError

    def return_tile(self, safe: bool = True):
        raise NotImplementedError

    def home(self):
        raise NotImplementedError

    def estop(self):
        raise NotImplementedError

    def tap(self, times: int = 3):
        raise NotImplementedError

    def nod(self):
        raise NotImplementedError

    def shake(self):
        raise NotImplementedError

    def status(self) -> dict:
        return {}
