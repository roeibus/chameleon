from abc import ABC
from asyncio import StreamReader, StreamWriter

from honeypot.bridge import BackendSessionBridge


class ProxySessionBridge(BackendSessionBridge, ABC):
    """
        For future https/other proxy common code.
    """
    async def _handle_client(self, reader: StreamReader,
                             writer: StreamWriter) -> None:
        async with self._backend:
            await self._forward(reader, writer)
