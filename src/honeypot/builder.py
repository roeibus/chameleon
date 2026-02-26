from pathlib import Path

import docker
from docker import DockerClient

from honeypot.containers.backend import ContainerBackend
from honeypot.containers.config import ContainerConfig
from honeypot.containers.wrapper import LOCAL_RESOURCES_DIR, ContainerWrapper
from honeypot.proxy.stream_backend import StreamBackend

SOCKET_PARAMS = {"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1}

# TODO: replace this builder with a bridge builder that does the building from 0 - 100


class BackendBuilder:
    def __init__(
        self,
        docker_client: DockerClient | None = None,
        resources_dir: Path | None = None,
    ) -> None:
        self._docker_client: DockerClient = docker_client or docker.from_env()
        self._resources_dir: Path = resources_dir or LOCAL_RESOURCES_DIR

    def container(self, name: str = "telnet") -> ContainerBackend:
        """Creates a ContainerBackend for the named resource folder."""
        context = str(self._resources_dir / name)
        c = ContainerWrapper(self._docker_client, ContainerConfig(name), context)
        return ContainerBackend(c, SOCKET_PARAMS)

    def proxy(self, host: str, port: int = 80) -> StreamBackend:
        return StreamBackend(host, port)
