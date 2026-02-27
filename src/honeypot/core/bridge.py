from abc import ABC, abstractmethod
from asyncio import StreamReader, StreamWriter

from loguru import logger

from honeypot.core.backend import Backend
from honeypot.utils import RaceGroup

READ_BUFFER_SIZE = 4096
RECV_BUFFER_SIZE = 4096
MAX_OUTPUT_LOG = 100


class SessionBridge(ABC):
    def __init__(self, backend: Backend) -> None:
        self._backend: Backend = backend

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    async def greet(self, reader: StreamReader, writer: StreamWriter) -> None:
        pass

    @abstractmethod
    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        pass

    async def handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        peername = writer.get_extra_info("peername")
        ip: str = peername[0] if peername else "UNKNOWN"
        with logger.contextualize(ip=ip, bridge=self.name):
            logger.info("[+] New client detected")
            try:
                await self._handle_client(reader, writer)
            except (OSError, EOFError) as e:
                logger.error(f"Bridge error: {e}")
            finally:
                logger.info("[-] Connection closed")
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass

    async def _forward(self, reader: StreamReader, writer: StreamWriter) -> None:
        async with RaceGroup() as rg:
            rg.create_task(self.forward_input(reader))
            rg.create_task(self.forward_output(writer))

    async def forward_input(self, reader: StreamReader) -> None:
        while True:
            data = await reader.read(READ_BUFFER_SIZE)
            if not data:
                break
            logger.info(f"CMD: {data.decode(errors='replace').strip() or repr(data)}")
            await self._backend.write(data)

    async def forward_output(self, writer: StreamWriter) -> None:
        while True:
            data = await self._backend.read(RECV_BUFFER_SIZE)
            if not data:
                break
            logger.debug(f"Output: {data.decode(errors='replace')[:MAX_OUTPUT_LOG]}")
            writer.write(data)
            await writer.drain()
