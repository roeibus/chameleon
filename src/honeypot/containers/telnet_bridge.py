import asyncio
from asyncio import StreamReader, StreamWriter
from typing import override

from loguru import logger

from honeypot.containers.bridge import ContainerSessionBridge


class TelnetBridge(ContainerSessionBridge):
    @property
    def name(self) -> str:
        return "telnet"

    @override
    async def greet(self, reader: StreamReader, writer: StreamWriter) -> None:
        try:
            writer.write(b"Ubuntu 20.04 LTS\r\nlogin: ")
            await writer.drain()
            username = await reader.readline()  # Username
            writer.write(b"Password: ")
            await writer.drain()
            password = await reader.readline()  # Password
            logger.info(
                f"Login attempt: username={username.strip().decode(errors='replace')!r}, password={password.strip().decode(errors='replace')!r}"
            )
            await asyncio.sleep(1)
            writer.write(b"\r\nWelcome to Ubuntu.\r\n\r\n")
            await writer.drain()
        except (OSError, EOFError) as e:
            logger.error(f"Connection error: {e}")
