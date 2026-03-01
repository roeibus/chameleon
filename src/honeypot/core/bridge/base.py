import asyncio
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack

from honeypot.core.backend import BackendFactory

READ_BUFFER_SIZE = 4096
RECV_BUFFER_SIZE = 4096
MAX_OUTPUT_LOG = 100


class ProtocolServer(ABC):
    def __init__(self, backend_factory: BackendFactory, host: str, port: int) -> None:
        self._backend_factory: BackendFactory = backend_factory
        self._host: str = host
        self._port: int = port

    @property
    @abstractmethod
    def protocol(self) -> str: ...

    @abstractmethod
    async def start(self, stack: AsyncExitStack) -> asyncio.Server | None: ...
