from abc import abstractmethod, ABC
from asyncio import StreamReader, StreamWriter

from honeypot.bridge import BackendSessionBridge


class ContainerSessionBridge(BackendSessionBridge, ABC):
    @abstractmethod
    async def greet(self, reader: StreamReader,
                    writer: StreamWriter) -> None:
        pass

    async def _handle_client(self, reader: StreamReader,
                             writer: StreamWriter) -> None:
        async with self._backend:
            await self.greet(reader, writer)
            await self._forward(reader, writer)
