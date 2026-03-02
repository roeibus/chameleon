import logging
import os
import sys
from pathlib import Path
from types import FrameType
from typing import override, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Message


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        return False
    return os.access(path, os.W_OK)


def resolve_log_dir(log_dir: Path | None = None) -> Path:
    if log_dir is not None and _is_writable_dir(log_dir):
        return log_dir

    xdg_state = os.environ.get("XDG_STATE_HOME")
    fallback = (
        Path(xdg_state) / "chameleon"
        if xdg_state
        else Path.home() / ".local" / "state" / "chameleon"
    )
    for candidate in (Path("/var/log"), fallback):
        if _is_writable_dir(candidate):
            return candidate
    return fallback


class InterceptHandler(logging.Handler):
    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _rotate_log_if_needed(log_file: Path, max_bytes: int = 10 * 1024 * 1024) -> None:
    """Rotates the log file if it exceeds the specified size."""
    try:
        if log_file.exists() and log_file.stat().st_size > max_bytes:
            backup = log_file.with_suffix(".log.1")
            log_file.replace(backup)
    except OSError:
        # Failure to rotate shouldn't stop the logging process
        pass


def _get_ip_log_path(log_dir: Path, ip: str) -> Path:
    """Generates a safe log file path for a given IP."""
    safe_ip = ip.replace("/", "_").replace("\\", "_")
    return log_dir / f"{safe_ip}.log"


def _ip_router_sink(message: "Message", log_dir: Path) -> None:
    """Routes logs to IP-specific files with basic rotation."""
    record = message.record
    ip = record["extra"].get("ip")

    if not ip:
        return

    log_file = _get_ip_log_path(log_dir, str(ip))
    _rotate_log_if_needed(log_file)

    with open(log_file, "a", encoding="utf-8") as f:
        _ = f.write(str(message))


def setup_logging(log_dir: Path | None = None) -> None:
    log_dir = resolve_log_dir(log_dir)

    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    logger.remove()

    _ = logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            + "<level>{level: <8}</level> | "
            + "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
            + "<level>{message}</level>"
        ),
        colorize=True,
    )

    _ = logger.add(
        log_dir / "honeypot.log",
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",
        compression="zip",
        enqueue=True,
    )

    _ = logger.add(
        lambda m: _ip_router_sink(m, log_dir),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}",
        filter=lambda r: "ip" in r["extra"],  # specific log file for connected ip
        enqueue=True,
    )
