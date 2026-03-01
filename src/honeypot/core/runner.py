import asyncio
from contextlib import AsyncExitStack

from honeypot.core.bridge import ProtocolServer


class HoneypotRunner:
    def __init__(self, servers: list[ProtocolServer]) -> None:
        self._servers: list[ProtocolServer] = servers

    async def run(self) -> None:
        async with AsyncExitStack() as stack:
            asyncio_servers: list[asyncio.Server] = [
                s for srv in self._servers if (s := await srv.start(stack)) is not None
            ]
            if asyncio_servers:
                await asyncio.gather(*(s.serve_forever() for s in asyncio_servers))
            else:
                await asyncio.Event().wait()
