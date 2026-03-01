import asyncio
from asyncio import StreamReader, StreamWriter
from types import TracebackType
from typing import override

from honeypot.core.backend import Backend
from honeypot.core.exceptions import BackendPropertyError
from honeypot.core.metrics import MetricsManager


class StreamBackend(Backend):
    def __init__(self, host: str, port: int, protocol: str = "http_proxy") -> None:
        self._host: str = host
        self._port: int = port
        self._protocol: str = protocol
        self._reader: StreamReader | None = None
        self._writer: StreamWriter | None = None

    @property
    def reader(self) -> StreamReader:
        if self._reader is None:
            raise BackendPropertyError("StreamBackend is not connected")
        return self._reader

    @property
    def writer(self) -> StreamWriter:
        if self._writer is None:
            raise BackendPropertyError("StreamBackend is not connected")
        return self._writer

    @override
    async def __aenter__(self) -> "StreamBackend":
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self._host, self._port
            )
            MetricsManager.set_backend_status(self._protocol, "stream", True)
        except Exception:
            MetricsManager.set_backend_status(self._protocol, "stream", False)
            raise
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        MetricsManager.set_backend_status(self._protocol, "stream", False)
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError:
                pass
        self._reader = None
        self._writer = None

    @override
    async def read(self, size: int) -> bytes:
        return await self.reader.read(size)

    @override
    async def write(self, data: bytes) -> None:
        self.writer.write(data)
        await self.writer.drain()
