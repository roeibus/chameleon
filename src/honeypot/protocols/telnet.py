import asyncio
from asyncio import StreamReader, StreamWriter
from typing import override

from loguru import logger

from honeypot.core.bridge import SessionBridge


class TelnetBridge(SessionBridge):
    @property
    @override
    def name(self) -> str:
        return "telnet"

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
        async with self._backend:
            await self.greet(reader, writer)
            await self._forward(reader, writer)
