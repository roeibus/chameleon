import asyncio
from asyncio import StreamWriter, StreamReader
from loguru import logger

from honeypot.containers.container_bridge import ContainerSessionBridge


class TelnetBridge(ContainerSessionBridge):

    @property
    def name(self) -> str:
        return "telnet"

    async def greet(self, reader: StreamReader,
                    writer: StreamWriter) -> None:
        try:
            writer.write(b"Ubuntu 20.04 LTS\r\nlogin: ")
            await writer.drain()
            await reader.readline()  # Username
            writer.write(b"Password: ")
            await writer.drain()
            await reader.readline()  # Password
            await asyncio.sleep(1)
            writer.write(b"\r\nWelcome to Ubuntu.\r\n\r\n")
            await writer.drain()
        except (OSError, EOFError) as e:
            logger.error(f"Connection error: {e}")
