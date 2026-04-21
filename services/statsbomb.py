class StatsBombService:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
    def is_available(self) -> bool:
        return bool(self.enabled)
