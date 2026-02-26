from abc import ABC
from asyncio import StreamReader, StreamWriter
from typing import override

from honeypot.bridge import SessionBridge


class ProxySessionBridge(SessionBridge, ABC):
    """
        For future https/other proxy common code.
    """
    @override
    async def _handle_client(self, reader: StreamReader,
                             writer: StreamWriter) -> None:
        async with self._backend:
            await self._forward(reader, writer)
