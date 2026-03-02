import asyncio
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Protocol

from honeypot.config import Protocol as HoneypotProtocol
from honeypot.core.backend import BackendFactory

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

    @property
    @abstractmethod
    def protocol(self) -> HoneypotProtocol: ...

    @abstractmethod
    async def start(self, stack: AsyncExitStack) -> asyncio.Server | None: ...
