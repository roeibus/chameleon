import asyncio
from contextlib import AsyncExitStack
import asyncssh
import pytest
from honeypot.protocols.ssh import SshBridge
from honeypot.core.metrics import MetricsManager
from tests.integration.conftest import free_port

@pytest.mark.asyncio
async def test_ssh_max_connections(container_backend_factory):
    port = free_port()
    # Set max_connections to 1
    max_conn = 1
    bridge = SshBridge(
        backend_factory=container_backend_factory,
        host="127.0.0.1",
        port=port,
        max_connections=max_conn,
    )

    async with AsyncExitStack() as stack:
        await bridge.start(stack)

        # First connection should succeed
        conn1 = await asyncssh.connect(
            "127.0.0.1",
            port=port,
            username="admin",
            password="secret",
            known_hosts=None,
        )
        process1 = await conn1.create_process(encoding=None)
        
        # Second connection should be rejected
        # In our implementation, rejection means the process exits with exit status 1
        conn2 = await asyncssh.connect(
            "127.0.0.1",
            port=port,
            username="user2",
            password="other",
            known_hosts=None,
        )
        process2 = await conn2.create_process(encoding=None)
        
        # We expect process2 to fail because it hit the semaphore limit
        # Wait for a small amount of time to allow the rejection to happen
        await asyncio.sleep(0.5)
        
        assert process2.exit_status == 1
        
        # Cleanup
        process1.terminate()
        await process1.wait()
        conn1.close()
        await conn1.wait_closed()
        
        conn2.close()
        await conn2.wait_closed()
