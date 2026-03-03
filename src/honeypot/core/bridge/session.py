import asyncio
from abc import ABC, abstractmethod
from asyncio import StreamReader, StreamWriter
from contextlib import AsyncExitStack
from typing import override

from loguru import logger

from honeypot.core.bridge.base import ProtocolServer
from honeypot.utils import extract_ip, close_writer


class SessionBridge(ProtocolServer, ABC):
    async def greet(self, _reader: StreamReader, _writer: StreamWriter) -> bool:
        return True

    @abstractmethod
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        pass

    async def handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        ip = extract_ip(writer)
        with logger.contextualize(ip=ip, bridge=self.__class__.__name__):
            if not await self._try_acquire():
                await close_writer(writer)
                return
            try:
                await self._run_session(reader, writer)
            finally:
                self._release()
                await close_writer(writer)

    async def _run_session(self, reader: StreamReader, writer: StreamWriter) -> None:
        logger.info("[+] New client detected")
        try:
            if await self.greet(reader, writer):
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
