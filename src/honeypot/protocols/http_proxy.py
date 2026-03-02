from asyncio import StreamReader, StreamWriter
from typing import override

from honeypot.config import Protocol
from honeypot.core.bridge import SessionBridge


class HttpProxyBridge(SessionBridge):
    @property
    @override
    def protocol(self) -> Protocol:
        return Protocol.HTTP_PROXY

    @override
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        backend = self._backend_factory.create()
        async with backend:
            await self._forward(reader, writer, backend)
