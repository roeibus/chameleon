import logging
import sys
from pathlib import Path
from types import FrameType
from loguru import logger

LOG_DIR = Path("/var/log/")
LOG_DIR.mkdir(exist_ok=True)


class InterceptHandler(logging.Handler):
    def emit(self, record):
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


def router_sink(message):
    record = message.record
    ip = record["extra"].get("ip")

    if ip:
        safe_ip = str(ip).replace("/", "_").replace("\\", "_")
        log_file = LOG_DIR / f"{safe_ip}.log"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(message)


def setup_logging():
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    logger.remove()

    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
               "<level>{message}</level>",
        colorize=True
    )

    logger.add(
        f"{LOG_DIR}/honeypot.log",
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",
        compression="zip",
        enqueue=True
    )

    logger.add(
        router_sink,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}",
        filter=lambda r: "ip" in r["extra"],  # specific log file for connected ip
        enqueue=True
    )
