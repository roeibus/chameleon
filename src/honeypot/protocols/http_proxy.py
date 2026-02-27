from asyncio import StreamReader, StreamWriter
from typing import override

from honeypot.core.bridge import SessionBridge


class HttpProxyBridge(SessionBridge):
    @override
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        async with self._backend:
            await self._forward(reader, writer)
