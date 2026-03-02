from contextlib import AsyncExitStack
from typing import override

import asyncssh
from asyncssh import SSHServer, SSHServerConnection, SSHServerProcess, SSHKey
from loguru import logger

from honeypot.config import Protocol
from honeypot.core.backend import Backend, BackendFactory
from honeypot.core.bridge import (
    MAX_OUTPUT_LOG,
    READ_BUFFER_SIZE,
    RECV_BUFFER_SIZE,
    ProtocolServer,
)
from honeypot.core.metrics import MetricsManager
from honeypot.utils import RaceGroup, extract_ip

"""
    SSH bridge isn't using core components
    because of asyncssh usage and incompatibility
"""


class _PasswordAuthServer(SSHServer):
    def __init__(self) -> None:
        super().__init__()
        self._ip: str = "UNKNOWN"

    @override
    def connection_made(self, conn: SSHServerConnection) -> None:
        self._ip = extract_ip(conn)

    @override
    def password_auth_supported(self) -> bool:
        return True

    @override
    def validate_password(self, username: str, password: str) -> bool:
        with logger.contextualize(ip=self._ip, bridge="ssh"):
            logger.info(
                "Login attempt: "
                + f"username={username!r}, "
                + f"password={password!r}"
            )
        return True


class SshBridge(ProtocolServer):
    def __init__(
        self,
        backend_factory: BackendFactory,
        host: str,
        port: int,
        max_connections: int = 100,
    ) -> None:
        super().__init__(backend_factory, host, port, max_connections)
        self._host_key: SSHKey = asyncssh.generate_private_key("ssh-rsa")

    @property
    @override
    def protocol(self) -> Protocol:
        return Protocol.SSH

    async def _handle_session(self, process: SSHServerProcess[bytes]) -> None:
        ip = extract_ip(process)
        with logger.contextualize(ip=ip, bridge=self.__class__.__name__):
            logger.info("[+] New client detected")
            MetricsManager.record_connection(self.protocol)
            exit_code = 0
            try:
                backend = self._backend_factory.create()
                async with backend:
                    async with RaceGroup() as rg:
                        rg.append_task(self._forward_input(process, backend))
                        rg.append_task(self._forward_output(process, backend))
            except (OSError, EOFError) as e:
                logger.error(f"Bridge error: {e}")
                exit_code = 1
            finally:
                logger.info("[-] Connection closed")
                MetricsManager.record_disconnection(self.protocol)
                process.exit(exit_code)

    async def _forward_input(
        self, process: SSHServerProcess[bytes], backend: Backend
    ) -> None:
        while True:
            data = await process.stdin.read(READ_BUFFER_SIZE)
            if not data:
                break
            logger.info(f"CMD: {data.decode(errors='replace').strip() or repr(data)}")
            MetricsManager.record_bytes(self.protocol, "tx", len(data))
            await backend.write(data)

    async def _forward_output(
        self, process: SSHServerProcess[bytes], backend: Backend
    ) -> None:
        while True:
            data = await backend.read(RECV_BUFFER_SIZE)
            if not data:
                break
            logger.debug(f"Output: {data.decode(errors='replace')[:MAX_OUTPUT_LOG]}")
            MetricsManager.record_bytes(self.protocol, "rx", len(data))
            process.stdout.write(data)
            await process.stdout.drain()

    @override
    async def start(self, stack: AsyncExitStack) -> None:
        ssh_server = await asyncssh.create_server(
            _PasswordAuthServer,
            self._host,
            self._port,
            server_host_keys=[self._host_key],
            process_factory=self._handle_session,
            encoding=None,
        )
        # LIFO: wait_closed runs before close (push_async_callback is LIFO)
        stack.push_async_callback(ssh_server.wait_closed)
        stack.callback(ssh_server.close)
        logger.info(f"[*] SSH listening on {ssh_server.get_addresses()}")
        return None  # asyncssh manages its own serve loop
