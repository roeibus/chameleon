import asyncio

import pytest

from tests.integration.conftest import docker_skip


pytestmark = [pytest.mark.integration, docker_skip]


@pytest.mark.asyncio
async def test_read_write_roundtrip(container_backend_factory):
    backend = container_backend_factory.create()
    async with asyncio.timeout(15):
        async with backend:
            await backend.write(b"echo hello\n")
            output = b""
            while b"hello" not in output:
                chunk = await backend.read(4096)
                assert chunk, "Backend returned empty read before expected output"
                output += chunk


@pytest.mark.asyncio
async def test_container_cleanup_on_exit(container_backend_factory, docker_client):
    backend = container_backend_factory.create()
    async with asyncio.timeout(15):
        async with backend:
            container_id = backend._container.inner_container.short_id
            await backend.write(b"echo hi\n")
            await asyncio.sleep(0.5)

    # After exiting, the container should be gone
    containers = docker_client.containers.list(all=True, filters={"id": container_id})
    assert len(containers) == 0, f"Container {container_id} was not cleaned up"


@pytest.mark.asyncio
async def test_container_cleanup_on_error(container_backend_factory, docker_client):
    container_id = None
    with pytest.raises(RuntimeError, match="intentional"):
        async with asyncio.timeout(15):
            backend = container_backend_factory.create()
            async with backend:
                container_id = backend._container.inner_container.short_id
                raise RuntimeError("intentional")

    assert container_id is not None
    containers = docker_client.containers.list(all=True, filters={"id": container_id})
    assert len(containers) == 0, f"Container {container_id} was not cleaned up"
