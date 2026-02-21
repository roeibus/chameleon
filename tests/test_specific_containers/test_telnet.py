import pytest
from unittest.mock import MagicMock, AsyncMock, call
from honeypot.containers.telnet_bridge import TelnetBridge
from honeypot.container import HoneypotContainer


@pytest.fixture
def mock_container():
    return MagicMock(spec=HoneypotContainer)


@pytest.fixture
def bridge(mock_container):
    return TelnetBridge(container=mock_container)


@pytest.fixture
def mock_reader():
    reader = AsyncMock()
    reader.readline.side_effect = [b'admin\n', b'password\n']
    return reader


@pytest.fixture
def mock_writer():
    writer = MagicMock()
    writer.drain = AsyncMock()
    return writer


@pytest.mark.asyncio
async def test_greet_successful_flow(bridge, mock_reader, mock_writer):
    await bridge.greet(mock_reader, mock_writer)

    expected_calls = [
        call(b"Ubuntu 20.04 LTS\r\nlogin: "),
        call(b"Password: "),
        call(b"\r\nWelcome to Ubuntu.\r\n\r\n")
    ]

    mock_writer.write.assert_has_calls(expected_calls)
    assert mock_writer.drain.call_count == 3
    assert mock_reader.readline.call_count == 2


@pytest.mark.asyncio
async def test_greet_handles_exception(bridge, mock_reader, mock_writer, caplog):
    mock_writer.write.side_effect = OSError("Network failure")

    await bridge.greet(mock_reader, mock_writer)
