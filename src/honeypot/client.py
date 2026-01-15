import asyncio
import logging
from abc import abstractmethod, ABC
from asyncio import AbstractEventLoop, StreamReader, StreamWriter
from functools import cached_property

from honeypot.container import HoneypotContainer

RECV_BUFFER_SIZE = 1024
READ_BUFFER_SIZE = 1024

logger = logging.getLogger(__name__)


class SessionBridge(ABC):
    def __init__(self, container: HoneypotContainer) -> None:
        self._container = container

    @cached_property
    def container_socket(self):
        params = {'stdin': 1, 'stdout': 1, 'stderr': 1, 'stream': 1}
        return self._container.attach_socket(**params)._sock

    @abstractmethod
    async def greet(self, writer: StreamWriter) -> None:
        pass

    async def handle_client(self, reader: StreamReader,
                            writer: StreamWriter) -> None:
        addr: tuple = writer.get_extra_info('peername')

        try:
            await self.greet(writer)
            await asyncio.to_thread(self._container.setup)
            loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
            await asyncio.gather(self.forward_input(reader, loop),
                                 self.forward_output(writer, loop))
        except Exception as e:
            logger.error(f"Bridge error on {self._container.name}: {e}")
        finally:
            logging.info(f"[-] Cleanup on {self._container.name} for {addr}")
            await asyncio.to_thread(self._container.teardown)
            writer.close()

    async def forward_input(self, reader: StreamReader,
                            loop: AbstractEventLoop) -> None:
        while True:
            data: bytes = await reader.read(READ_BUFFER_SIZE)
            if not data: break
            await loop.run_in_executor(None, self.container_socket.sendall, data)

    async def forward_output(self, writer: StreamWriter,
                             loop: AbstractEventLoop) -> None:
        while True:
            data = await loop.run_in_executor(None,
                                              self.container_socket.recv,
                                              RECV_BUFFER_SIZE)
            if not data: break
            writer.write(data)
            await writer.drain()
