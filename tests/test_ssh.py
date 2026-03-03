import asyncio
import pytest

from honeypot.config import Protocol
from honeypot.core.backend import Backend, BackendFactory
from honeypot.core.bridge.relay import forward_input, forward_output
from honeypot.protocols.ssh import SshBridge, _PasswordAuthServer


# ── _PasswordAuthServer ──────────────────────────────────────────────


class TestPasswordAuthServer:
    def test_password_auth_supported(self):
        server = _PasswordAuthServer()
        assert server.password_auth_supported() is True

    def test_validate_password_always_accepts(self):
        server = _PasswordAuthServer()
        assert server.validate_password("root", "toor") is True




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
    return SshBridge(backend_factory=mock_factory, host="127.0.0.1", port=0)


@pytest.fixture
def mock_process(mocker):
    """Fake SSHServerProcess with stdin/stdout stubs."""
    process = mocker.Mock()
    process.get_extra_info.return_value = ("192.168.1.10", 4321)

    # stdin: async read
    stdin = mocker.AsyncMock()
    stdin.read.return_value = b""
    process.stdin = stdin

    # stdout: sync write, async drain
    stdout = mocker.Mock()
    stdout.drain = mocker.AsyncMock()
    process.stdout = stdout

    process.exit = mocker.Mock()
    return process


# ── relay.forward_input ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_forward_input_sends_to_backend(mock_backend, mock_process):
    mock_process.stdin.read.side_effect = [b"whoami\n", b""]

    async with asyncio.timeout(1.0):
        await forward_input(mock_process.stdin, mock_backend, Protocol.SSH)

    mock_backend.write.assert_awaited_with(b"whoami\n")


@pytest.mark.asyncio
async def test_forward_input_stops_on_empty(mock_backend, mock_process):
    mock_process.stdin.read.side_effect = [b""]

    async with asyncio.timeout(1.0):
        await forward_input(mock_process.stdin, mock_backend, Protocol.SSH)

    mock_backend.write.assert_not_awaited()


@pytest.mark.asyncio
async def test_forward_input_multiple_reads(mock_backend, mock_process):
    mock_process.stdin.read.side_effect = [b"cmd1\n", b"cmd2\n", b""]

    async with asyncio.timeout(1.0):
        await forward_input(mock_process.stdin, mock_backend, Protocol.SSH)

    assert mock_backend.write.await_count == 2


# ── relay.forward_output ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_forward_output_writes_to_process(mock_backend, mock_process):
    mock_backend.read.side_effect = [b"output data", b""]

    async with asyncio.timeout(1.0):
        await forward_output(mock_process.stdout, mock_backend, Protocol.SSH)

    mock_process.stdout.write.assert_called_with(b"output data")


@pytest.mark.asyncio
async def test_forward_output_drains_stdout(mock_backend, mock_process):
    mock_backend.read.side_effect = [b"data", b""]

    async with asyncio.timeout(1.0):
        await forward_output(mock_process.stdout, mock_backend, Protocol.SSH)

    mock_process.stdout.drain.assert_awaited()


@pytest.mark.asyncio
async def test_forward_output_stops_on_empty(mock_backend, mock_process):
    mock_backend.read.side_effect = [b""]

    async with asyncio.timeout(1.0):
        await forward_output(mock_process.stdout, mock_backend, Protocol.SSH)

    mock_process.stdout.write.assert_not_called()


# ── SshBridge._handle_session ────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_session_enters_backend(bridge, mock_backend, mock_process):
    await bridge._handle_session(mock_process)
    mock_backend.__aenter__.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_session_exits_backend(bridge, mock_backend, mock_process):
    await bridge._handle_session(mock_process)
    mock_backend.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_session_calls_process_exit(bridge, mock_backend, mock_process):
    await bridge._handle_session(mock_process)
    mock_process.exit.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_handle_session_catches_os_error(bridge, mock_backend, mock_process):
    mock_backend.__aenter__.side_effect = OSError("boom")
    await bridge._handle_session(mock_process)
    mock_process.exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_handle_session_catches_eof_error(bridge, mock_backend, mock_process):
    mock_backend.__aenter__.side_effect = EOFError("eof")
    await bridge._handle_session(mock_process)
    mock_process.exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_handle_session_no_peername_defaults_unknown(
    bridge, mock_backend, mock_process
):
    mock_process.get_extra_info.return_value = None
    # Should not raise — just uses "UNKNOWN" for IP.
    await bridge._handle_session(mock_process)
    mock_process.exit.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_handle_session_full_data_flow(bridge, mock_backend, mock_process):
    mock_process.stdin.read.side_effect = [b"id\n", b""]
    mock_backend.read.side_effect = [b"uid=0(root)", b""]

    await bridge._handle_session(mock_process)

    mock_backend.write.assert_awaited_with(b"id\n")
    mock_process.stdout.write.assert_called_with(b"uid=0(root)")


@pytest.mark.asyncio
async def test_start_server(bridge, mocker):
    mock_ssh_server = mocker.Mock()
    mock_ssh_server.get_addresses.return_value = [("127.0.0.1", 2222)]

    mock_create_server = mocker.patch(
        "asyncssh.create_server", new_callable=mocker.AsyncMock
    )
    mock_create_server.return_value = mock_ssh_server

    stack = mocker.Mock()

    result = await bridge.start(stack)

    assert result is None
    mock_create_server.assert_awaited_once()
    kwargs = mock_create_server.call_args.kwargs
    assert kwargs["server_host_keys"] == [bridge._host_key]
    assert kwargs["process_factory"] == bridge._handle_session

    stack.push_async_callback.assert_called_once_with(mock_ssh_server.wait_closed)
    stack.callback.assert_called_once_with(mock_ssh_server.close)
