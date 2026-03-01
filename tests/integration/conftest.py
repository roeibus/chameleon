import asyncio
import socket
from pathlib import Path

import docker
import pytest
import pytest_asyncio
from docker import DockerClient
from docker.errors import DockerException

from honeypot.core.builder import ContainerBackendFactory

RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "resources"


def is_docker_available() -> bool:
    try:
        client = docker.from_env()
        client.ping()
        return True
    except (DockerException, Exception):
        return False


DOCKER_AVAILABLE = is_docker_available()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


docker_skip = pytest.mark.skipif(
    not DOCKER_AVAILABLE, reason="Docker daemon not available"
)


@pytest.fixture(scope="session")
def docker_client() -> DockerClient:
    return docker.from_env()


@pytest.fixture
def container_backend_factory(docker_client: DockerClient) -> ContainerBackendFactory:
    return ContainerBackendFactory(
        docker_client,
        RESOURCES_DIR,
        "telnet",
        mem_limit="128m",
        cpu_period=100000,
        cpu_quota=50000,
        pids_limit=64,
    )


@pytest_asyncio.fixture
async def echo_tcp_server():
    async def handle_echo(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    port = free_port()
    server = await asyncio.start_server(handle_echo, "127.0.0.1", port)
    async with server:
        yield ("127.0.0.1", port)
