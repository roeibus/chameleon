import pytest
from honeypot.protocols.telnet import TelnetBridge
from honeypot.core.backend import Backend, BackendFactory

@pytest.fixture
def mock_backend(mocker):
    backend = mocker.AsyncMock(spec=Backend)
    backend.__aenter__.return_value = backend
    return backend

@pytest.fixture
def mock_factory(mocker, mock_backend):
    factory = mocker.Mock(spec=BackendFactory)
    factory.create.return_value = mock_backend
    return factory

@pytest.fixture
def bridge(mock_factory):
    return TelnetBridge(backend_factory=mock_factory, host="127.0.0.1", port=0)

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
async def test_greet_propagates_exception(bridge, mock_reader, mock_writer):
    mock_writer.write.side_effect = OSError("Network failure")

    with pytest.raises(OSError, match="Network failure"):
        await bridge.greet(mock_reader, mock_writer)