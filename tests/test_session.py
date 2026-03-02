import asyncio
from asyncio import StreamReader, StreamWriter
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from honeypot.core.bridge.session import SessionBridge
from honeypot.core.metrics import MetricsManager


class _ConcreteSessionBridge(SessionBridge):
    """Minimal concrete subclass for testing."""

    def __init__(self, max_connections: int = 100) -> None:
        super().__init__(None, "127.0.0.1", 0, max_connections)  # type: ignore
        self._handle_client_mock = AsyncMock()

    @property
    def protocol(self):
        return "test_protocol"

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        await self._handle_client_mock(reader, writer)


def _make_writer() -> StreamWriter:
    writer = MagicMock(spec=StreamWriter)
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    writer.get_extra_info = MagicMock(return_value=("1.2.3.4", 1234))
    return writer


@pytest.mark.asyncio
async def test_at_capacity_rejects_connection():
    """When the semaphore is exhausted, handle_client closes the writer immediately."""
    bridge = _ConcreteSessionBridge(max_connections=1)
    # Manually drain the semaphore to simulate a full server.
    await bridge._sem.acquire()

    writer = _make_writer()
    reader = MagicMock(spec=StreamReader)

    with patch.object(MetricsManager, "record_rejected_connection") as mock_rejected:
        await bridge.handle_client(reader, writer)

    writer.close.assert_called_once()
    bridge._handle_client_mock.assert_not_called()
    mock_rejected.assert_called_once_with(bridge.protocol)


@pytest.mark.asyncio
async def test_under_capacity_calls_handle_client():
    """When a slot is free, handle_client delegates to _handle_client and releases."""
    bridge = _ConcreteSessionBridge(max_connections=2)
    # One slot taken, one free.
    await bridge._sem.acquire()

    writer = _make_writer()
    reader = MagicMock(spec=StreamReader)

    with (
        patch.object(MetricsManager, "record_connection"),
        patch.object(MetricsManager, "record_disconnection"),
    ):
        await bridge.handle_client(reader, writer)

    bridge._handle_client_mock.assert_called_once_with(reader, writer)
    # The slot must have been released: value is back to 1.
    async with asyncio.timeout(0):
        await bridge._sem.acquire()
    bridge._sem.release()

@pytest.mark.asyncio
async def test_semaphore_released_on_exception():
    """Even when _handle_client raises, the semaphore slot is released."""
    bridge = _ConcreteSessionBridge(max_connections=1)
    bridge._handle_client_mock.side_effect = OSError("boom")

    writer = _make_writer()
    reader = MagicMock(spec=StreamReader)

    assert bridge._sem._value == 1  # type: ignore[attr-defined]

    with (
        patch.object(MetricsManager, "record_connection"),
        patch.object(MetricsManager, "record_disconnection"),
    ):
        await bridge.handle_client(reader, writer)

    assert bridge._sem._value == 1  # type: ignore[attr-defined]
