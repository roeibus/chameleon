class CredCache:
    """Tracks (ip, username, password) tuples seen across sessions."""

    def __init__(self) -> None:
        self._seen: dict[str, set[tuple[str, str]]] = {}

    def is_new(self, ip: str, username: str, password: str) -> bool:
        """Returns True and records the cred if unseen; False if already seen."""
        cred = (username, password)
        seen = self._seen.setdefault(ip, set())
        if cred in seen:
            return False
        seen.add(cred)
        return True