import asyncio
from contextlib import AsyncExitStack

import pytest

from honeypot.core.bridge import ProtocolServer
from honeypot.core.runner import HoneypotRunner


class DummyServer(ProtocolServer):
    def __init__(self, mock_server):
        super().__init__(None, "127.0.0.1", 0)  # type: ignore
        self.mock_server = mock_server
        self.started = False

    @property
    def protocol(self) -> str:
        return "dummy"

    async def start(self, stack: AsyncExitStack) -> asyncio.Server | None:
        self.started = True
        return self.mock_server


@pytest.mark.asyncio
async def test_runner_starts_all_servers_and_calls_serve_forever(mocker):
    runner = HoneypotRunner(servers=[])  # placeholder; reassigned below

    server1 = mocker.Mock(spec=asyncio.Server)
    server2 = mocker.Mock(spec=asyncio.Server)

    # server1.serve_forever triggers shutdown so the runner exits cleanly
    async def serve_and_stop():
        runner.stop()

    server1.serve_forever = serve_and_stop
    server2.serve_forever = mocker.AsyncMock()

    dummy_1 = DummyServer(server1)
    dummy_2 = DummyServer(None)  # simulates SSH (returns None)
    dummy_3 = DummyServer(server2)

    runner._servers = [dummy_1, dummy_2, dummy_3]

    async with AsyncExitStack() as stack:
        await runner.run(stack)

    assert dummy_1.started
    assert dummy_2.started
    assert dummy_3.started


@pytest.mark.asyncio
async def test_runner_restarts_after_crash(mocker):
    runner = HoneypotRunner(servers=[])

    call_count = 0
    server = mocker.Mock(spec=asyncio.Server)
    server.close = mocker.Mock()

    async def flaky_serve():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("bind failed")
        runner.stop()  # succeed on second attempt, then stop

    server.serve_forever = flaky_serve
    dummy = DummyServer(server)
    runner._servers = [dummy]

    async with AsyncExitStack() as stack:
        await runner.run(stack)

    assert call_count == 2  # crashed once, restarted once
    server.close.assert_called_once()  # old server closed before retry
