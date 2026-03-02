import asyncio
from abc import ABC, abstractmethod
from asyncio import StreamReader, StreamWriter
from contextlib import AsyncExitStack
from typing import override

from loguru import logger

from honeypot.core.backend import Backend, BackendFactory
from honeypot.core.bridge.base import (
    MAX_OUTPUT_LOG,
    READ_BUFFER_SIZE,
    RECV_BUFFER_SIZE,
    ProtocolServer,
)
from honeypot.core.metrics import MetricsManager
from honeypot.utils import RaceGroup, extract_ip


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
                writer.close()
                return

            logger.info("[+] New client detected")
            MetricsManager.record_connection(self.protocol)
            try:
                await self._handle_client(reader, writer)
            except (OSError, EOFError) as e:
                logger.error(f"Bridge error: {e}")
            finally:
                self._sem.release()
                logger.info("[-] Connection closed")
                MetricsManager.record_disconnection(self.protocol)
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass

    @override
    async def start(self, stack: AsyncExitStack) -> asyncio.Server:
        server = await asyncio.start_server(self.handle_client, self._host, self._port)
        await stack.enter_async_context(server)
        addr = server.sockets[0].getsockname()
        logger.info(f"[*] {self.__class__.__name__} listening on {addr}")
        return server

    async def _forward(
        self, reader: StreamReader, writer: StreamWriter, backend: Backend
    ) -> None:
        async with RaceGroup() as rg:
            rg.append_task(self.forward_input(reader, backend))
            rg.append_task(self.forward_output(writer, backend))

    async def forward_input(self, reader: StreamReader, backend: Backend) -> None:
        while True:
            data = await reader.read(READ_BUFFER_SIZE)
            if not data:
                break
            logger.info(f"CMD: {data.decode(errors='replace').strip() or repr(data)}")
            MetricsManager.record_bytes(self.protocol, "tx", len(data))
            await backend.write(data)

    async def forward_output(self, writer: StreamWriter, backend: Backend) -> None:
        while True:
            data = await backend.read(RECV_BUFFER_SIZE)
            if not data:
                break
            logger.debug(f"Output: {data.decode(errors='replace')[:MAX_OUTPUT_LOG]}")
            MetricsManager.record_bytes(self.protocol, "rx", len(data))
            writer.write(data)
            await writer.drain()
