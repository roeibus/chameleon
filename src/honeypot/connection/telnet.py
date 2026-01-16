import asyncio
import logging
from asyncio import StreamWriter, StreamReader

from honeypot.client import ContainerSessionBridge

logger = logging.getLogger(__name__)


class TelnetBridge(ContainerSessionBridge):

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
        except Exception as e:
            logger.error(f"Connection error: {e}")
