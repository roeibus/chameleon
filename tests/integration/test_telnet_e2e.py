import asyncio
from contextlib import AsyncExitStack

import pytest

from honeypot.protocols.telnet import TelnetBridge
from tests.integration.conftest import docker_skip, free_port


pytestmark = [pytest.mark.integration, docker_skip]


@pytest.mark.asyncio
async def test_telnet_login_and_command(container_backend_factory):
    port = free_port()
    bridge = TelnetBridge(
        backend_factory=container_backend_factory,
        host="127.0.0.1",
        port=port,
    )

    async with asyncio.timeout(15):
        async with AsyncExitStack() as stack:
            await bridge.start(stack)

            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            try:
                # Read greeting banner
                greeting = b""
                while b"login: " not in greeting:
                    chunk = await reader.read(4096)
                    assert chunk, "Connection closed before login prompt"
                    greeting += chunk
                assert b"Ubuntu 20.04" in greeting

                # Send username
                writer.write(b"admin\n")
                await writer.drain()

                # Read password prompt
                prompt = b""
                while b"Password: " not in prompt:
                    chunk = await reader.read(4096)
                    assert chunk, "Connection closed before password prompt"
                    prompt += chunk

                # Send password
                writer.write(b"secret\n")
                await writer.drain()

                # Read welcome banner
                welcome = b""
                while b"Welcome to Ubuntu" not in welcome:
                    chunk = await reader.read(4096)
                    assert chunk, "Connection closed before welcome banner"
                    welcome += chunk

                # Send a command
                writer.write(b"echo test123\n")
                await writer.drain()

                # Read command output
                output = b""
                while b"test123" not in output:
                    chunk = await reader.read(4096)
                    assert chunk, "Connection closed before command output"
                    output += chunk
            finally:
                writer.close()
                await writer.wait_closed()


@pytest.mark.asyncio
async def test_telnet_client_disconnect_cleanup(
    container_backend_factory, docker_client
):
    # Snapshot existing containers before the test
    pre_ids = {
        c.id
        for c in docker_client.containers.list(
            all=True, filters={"ancestor": "telnet"}
        )
    }

    port = free_port()
    bridge = TelnetBridge(
        backend_factory=container_backend_factory,
        host="127.0.0.1",
        port=port,
    )

    async with asyncio.timeout(15):
        async with AsyncExitStack() as stack:
            await bridge.start(stack)

            reader, writer = await asyncio.open_connection("127.0.0.1", port)

            # Read greeting
            greeting = b""
            while b"login: " not in greeting:
                chunk = await reader.read(4096)
                assert chunk
                greeting += chunk

            writer.write(b"admin\n")
            await writer.drain()

            prompt = b""
            while b"Password: " not in prompt:
                chunk = await reader.read(4096)
                assert chunk
                prompt += chunk

            writer.write(b"pass\n")
            await writer.drain()

            welcome = b""
            while b"Welcome to Ubuntu" not in welcome:
                chunk = await reader.read(4096)
                assert chunk
                welcome += chunk

            # Abruptly close connection
            writer.close()
            await writer.wait_closed()

            # Give bridge time to clean up the container
            await asyncio.sleep(2)

    # Verify no NEW containers leaked from this test
    post_ids = {
        c.id
        for c in docker_client.containers.list(
            all=True, filters={"ancestor": "telnet"}
        )
    }
    new_containers = post_ids - pre_ids
    assert len(new_containers) == 0, (
        f"Leaked containers from test: {new_containers}"
    )
