import asyncio
from abc import ABC, abstractmethod
from asyncio import StreamReader, StreamWriter
from contextlib import AsyncExitStack
from typing import override

from loguru import logger

from honeypot.core.backend import BackendFactory
from honeypot.core.bridge.base import ProtocolServer
from honeypot.core.metrics import MetricsManager
from honeypot.utils import extract_ip, close_writer


class SessionBridge(ProtocolServer, ABC):
    def __init__(
        self,
        backend_factory: BackendFactory,
        host: str,
        port: int,
        max_connections: int = 100,
    ) -> None:
        super().__init__(backend_factory, host, port, max_connections)
        self._sem: asyncio.Semaphore = asyncio.Semaphore(max_connections)

    async def greet(self, _reader: StreamReader, _writer: StreamWriter) -> None:
        pass

    @abstractmethod
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        pass

    async def handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        ip = extract_ip(writer)
        with logger.contextualize(ip=ip, bridge=self.__class__.__name__):
            try:
                async with asyncio.timeout(0):
                    await self._sem.acquire()
            except TimeoutError:
                logger.warning("[!] Connection limit reached, rejecting")
                MetricsManager.record_rejected_connection(self.protocol)
                await close_writer(writer)
                return

            MetricsManager.record_connection(self.protocol)
            try:
                await self._run_session(reader, writer)
            finally:
                self._sem.release()
                MetricsManager.record_disconnection(self.protocol)
                await close_writer(writer)

    async def _run_session(self, reader: StreamReader, writer: StreamWriter) -> None:
        logger.info("[+] New client detected")
        try:
            await self.greet(reader, writer)
            await self._handle_client(reader, writer)
        except (OSError, EOFError) as e:
            logger.error(f"Bridge error: {e}")
        finally:
            logger.info("[-] Connection closed")

    @override
    async def start(self, stack: AsyncExitStack) -> asyncio.Server:
        server = await asyncio.start_server(self.handle_client, self._host, self._port)
        await stack.enter_async_context(server)
        addr = server.sockets[0].getsockname()
        logger.info(f"[*] {self.__class__.__name__} listening on {addr}")
        return server
