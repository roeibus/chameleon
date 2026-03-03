from loguru import logger

from honeypot.config import Protocol
from honeypot.core.backend import Backend
from honeypot.core.bridge.base import (
    MAX_OUTPUT_LOG,
    READ_BUFFER_SIZE,
    RECV_BUFFER_SIZE,
    AsyncReader,
    AsyncWriter,
)
from honeypot.core.metrics import MetricsManager
from honeypot.utils import LineBuffer, RaceGroup, safe_decode


async def forward_input(
    reader: AsyncReader, backend: Backend, protocol: Protocol
) -> None:
    buf = LineBuffer()
    while True:
        data = await reader.read(n=READ_BUFFER_SIZE)
        if not data:
            if remaining := buf.flush():
                logger.info(f"→ {remaining}")
            break
        MetricsManager.record_bytes(protocol, "tx", len(data))
        await backend.write(data)
        for line in buf.feed(data):
            logger.info(f"→ {line}")


async def forward_output(
    writer: AsyncWriter, backend: Backend, protocol: Protocol
) -> None:
    while True:
        data = await backend.read(RECV_BUFFER_SIZE)
        if not data:
            break
        text = safe_decode(data, limit=MAX_OUTPUT_LOG).rstrip()
        if text:
            logger.debug(f"← {text}")
        MetricsManager.record_bytes(protocol, "rx", len(data))
        writer.write(data)
        await writer.drain()


async def relay(
    reader: AsyncReader,
    writer: AsyncWriter,
    backend: Backend,
    protocol: Protocol,
) -> None:
    async with RaceGroup() as rg:
        rg.append_task(forward_input(reader, backend, protocol))
        rg.append_task(forward_output(writer, backend, protocol))