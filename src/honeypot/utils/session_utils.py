from asyncio import StreamWriter

from loguru import logger


async def close_writer(writer: StreamWriter) -> None:
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass


async def safe_write(writer: StreamWriter, data: bytes) -> None:
    """Write data and drain the writer."""
    writer.write(data)
    await writer.drain()


def safe_decode(data: bytes, limit: int | None = None) -> str:
    """Safely decode bytes to string for logging, replacing errors.

    Normalises ``\\r\\n`` and bare ``\\r`` to ``\\n`` so log output is
    readable regardless of the wire line-ending convention.
    """
    decoded = data.decode(errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    if limit:
        return decoded[:limit]
    return decoded


def log_login_attempt(username: str | bytes, password: str | bytes) -> None:
    """Log a login attempt with username and password."""
    u = (
        safe_decode(username).strip()
        if isinstance(username, bytes)
        else str(username).strip()
    )
    p = (
        safe_decode(password).strip()
        if isinstance(password, bytes)
        else str(password).strip()
    )
    logger.info(f"Login attempt: username={u!r}, password={p!r}")
