import asyncio
from loguru import logger
from abc import abstractmethod, ABC
from asyncio import AbstractEventLoop, StreamReader, StreamWriter
from functools import cached_property
from socket import socket

from honeypot.container import HoneypotContainer

RECV_BUFFER_SIZE = 4096
READ_BUFFER_SIZE = 4096
MAX_CMD_OUTPUT_LOG = 100
SOCKET_PARAMS = {'stdin': 1, 'stdout': 1, 'stderr': 1, 'stream': 1}


class ContainerSessionBridge(ABC):
    def __init__(self, container: HoneypotContainer,
                 socket_params: dict[str, int] | None = None) -> None:
        self._container = container
        self._socket_params = socket_params or SOCKET_PARAMS

    @abstractmethod
    async def greet(self, reader: StreamReader,
                    writer: StreamWriter) -> None:
        pass

    @cached_property
    def container_socket(self) -> socket:
        """
            We are deliberately giving the underlying sock class
            instead of the socket wrapper given by attach socket
            to avoid unwanted underlying logic (e.g: buffering data)
        """
        return self._container.attach_socket(params=self._socket_params)._sock  # pylint: disable=protected-access

    async def handle_client(self, reader: StreamReader,
                            writer: StreamWriter) -> None:
        addr: tuple = writer.get_extra_info('peername')
        with logger.contextualize(ip=addr[0]):
            try:
                await self.greet(reader, writer)
                await asyncio.to_thread(self._container.setup)
                loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
                await asyncio.gather(self.forward_input(reader, loop),
                                     self.forward_output(writer, loop))
            except Exception as e:
                logger.error(f"Bridge error on {self._container.name}: {e}")
            finally:
                logger.info(f"[-] Cleanup on {self._container.name} for {addr}")
                await asyncio.to_thread(self._container.teardown)
                writer.close()

    async def forward_input(self, reader: StreamReader,
                            loop: AbstractEventLoop) -> None:
        while True:
            data: bytes = await reader.read(READ_BUFFER_SIZE)
            if not data: break
            text = data.decode(errors='replace').strip() or repr(data)
            logger.info(f"CMD: {text}")
            await loop.run_in_executor(None, self.container_socket.sendall, data)

    async def forward_output(self, writer: StreamWriter,
                             loop: AbstractEventLoop) -> None:
        while True:
            data = await loop.run_in_executor(None,
                                              self.container_socket.recv,
                                              RECV_BUFFER_SIZE)
            if not data: break
            text = data.decode(errors='replace')[:MAX_CMD_OUTPUT_LOG].replace('\r', '')
            logger.debug(f"Output: {text}")
            writer.write(data)
            await writer.drain()
