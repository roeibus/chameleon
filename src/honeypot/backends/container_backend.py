import asyncio
from socket import socket
from types import TracebackType
from typing import override

from honeypot.backends.container_wrapper import ContainerWrapper
from honeypot.core.backend import Backend
from honeypot.core.exc import BackendPropertyError


class ContainerBackend(Backend):
    def __init__(
        self, container: ContainerWrapper, socket_params: dict[str, int]
    ) -> None:
        self._container: ContainerWrapper = container
        self._socket_params: dict[str, int] = socket_params
        self._sock: socket | None = None

    @property
    def sock(self) -> socket:
        if self._sock is None:
            raise BackendPropertyError("ContainerBackend is not connected")
        return self._sock

    @override
    async def __aenter__(self) -> "ContainerBackend":
        await asyncio.to_thread(self._container.setup)
        try:
            raw_sock = self._container.attach_socket(params=self._socket_params)
            raw_sock.setblocking(False)
            self._sock = raw_sock
        except BaseException:
            await asyncio.to_thread(self._container.teardown)
            raise
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await asyncio.to_thread(self._container.teardown)
        self._sock = None

    @override
    async def read(self, size: int) -> bytes:
        return await asyncio.get_running_loop().sock_recv(self.sock, size)

    @override
    async def write(self, data: bytes) -> None:
        await asyncio.get_running_loop().sock_sendall(self.sock, data)
