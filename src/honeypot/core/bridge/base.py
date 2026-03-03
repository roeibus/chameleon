import asyncio
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Protocol

from loguru import logger

from honeypot.config import Protocol as HoneypotProtocol
from honeypot.core.backend import BackendFactory
from honeypot.core.metrics import MetricsManager

READ_BUFFER_SIZE = 4096
RECV_BUFFER_SIZE = 4096
MAX_OUTPUT_LOG = 100


class AsyncReader(Protocol):
    async def read(self, n: int) -> bytes: ...


class AsyncWriter(Protocol):
    def write(self, data: bytes) -> None: ...
    async def drain(self) -> None: ...


class ProtocolServer(ABC):
    def __init__(
        self,
        backend_factory: BackendFactory,
        host: str,
        port: int,
        max_connections: int = 100,
    ) -> None:
        self._backend_factory: BackendFactory = backend_factory
        self._host: str = host
        self._port: int = port
        self._max_connections: int = max_connections
        self._sem: asyncio.Semaphore = asyncio.Semaphore(max_connections)

    @property
    @abstractmethod
    def protocol(self) -> HoneypotProtocol: ...

    @abstractmethod
    async def start(self, stack: AsyncExitStack) -> asyncio.Server | None: ...

    async def _try_acquire(self) -> bool:
        """Acquire a connection slot. Returns False if at capacity."""
        try:
            async with asyncio.timeout(0):
                await self._sem.acquire()
            MetricsManager.record_connection(self.protocol)
            return True
        except TimeoutError:
            logger.warning("[!] Connection limit reached, rejecting")
            MetricsManager.record_rejected_connection(self.protocol)
            return False

    def _release(self) -> None:
        self._sem.release()
        MetricsManager.record_disconnection(self.protocol)
