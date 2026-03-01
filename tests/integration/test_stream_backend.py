import asyncio

import pytest

from honeypot.backends.stream_backend import StreamBackend
from tests.integration.conftest import free_port


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_write_roundtrip(echo_tcp_server):
    host, port = echo_tcp_server
    backend = StreamBackend(host, port)
    async with asyncio.timeout(5):
        async with backend:
            await backend.write(b"hello world")
            output = b""
            while len(output) < len(b"hello world"):
                chunk = await backend.read(4096)
                assert chunk, "Backend returned empty read before expected output"
                output += chunk
            assert output == b"hello world"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cleanup_on_exit(echo_tcp_server):
    host, port = echo_tcp_server
    backend = StreamBackend(host, port)
    async with asyncio.timeout(5):
        async with backend:
            await backend.write(b"data")
            await backend.read(4096)

    assert backend._writer is None
    assert backend._reader is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connection_refused():
    port = free_port()
    backend = StreamBackend("127.0.0.1", port)
    with pytest.raises((ConnectionRefusedError, OSError)):
        async with asyncio.timeout(5):
            async with backend:
                pass
