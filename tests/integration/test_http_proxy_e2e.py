import asyncio
from contextlib import AsyncExitStack

import pytest

from honeypot.core.builder import ProxyBackendFactory
from honeypot.protocols.http_proxy import HttpProxyBridge
from tests.integration.conftest import free_port


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxy_data_relay(echo_tcp_server):
    target_host, target_port = echo_tcp_server
    factory = ProxyBackendFactory(target_host, target_port)
    port = free_port()
    bridge = HttpProxyBridge(
        backend_factory=factory,
        host="127.0.0.1",
        port=port,
    )

    async with asyncio.timeout(5):
        async with AsyncExitStack() as stack:
            await bridge.start(stack)

            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            try:
                payload = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
                writer.write(payload)
                await writer.drain()

                output = b""
                while len(output) < len(payload):
                    chunk = await reader.read(4096)
                    assert chunk, "Connection closed before echo completed"
                    output += chunk
                assert output == payload
            finally:
                writer.close()
                await writer.wait_closed()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxy_backend_down():
    closed_port = free_port()
    factory = ProxyBackendFactory("127.0.0.1", closed_port)
    port = free_port()
    bridge = HttpProxyBridge(
        backend_factory=factory,
        host="127.0.0.1",
        port=port,
    )

    async with asyncio.timeout(5):
        async with AsyncExitStack() as stack:
            await bridge.start(stack)

            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            try:
                writer.write(b"some data\n")
                await writer.drain()

                # The bridge should handle the ConnectionRefusedError and
                # close the connection gracefully (not crash the server)
                await reader.read(4096)
            finally:
                writer.close()
                await writer.wait_closed()

            # Verify the server is still accepting connections (didn't crash)
            reader2, writer2 = await asyncio.open_connection("127.0.0.1", port)
            writer2.close()
            await writer2.wait_closed()
