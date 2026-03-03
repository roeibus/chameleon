from honeypot.utils.session_utils import safe_decode

_MAX_CARRY = 4096


class LineBuffer:
    """Accumulates raw bytes and yields complete decoded lines for logging.

    Forwarding to the backend is the caller's responsibility; this class only
    concerns itself with what gets logged and when.
    """

    def __init__(self) -> None:
        self._buf: bytes = b""

    def feed(self, data: bytes) -> list[str]:
        """Add *data* and return any complete lines ready for logging."""
        self._buf += data
        parts = self._buf.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
        self._buf = parts[-1]
        lines = [safe_decode(p).strip() for p in parts[:-1] if p.strip()]
        # Guard against unbounded growth on binary streams with no newlines.
        if len(self._buf) >= _MAX_CARRY:
            overflow = safe_decode(self._buf).strip()
            self._buf = b""
            if overflow:
                lines.append(overflow)
        return lines

    def flush(self) -> str | None:
        """Return any remaining buffered data and reset the buffer."""
        text = safe_decode(self._buf).strip()
        self._buf = b""
        return text or None