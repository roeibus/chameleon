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
from honeypot.utils import RaceGroup, safe_decode


async def forward_input(
    reader: AsyncReader, backend: Backend, protocol: Protocol
) -> None:
    while True:
        data = await reader.read(n=READ_BUFFER_SIZE)
        if not data:
            break
        logger.info(f"CMD: {safe_decode(data) or repr(data)}")
        MetricsManager.record_bytes(protocol, "tx", len(data))
        await backend.write(data)


async def forward_output(
    writer: AsyncWriter, backend: Backend, protocol: Protocol
) -> None:
    while True:
        data = await backend.read(RECV_BUFFER_SIZE)
        if not data:
            break
        logger.debug(f"Output: {safe_decode(data, limit=MAX_OUTPUT_LOG)}")
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

