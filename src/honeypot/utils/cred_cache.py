class CredCache:
    """Caches the first successful credential per IP and enforces it on repeats."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[str, str]] = {}

    def allows(self, ip: str, username: str, password: str) -> bool:
        """Returns True if the login should be allowed.

        First login from an IP: always allowed; credentials are cached.
        Subsequent logins: only allowed if they match the cached credentials.
        """
        cred = (username, password)
        if ip not in self._cache:
            self._cache[ip] = cred
            return True
        return self._cache[ip] == cred