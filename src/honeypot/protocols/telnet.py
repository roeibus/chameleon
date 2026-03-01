import asyncio
from asyncio import StreamReader, StreamWriter
from typing import override

from loguru import logger

from honeypot.core.bridge import SessionBridge


class TelnetBridge(SessionBridge):
    @override
    async def greet(self, reader: StreamReader, writer: StreamWriter) -> None:
        writer.write(b"Ubuntu 20.04 LTS\r\nlogin: ")
        await writer.drain()
        username = await reader.readline()
        writer.write(b"Password: ")
        await writer.drain()
        password = await reader.readline()
        logger.info(
            "Login attempt: "
            + f"username={username.strip().decode(errors='replace')!r}, "
            + f"password={password.strip().decode(errors='replace')!r}"
        )
        await asyncio.sleep(1)
        writer.write(b"\r\nWelcome to Ubuntu.\r\n\r\n")
        await writer.drain()

    @override
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        await self.greet(reader, writer)
        backend = self._backend_factory.create()
        async with backend:
            await self._forward(reader, writer, backend)
