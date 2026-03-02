import asyncio
from asyncio import StreamReader, StreamWriter

import pytest

from honeypot.config import Protocol
from honeypot.core.bridge.session import SessionBridge
from honeypot.core.metrics import MetricsManager


class _ConcreteSessionBridge(SessionBridge):
    """Minimal concrete subclass for testing."""

    def __init__(self, mocker, max_connections: int = 100) -> None:
        super().__init__(None, "127.0.0.1", 0, max_connections)  # type: ignore
        self._handle_client_mock = mocker.AsyncMock()

    @property
    def protocol(self):
        return Protocol.TELNET

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        await self._handle_client_mock(reader, writer)


def _make_writer(mocker) -> StreamWriter:
    writer = mocker.MagicMock(spec=StreamWriter)
    writer.close = mocker.MagicMock()
    writer.wait_closed = mocker.AsyncMock()
    writer.get_extra_info = mocker.MagicMock(return_value=("1.2.3.4", 1234))
    return writer


@pytest.mark.asyncio
async def test_at_capacity_rejects_connection(mocker):
    """When the semaphore is exhausted, handle_client closes the writer immediately."""
    bridge = _ConcreteSessionBridge(mocker, max_connections=1)
    # Manually drain the semaphore to simulate a full server.
    await bridge._sem.acquire()

    writer = _make_writer(mocker)
    reader = mocker.MagicMock(spec=StreamReader)

    mock_rejected = mocker.patch.object(MetricsManager, "record_rejected_connection")
    await bridge.handle_client(reader, writer)

    writer.close.assert_called_once()
    bridge._handle_client_mock.assert_not_called()
    mock_rejected.assert_called_once_with(bridge.protocol)


@pytest.mark.asyncio
async def test_under_capacity_calls_handle_client(mocker):
    """When a slot is free, handle_client delegates to _handle_client and releases."""
    bridge = _ConcreteSessionBridge(mocker, max_connections=2)
    # One slot taken, one free.
    await bridge._sem.acquire()

    writer = _make_writer(mocker)
    reader = mocker.MagicMock(spec=StreamReader)

    mocker.patch.object(MetricsManager, "record_connection")
    mocker.patch.object(MetricsManager, "record_disconnection")

    await bridge.handle_client(reader, writer)

    bridge._handle_client_mock.assert_called_once_with(reader, writer)
    # The slot must have been released: value is back to 1.
    async with asyncio.timeout(0):
        await bridge._sem.acquire()
    bridge._sem.release()


@pytest.mark.asyncio
async def test_semaphore_released_on_exception(mocker):
    """Even when _handle_client raises, the semaphore slot is released."""
    bridge = _ConcreteSessionBridge(mocker, max_connections=1)
    bridge._handle_client_mock.side_effect = OSError("boom")

    writer = _make_writer(mocker)
    reader = mocker.MagicMock(spec=StreamReader)

    mocker.patch.object(MetricsManager, "record_connection")
    mocker.patch.object(MetricsManager, "record_disconnection")

    await bridge.handle_client(reader, writer)

    # Check if slot was released
    async with asyncio.timeout(0):
        await bridge._sem.acquire()
    bridge._sem.release()
