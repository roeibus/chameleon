import asyncio
from asyncio import StreamReader, StreamWriter

import pytest

from honeypot.config import Protocol
from honeypot.core.backend import Backend, BackendFactory
from honeypot.core.bridge import SessionBridge
from honeypot.core.bridge.relay import forward_input, forward_output, relay


class DummyBridge(SessionBridge):
    @property
    def protocol(self) -> Protocol:
        return Protocol.HTTP_PROXY

    @property
    def name(self) -> str:
        return "test_honey"

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        backend = self._backend_factory.create()
        async with backend:
            await relay(reader, writer, backend, self.protocol)


@pytest.fixture
def mock_backend(mocker):
    backend = mocker.AsyncMock(spec=Backend)
    backend.read.return_value = b""
    backend.__aenter__.return_value = backend
    return backend


@pytest.fixture
def mock_factory(mocker, mock_backend):
    factory = mocker.Mock(spec=BackendFactory)
    factory.create.return_value = mock_backend
    return factory


@pytest.fixture
def bridge(mock_factory):
    return DummyBridge(backend_factory=mock_factory, host="127.0.0.1", port=0)


@pytest.fixture
def mock_reader(mocker):
    reader = mocker.AsyncMock(spec=StreamReader)
    reader.read.return_value = b""
    return reader


@pytest.fixture
def mock_writer(mocker):
    writer = mocker.Mock(spec=StreamWriter)
    writer.get_extra_info.return_value = ("127.0.0.1", 12345)
    writer.drain = mocker.AsyncMock()
    writer.close = mocker.Mock()
    writer.wait_closed = mocker.AsyncMock()
    return writer


@pytest.mark.asyncio
async def test_forward_input_sends_to_backend(mock_backend, mock_reader):
    mock_reader.read.side_effect = [b"hello", b""]

    async with asyncio.timeout(1.0):
        await forward_input(mock_reader, mock_backend, Protocol.HTTP_PROXY)

    mock_backend.write.assert_awaited_with(b"hello")


@pytest.mark.asyncio
async def test_forward_output_writes_to_client(mock_backend, mock_writer):
    mock_backend.read.side_effect = [b"response", b""]

    async with asyncio.timeout(1.0):
        await forward_output(mock_writer, mock_backend, Protocol.HTTP_PROXY)

    mock_writer.write.assert_called_with(b"response")


@pytest.mark.asyncio
async def test_forward_output_drains_writer(mock_backend, mock_writer):
    mock_backend.read.side_effect = [b"response", b""]

    async with asyncio.timeout(1.0):
        await forward_output(mock_writer, mock_backend, Protocol.HTTP_PROXY)

    mock_writer.drain.assert_awaited()


@pytest.mark.asyncio
async def test_handle_client_calls_aenter(
    bridge, mock_backend, mock_reader, mock_writer
):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_backend.__aenter__.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_client_calls_aexit(
    bridge, mock_backend, mock_reader, mock_writer
):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_backend.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_client_closes_writer(
    bridge, mock_backend, mock_reader, mock_writer
):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_data_flow(bridge, mock_backend, mock_reader, mock_writer):
    mock_reader.read.side_effect = [b"ls", b""]
    mock_backend.read.side_effect = [b"ok", b""]

    await bridge.handle_client(mock_reader, mock_writer)

    mock_backend.write.assert_awaited_with(b"ls")


@pytest.mark.asyncio
async def test_cleanup_on_setup_error(bridge, mock_backend, mock_reader, mock_writer):
    mock_backend.__aenter__.side_effect = OSError("Fail")
    await bridge.handle_client(mock_reader, mock_writer)
    mock_writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_creates_backend(
    bridge, mock_factory, mock_reader, mock_writer
):
    await bridge._handle_client(mock_reader, mock_writer)
    mock_factory.create.assert_called_once()


@pytest.mark.asyncio
async def test_start_server(bridge, mocker):
    mock_server = mocker.Mock(spec=asyncio.Server)
    mock_socket = mocker.Mock()
    mock_socket.getsockname.return_value = ("127.0.0.1", 1234)
    mock_server.sockets = [mock_socket]

    mock_start_server = mocker.patch(
        "asyncio.start_server", new_callable=mocker.AsyncMock
    )
    mock_start_server.return_value = mock_server

    stack = mocker.AsyncMock()

    result = await bridge.start(stack)

    assert result is mock_server
    mock_start_server.assert_awaited_once_with(
        bridge.handle_client, bridge._host, bridge._port
    )
    stack.enter_async_context.assert_awaited_once_with(mock_server)
