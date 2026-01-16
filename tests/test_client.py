import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from asyncio import StreamReader, StreamWriter

from honeypot.client import ContainerSessionBridge
from honeypot.container import HoneypotContainer

class TestBridge(ContainerSessionBridge):
    async def greet(self, reader, writer):
        pass


@pytest.fixture
def mock_container():
    """Mocks the HoneypotContainer and its internal socket wrapper."""
    container = MagicMock(spec=HoneypotContainer)
    container.name = "test_honey"
    socket_wrapper = MagicMock()
    raw_socket = MagicMock()
    socket_wrapper._sock = raw_socket
    container.attach_socket.return_value = socket_wrapper
    return container


@pytest.fixture
def bridge(mock_container):
    return TestBridge(container=mock_container)


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
    return writer


@pytest.mark.asyncio
async def test_container_socket_property(bridge, mock_container):
    """Ensure we unwrap the socket correctly (accesses ._sock)."""
    sock = bridge.container_socket
    mock_container.attach_socket.assert_called_once()
    assert sock == mock_container.attach_socket.return_value._sock


@pytest.mark.asyncio
async def test_forward_input(bridge, mock_container, mock_reader):
    """Test reading from client and sending to container socket."""
    mock_reader.read.side_effect = [b'hello', b'']
    loop = asyncio.get_running_loop()
    async with asyncio.timeout(1.0): # prevent infinite loop
        await bridge.forward_input(mock_reader, loop)
    assert mock_reader.read.call_count == 2
    raw_sock = mock_container.attach_socket.return_value._sock
    raw_sock.sendall.assert_called_with(b'hello')


@pytest.mark.asyncio
async def test_forward_output(bridge, mock_container, mock_writer):
    """Test reading from container socket and writing to client."""
    raw_sock = mock_container.attach_socket.return_value._sock
    raw_sock.recv.side_effect = [b'response', b'']

    loop = asyncio.get_running_loop()

    async with asyncio.timeout(1.0):
        await bridge.forward_output(mock_writer, loop)

    mock_writer.write.assert_called_with(b'response')
    mock_writer.drain.assert_awaited()


@pytest.mark.asyncio
async def test_handle_client_full_flow(bridge, mock_container, mock_reader, mock_writer):
    """
    Test the full lifecycle without patching internal methods by name.
    We control the loop execution via the Mocks' return values.
    """

    mock_reader.read.side_effect = [b'ls -la', b'']

    raw_socket = mock_container.attach_socket.return_value._sock
    raw_socket.recv.side_effect = [b'total 0\n', b'']

    await bridge.handle_client(mock_reader, mock_writer)

    mock_container.setup.assert_called_once()
    mock_container.teardown.assert_called_once()
    mock_writer.close.assert_called_once()

    raw_socket.sendall.assert_called_with(b'ls -la')

    mock_writer.write.assert_called_with(b'total 0\n')
    mock_writer.drain.assert_awaited()


@pytest.mark.asyncio
async def test_error_handling_cleanup(bridge, mock_container, mock_reader, mock_writer):
    """
    Verify teardown happens even if the container setup crashes.
    """
    # Simulate a crash during setup
    mock_container.setup.side_effect = RuntimeError("Docker failed")

    await bridge.handle_client(mock_reader, mock_writer)

    # Verify we still cleaned up
    mock_container.teardown.assert_called_once()
    # Verify we closed the client connection
    mock_writer.close.assert_called_once()