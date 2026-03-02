import asyncio
from asyncio import StreamReader, StreamWriter
from typing import override


from honeypot.config import Protocol
from honeypot.core.bridge import SessionBridge
from honeypot.core.bridge.relay import relay
from honeypot.utils import safe_write, log_login_attempt


class TelnetBridge(SessionBridge):

    @property
    @override
    def protocol(self) -> Protocol:
        return Protocol.TELNET

    @override
    async def greet(self, reader: StreamReader, writer: StreamWriter) -> None:
        await safe_write(writer, b"Ubuntu 20.04 LTS\r\nlogin: ")
        username = await reader.readline()
        await safe_write(writer, b"Password: ")
        password = await reader.readline()
        log_login_attempt(username, password)
        await asyncio.sleep(1)
        await safe_write(writer, b"\r\nWelcome to Ubuntu.\r\n\r\n")

    @override
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        backend = self._backend_factory.create()
        async with backend:
            await relay(reader, writer, backend, self.protocol)
