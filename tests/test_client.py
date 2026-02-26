import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from asyncio import StreamReader, StreamWriter

from honeypot.bridge import SessionBridge
from honeypot.backend import Backend


class TestBridge(SessionBridge):
    @property
    def name(self) -> str:
        return "test_honey"

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        async with self._backend:
            await self._forward(reader, writer)


@pytest.fixture
def mock_backend():
    backend = AsyncMock(spec=Backend)
    backend.read.return_value = b''
    backend.__aenter__.return_value = backend
    return backend


@pytest.fixture
def bridge(mock_backend):
    return TestBridge(backend=mock_backend)


@pytest.fixture
def mock_reader():
    reader = AsyncMock(spec=StreamReader)
    reader.read.return_value = b''
    return reader


@pytest.fixture
def mock_writer():
    writer = MagicMock(spec=StreamWriter)
    writer.get_extra_info.return_value = ('127.0.0.1', 12345)
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return writer


@pytest.mark.asyncio
async def test_forward_input_sends_to_backend(bridge, mock_backend, mock_reader):
    mock_reader.read.side_effect = [b'hello', b'']

    async with asyncio.timeout(1.0):
        await bridge.forward_input(mock_reader)

    mock_backend.write.assert_awaited_with(b'hello')


@pytest.mark.asyncio
async def test_forward_output_writes_to_client(bridge, mock_backend, mock_writer):
    mock_backend.read.side_effect = [b'response', b'']

    async with asyncio.timeout(1.0):
        await bridge.forward_output(mock_writer)

    mock_writer.write.assert_called_with(b'response')


@pytest.mark.asyncio
async def test_forward_output_drains_writer(bridge, mock_backend, mock_writer):
    mock_backend.read.side_effect = [b'response', b'']

    async with asyncio.timeout(1.0):
        await bridge.forward_output(mock_writer)

    mock_writer.drain.assert_awaited()


@pytest.mark.asyncio
async def test_handle_client_calls_aenter(bridge, mock_backend, mock_reader, mock_writer):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_backend.__aenter__.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_client_calls_aexit(bridge, mock_backend, mock_reader, mock_writer):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_backend.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_client_closes_writer(bridge, mock_backend, mock_reader, mock_writer):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_data_flow(bridge, mock_backend, mock_reader, mock_writer):
    mock_reader.read.side_effect = [b'ls', b'']
    mock_backend.read.side_effect = [b'ok', b'']

    await bridge.handle_client(mock_reader, mock_writer)

    mock_backend.write.assert_awaited_with(b'ls')


@pytest.mark.asyncio
async def test_cleanup_on_setup_error(bridge, mock_backend, mock_reader, mock_writer):
    mock_backend.__aenter__.side_effect = OSError("Fail")
    await bridge.handle_client(mock_reader, mock_writer)
    mock_writer.close.assert_called_once()
