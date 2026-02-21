import asyncio
from abc import abstractmethod, ABC
from asyncio import StreamReader, StreamWriter
from socket import socket
from loguru import logger

from honeypot.container import HoneypotContainer
from honeypot.session_bridge import SessionBridge
from honeypot.utils.race_group import RaceGroup

RECV_BUFFER_SIZE = 4096
READ_BUFFER_SIZE = 4096
MAX_CMD_OUTPUT_LOG = 100
SOCKET_PARAMS = {'stdin': 1, 'stdout': 1, 'stderr': 1, 'stream': 1}


class ContainerSessionBridge(SessionBridge, ABC):
    def __init__(self, container: HoneypotContainer,
                 race_group: RaceGroup | None = None,
                 socket_params: dict[str, int] | None = None) -> None:
        self._container = container
        self._race_group = race_group or RaceGroup()
        self._socket_params = socket_params or SOCKET_PARAMS

    @abstractmethod
    async def greet(self, reader: StreamReader,
                    writer: StreamWriter) -> None:
        pass

    def _get_container_socket(self) -> socket:
        """
        Helper to attach and configure the socket.
        Not cached, so we get a fresh one every time setup() runs.
        """
        # pylint: disable=protected-access
        raw_sock = self._container.attach_socket(params=self._socket_params)._sock
        raw_sock.setblocking(False)
        return raw_sock

    async def handle_bridge(self, reader: StreamReader,
                            writer: StreamWriter) -> None:
        try:
            await asyncio.to_thread(self._container.setup)
            container_socket = self._get_container_socket()
            await self.greet(reader, writer)
            async with self._race_group as rg:
                rg.create_task(self.forward_input(reader, container_socket))
                rg.create_task(self.forward_output(writer, container_socket))
        finally:
            await asyncio.to_thread(self._container.teardown)

    async def forward_input(self, reader: StreamReader, container_socket: socket) -> None:
        while True:
            data: bytes = await reader.read(READ_BUFFER_SIZE)
            if not data: break
            text = data.decode(errors='replace').strip() or repr(data)
            logger.info(f"CMD: {text}")
            await self.loop.sock_sendall(container_socket, data)

    async def forward_output(self, writer: StreamWriter, container_socket: socket) -> None:
        while True:
            data = await self.loop.sock_recv(container_socket, RECV_BUFFER_SIZE)
            if not data: break
            text = data.decode(errors='replace')[:MAX_CMD_OUTPUT_LOG].replace('\r', '')
            logger.debug(f"Output: {text}")
            writer.write(data)
            await writer.drain()
