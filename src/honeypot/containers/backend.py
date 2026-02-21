import asyncio
from socket import socket
from types import TracebackType

from honeypot.containers.wrapper import HoneypotContainer
from honeypot.backend import Backend
from honeypot.exc import BackendPropertyError


class ContainerBackend(Backend):
    def __init__(self, container: HoneypotContainer,
                 socket_params: dict[str, int]) -> None:
        self._container = container
        self._socket_params = socket_params
        self._sock: socket | None = None

    @property
    def sock(self) -> socket:
        if self._sock is None:
            raise BackendPropertyError("ContainerBackend is not connected")
        return self._sock

    async def __aenter__(self) -> 'ContainerBackend':
        """
            Accessing the inner container to emulate real raw connection.
        """
        await asyncio.to_thread(self._container.setup)
        # pylint: disable=protected-access
        raw_sock = self._container.attach_socket(params=self._socket_params)._sock
        raw_sock.setblocking(False)
        self._sock = raw_sock
        return self

    async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None
    ) -> None:
        await asyncio.to_thread(self._container.teardown)
        self._sock = None

    async def read(self, size: int) -> bytes:
        return await asyncio.get_running_loop().sock_recv(self.sock, size)

    async def write(self, data: bytes) -> None:
        await asyncio.get_running_loop().sock_sendall(self.sock, data)
