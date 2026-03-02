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
    """Safely decode bytes to string for logging, replacing errors."""
    decoded = data.decode(errors="replace").strip()
    if limit:
        return decoded[:limit]
    return decoded


def log_login_attempt(username: str | bytes, password: str | bytes) -> None:
    """Log a login attempt with username and password."""
    u = safe_decode(username) if isinstance(username, bytes) else username
    p = safe_decode(password) if isinstance(password, bytes) else password
    logger.info(f"Login attempt: username={u!r}, password={p!r}")