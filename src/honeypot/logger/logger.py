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
    for candidate in (Path("/var/log/chameleon"), fallback):
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


def _get_ip_log_path(log_dir: Path, ip: str) -> Path:
    safe_ip = ip.replace("/", "_").replace("\\", "_")
    return log_dir / f"{safe_ip}.log"


class IpSinkRouter:
    """Loguru sink that lazily creates and caches a dedicated per-IP file sink."""

    def __init__(self, log_dir: Path) -> None:
        self._log_dir: Path = log_dir
        self._handlers: dict[str, int] = {}

    def __call__(self, message: "Message") -> None:
        ip = message.record["extra"].get("ip")
        if ip:
            self._ensure_sink(str(ip))

    def _ensure_sink(self, ip: str) -> None:
        if ip in self._handlers:
            return
        handler_id = logger.add(
            _get_ip_log_path(self._log_dir, ip),
            rotation="10 MB",
            retention="10 days",
            compression="zip",
            enqueue=True,
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                + "<level>{level: <8}</level> | "
                + "<cyan>{name}</cyan> | "
                + "<level>{message}</level>"
            ),
            filter=lambda r, _ip=ip: r["extra"].get("ip") == _ip,
        )
        self._handlers[ip] = handler_id


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
        log_dir / "chameleon.log",
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",
        compression="zip",
        enqueue=True,
    )

    _ = logger.add(
        IpSinkRouter(log_dir),
        filter=lambda r: "ip" in r["extra"],
        enqueue=True,
    )
