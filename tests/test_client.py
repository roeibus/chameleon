import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from asyncio import StreamReader, StreamWriter

from honeypot.containers.container_bridge import ContainerSessionBridge
from honeypot.container import HoneypotContainer


class TestBridge(ContainerSessionBridge):
    def __init__(self, container, mock_loop):
        super().__init__(container)
        self._mock_loop = mock_loop

    @property
    def name(self) -> str:
        return "test_honey"

    @property
    def loop(self):
        return self._mock_loop

    async def greet(self, reader, writer):
        pass


@pytest.fixture
def mock_loop():
    loop = MagicMock()
    loop.sock_sendall = AsyncMock()
    loop.sock_recv = AsyncMock()
    return loop


@pytest.fixture
def mock_container():
    container = MagicMock(spec=HoneypotContainer)
    container.name = "test_honey"
    socket_wrapper = MagicMock()
    raw_socket = MagicMock()
    socket_wrapper._sock = raw_socket
    container.attach_socket.return_value = socket_wrapper
    return container


@pytest.fixture
def bridge(mock_container, mock_loop):
    return TestBridge(container=mock_container, mock_loop=mock_loop)


@pytest.fixture
def mock_reader():
    reader = AsyncMock(spec=StreamReader)
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
async def test_forward_input_sends_to_socket(bridge, mock_container, mock_reader, mock_loop):
    mock_reader.read.side_effect = [b'hello', b'']
    raw_sock = mock_container.attach_socket.return_value._sock

    async with asyncio.timeout(1.0):
        await bridge.forward_input(mock_reader, raw_sock)

    mock_loop.sock_sendall.assert_called_with(raw_sock, b'hello')


@pytest.mark.asyncio
async def test_forward_output_writes_to_client(bridge, mock_container, mock_writer, mock_loop):
    raw_sock = mock_container.attach_socket.return_value._sock
    mock_loop.sock_recv.side_effect = [b'response', b'']

    async with asyncio.timeout(1.0):
        await bridge.forward_output(mock_writer, raw_sock)

    mock_writer.write.assert_called_with(b'response')


@pytest.mark.asyncio
async def test_forward_output_drains_writer(bridge, mock_container, mock_writer, mock_loop):
    raw_sock = mock_container.attach_socket.return_value._sock
    mock_loop.sock_recv.side_effect = [b'response', b'']

    async with asyncio.timeout(1.0):
        await bridge.forward_output(mock_writer, raw_sock)

    mock_writer.drain.assert_awaited()


@pytest.mark.asyncio
async def test_handle_client_calls_setup(bridge, mock_container, mock_reader, mock_writer):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_container.setup.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_calls_teardown(bridge, mock_container, mock_reader, mock_writer):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_container.teardown.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_closes_writer(bridge, mock_container, mock_reader, mock_writer):
    await bridge.handle_client(mock_reader, mock_writer)
    mock_writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_data_flow(bridge, mock_container, mock_reader, mock_writer, mock_loop):
    mock_reader.read.side_effect = [b'ls', b'']
    mock_loop.sock_recv.side_effect = [b'ok', b'']
    raw_socket = mock_container.attach_socket.return_value._sock

    await bridge.handle_client(mock_reader, mock_writer)

    mock_loop.sock_sendall.assert_called_with(raw_socket, b'ls')


@pytest.mark.asyncio
async def test_cleanup_on_setup_error(bridge, mock_container, mock_reader, mock_writer):
    mock_container.setup.side_effect = RuntimeError("Fail")
    await bridge.handle_client(mock_reader, mock_writer)
    mock_container.teardown.assert_called_once()