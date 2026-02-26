from abc import ABC, abstractmethod
from asyncio import StreamReader, StreamWriter
from typing import override

from honeypot.bridge import SessionBridge


class ContainerSessionBridge(SessionBridge, ABC):
    @abstractmethod
    async def greet(self, reader: StreamReader, writer: StreamWriter) -> None:
        pass

    @override
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        async with self._backend:
            await self.greet(reader, writer)
            await self._forward(reader, writer)
