from typing import override

import asyncssh
from asyncssh import SSHServer, SSHServerConnection, SSHServerProcess, SSHKey
from loguru import logger

from honeypot.core.backend import Backend
from honeypot.core.bridge import MAX_OUTPUT_LOG, READ_BUFFER_SIZE, RECV_BUFFER_SIZE
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


class SshBridge:
    def __init__(self, backend: Backend) -> None:
        self._backend: Backend = backend
        self._host_key: SSHKey = asyncssh.generate_private_key("ssh-rsa")

    async def _handle_session(self, process: SSHServerProcess[bytes]) -> None:
        ip = extract_ip(process)
        with logger.contextualize(ip=ip, bridge=self.__class__.__name__):
            logger.info("[+] New client detected")
            exit_code = 0
            try:
                async with self._backend:
                    async with RaceGroup() as rg:
                        rg.create_task(self._forward_input(process))
                        rg.create_task(self._forward_output(process))
            except (OSError, EOFError) as e:
                logger.error(f"Bridge error: {e}")
                exit_code = 1
            finally:
                logger.info("[-] Connection closed")
                process.exit(exit_code)

    async def _forward_input(self, process: SSHServerProcess[bytes]) -> None:
        while True:
            data = await process.stdin.read(READ_BUFFER_SIZE)
            if not data:
                break
            logger.info(f"CMD: {data.decode(errors='replace').strip() or repr(data)}")
            await self._backend.write(data)

    async def _forward_output(self, process: SSHServerProcess[bytes]) -> None:
        while True:
            data = await self._backend.read(RECV_BUFFER_SIZE)
            if not data:
                break
            logger.debug(f"Output: {data.decode(errors='replace')[:MAX_OUTPUT_LOG]}")
            process.stdout.write(data)
            await process.stdout.drain()

    async def start_server(
        self, host: str, port: int
    ) -> asyncssh.SSHAcceptor:
        return await asyncssh.create_server(
            _PasswordAuthServer,
            host,
            port,
            server_host_keys=[self._host_key],
            process_factory=self._handle_session,
            encoding=None,
        )
