
import asyncio
import pytest
from honeypot.core.bridge.session import SessionBridge
from honeypot.config import Protocol

class MockBridge(SessionBridge):
    @property
    def protocol(self) -> Protocol:
        return Protocol.TELNET

    async def _handle_client(self, reader, writer) -> None:
        await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_session_bridge_max_connections_cleanup(mocker):
    # Mock dependencies
    backend_factory = mocker.MagicMock()
    
    # Create bridge with max_connections=1
    bridge = MockBridge(backend_factory, "127.0.0.1", 0, max_connections=1)
    
    # Mock writer
    mock_writer = mocker.MagicMock(spec=asyncio.StreamWriter)
    mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
    mock_writer.wait_closed = mocker.AsyncMock()
    mock_reader = mocker.MagicMock(spec=asyncio.StreamReader)
    
    # First connection should succeed
    # We need to run it in a task because it sleeps
    task1 = asyncio.create_task(bridge.handle_client(mock_reader, mock_writer))
    await asyncio.sleep(0.01) # Give it time to acquire semaphore
    
    # Second connection should be rejected
    mock_writer2 = mocker.MagicMock(spec=asyncio.StreamWriter)
    mock_writer2.get_extra_info.return_value = ("127.0.0.1", 12346)
    mock_writer2.wait_closed = mocker.AsyncMock()
    mock_reader2 = mocker.MagicMock(spec=asyncio.StreamReader)
    
    await bridge.handle_client(mock_reader2, mock_writer2)
    
    # Verify rejection cleanup
    mock_writer2.close.assert_called_once()
    mock_writer2.wait_closed.assert_awaited_once()
    
    await task1
    mock_writer.close.assert_called_once()
