import pytest
from honeypot.containers.telnet_bridge import TelnetBridge
from honeypot.backend import Backend

@pytest.fixture
def mock_backend(mocker):
    backend = mocker.AsyncMock(spec=Backend)
    backend.__aenter__.return_value = backend
    return backend

@pytest.fixture
def bridge(mock_backend):
    return TelnetBridge(backend=mock_backend)

@pytest.fixture
def mock_reader(mocker):
    reader = mocker.AsyncMock()
    reader.readline.side_effect = [b'admin\n', b'password\n']
    return reader

@pytest.fixture
def mock_writer(mocker):
    writer = mocker.Mock()
    writer.drain = mocker.AsyncMock()
    return writer

@pytest.mark.asyncio
async def test_greet_successful_flow(bridge, mock_reader, mock_writer, mocker):
    await bridge.greet(mock_reader, mock_writer)

    expected_calls = [
        mocker.call(b"Ubuntu 20.04 LTS\r\nlogin: "),
        mocker.call(b"Password: "),
        mocker.call(b"\r\nWelcome to Ubuntu.\r\n\r\n")
    ]

    mock_writer.write.assert_has_calls(expected_calls)
    assert mock_writer.drain.call_count == 3
    assert mock_reader.readline.call_count == 2

@pytest.mark.asyncio
async def test_greet_handles_exception(bridge, mock_reader, mock_writer, mocker):
    mock_writer.write.side_effect = OSError("Network failure")
    
    mock_logger_error = mocker.patch("honeypot.containers.telnet_bridge.logger.error")

    await bridge.greet(mock_reader, mock_writer)
    
    mock_logger_error.assert_called_once()
    assert "Connection error: Network failure" in mock_logger_error.call_args[0][0]