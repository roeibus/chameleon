import asyncio
from contextlib import AsyncExitStack
from typing import override

import asyncssh
from asyncssh import SSHServer, SSHServerConnection, SSHServerProcess, SSHKey
from loguru import logger

from honeypot.config import Protocol
from honeypot.core.backend import BackendFactory
from honeypot.core.bridge import ProtocolServer
from honeypot.core.bridge.relay import relay
from honeypot.core.metrics import MetricsManager
from honeypot.utils import extract_ip, log_login_attempt

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
            log_login_attempt(username, password)
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
        self._sem: asyncio.Semaphore = asyncio.Semaphore(max_connections)

    @property
    @override
    def protocol(self) -> Protocol:
        return Protocol.SSH

    async def _handle_session(self, process: SSHServerProcess[bytes]) -> None:
        ip = extract_ip(process)
        with logger.contextualize(ip=ip, bridge=self.__class__.__name__):
            try:
                async with asyncio.timeout(0):
                    await self._sem.acquire()
            except TimeoutError:
                logger.warning("[!] Connection limit reached, rejecting")
                MetricsManager.record_rejected_connection(self.protocol)
                process.exit(1)
                return

            logger.info("[+] New client detected")
            MetricsManager.record_connection(self.protocol)
            exit_code = 0
            try:
                backend = self._backend_factory.create()
                async with backend:
                    await relay(process.stdin, process.stdout, backend, self.protocol)
            except (OSError, EOFError) as e:
                logger.error(f"Bridge error: {e}")
                exit_code = 1
            finally:
                logger.info("[-] Connection closed")
                MetricsManager.record_disconnection(self.protocol)
                self._sem.release()
                process.exit(exit_code)

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
