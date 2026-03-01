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

    async def start(self, stack: AsyncExitStack) -> asyncio.Server | None:
        self.started = True
        return self.mock_server


@pytest.mark.asyncio
async def test_runner_run(mocker):
    server1 = mocker.Mock(spec=asyncio.Server)
    server1.serve_forever = mocker.AsyncMock()
    
    server2 = mocker.Mock(spec=asyncio.Server)
    server2.serve_forever = mocker.AsyncMock()

    dummy_1 = DummyServer(server1)
    dummy_2 = DummyServer(None)
    dummy_3 = DummyServer(server2)

    runner = HoneypotRunner(servers=[dummy_1, dummy_2, dummy_3])
    await runner.run()

    assert dummy_1.started
    assert dummy_2.started
    assert dummy_3.started

    server1.serve_forever.assert_awaited_once()
    server2.serve_forever.assert_awaited_once()
