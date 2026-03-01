import asyncio
from contextlib import AsyncExitStack

import asyncssh
import pytest

from honeypot.protocols.ssh import SshBridge
from tests.integration.conftest import docker_skip, free_port


pytestmark = [pytest.mark.integration, docker_skip]


@pytest.mark.asyncio
async def test_ssh_login_and_command(container_backend_factory):
    port = free_port()
    bridge = SshBridge(
        backend_factory=container_backend_factory,
        host="127.0.0.1",
        port=port,
    )

    async with asyncio.timeout(15):
        async with AsyncExitStack() as stack:
            await bridge.start(stack)

            async with asyncssh.connect(
                "127.0.0.1",
                port=port,
                username="admin",
                password="secret",
                known_hosts=None,
            ) as conn:
                process = await conn.create_process(encoding=None)
                assert process.stdin is not None
                assert process.stdout is not None

                process.stdin.write(b"echo test123\n")
                await process.stdin.drain()

                output = b""
                while b"test123" not in output:
                    chunk = await process.stdout.read(4096)
                    if not chunk:
                        break
                    output += chunk

                assert b"test123" in output
