import asyncio
from socket import socket
from types import TracebackType
from typing import override

from honeypot.backends.container_wrapper import ContainerWrapper
from honeypot.core.backend import Backend
from honeypot.core.exceptions import BackendPropertyError
from honeypot.core.metrics import MetricsManager

SOCKET_PARAMS = {"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1}


class ContainerBackend(Backend):
    def __init__(
        self, container: ContainerWrapper
    ) -> None:
        self._container: ContainerWrapper = container
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
            raw_sock = self._container.attach_socket(params=SOCKET_PARAMS)
            raw_sock.setblocking(False)
            self._sock = raw_sock
            MetricsManager.set_backend_status("container", "docker", True)
        except BaseException:
            MetricsManager.set_backend_status("container", "docker", False)
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
        MetricsManager.set_backend_status("container", "docker", False)
        await asyncio.to_thread(self._container.teardown)
        self._sock = None

    @override
    async def read(self, size: int) -> bytes:
        return await asyncio.get_running_loop().sock_recv(self.sock, size)

    @override
    async def write(self, data: bytes) -> None:
        await asyncio.get_running_loop().sock_sendall(self.sock, data)
