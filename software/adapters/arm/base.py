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

    def status(self) -> dict:
        return {}
