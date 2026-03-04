import asyncio
from asyncio import StreamReader, StreamWriter
from typing import override

from loguru import logger

from honeypot.config import Protocol
from honeypot.core.backend import BackendFactory
from honeypot.core.bridge import SessionBridge
from honeypot.core.bridge.relay import relay
from honeypot.utils import (
    CredCache,
    extract_ip,
    log_login_attempt,
    safe_decode,
    safe_write,
)


class TelnetBridge(SessionBridge):
    def __init__(
        self,
        backend_factory: BackendFactory,
        host: str,
        port: int,
        max_connections: int = 100,
        cred_cache: CredCache | None = None,
    ) -> None:
        super().__init__(backend_factory, host, port, max_connections)
        self._cred_cache: CredCache = cred_cache or CredCache()

    @property
    @override
    def protocol(self) -> Protocol:
        return Protocol.TELNET

    @override
    async def greet(self, reader: StreamReader, writer: StreamWriter) -> bool:
        await safe_write(writer, b"Ubuntu 20.04 LTS\r\nlogin: ")
        username = await reader.readline()
        await safe_write(writer, b"Password: ")
        password = await reader.readline()
        log_login_attempt(username, password)

        await asyncio.sleep(1)

        if not self._cred_cache.allows(
            extract_ip(writer), safe_decode(username), safe_decode(password)
        ):
            logger.info("[~] Credentials rejected for known IP, denying")
            await safe_write(writer, b"\r\nLogin incorrect\r\n")
            return False

        await safe_write(writer, b"\r\nWelcome to Ubuntu.\r\n\r\n")
        return True

    @override
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        backend = self._backend_factory.create()
        async with backend:
            await relay(reader, writer, backend, self.protocol)
