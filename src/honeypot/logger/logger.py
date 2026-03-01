import logging
import os
import sys
from pathlib import Path
from types import FrameType
from typing import override

from loguru import Message, logger


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


def setup_logging(log_dir: Path) -> None:
    def router_sink(message: Message) -> None:
        record = message.record
        ip = record["extra"].get("ip")

        if ip:
            safe_ip = str(ip).replace("/", "_").replace("\\", "_")
            log_file = log_dir / f"{safe_ip}.log"

            with open(log_file, "a", encoding="utf-8") as f:
                _ = f.write(message)

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
        router_sink,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}",
        filter=lambda r: "ip" in r["extra"],  # specific log file for connected ip
        enqueue=True,
    )
