from pathlib import Path

import docker
from docker import DockerClient

from honeypot.backends.container_backend import ContainerBackend
from honeypot.backends.container_config import ContainerConfig
from honeypot.backends.container_wrapper import LOCAL_RESOURCES_DIR, ContainerWrapper
from honeypot.backends.stream_backend import StreamBackend

SOCKET_PARAMS = {"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1}


class BackendBuilder:
    def __init__(
        self,
        resources_dir: Path | None = None,
        docker_client: DockerClient | None = None,
    ) -> None:
        self._docker_client: DockerClient | None = docker_client
        self._resources_dir: Path = resources_dir or LOCAL_RESOURCES_DIR

    @property
    def docker_client(self) -> DockerClient:
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    def container(self, name: str = "telnet") -> ContainerBackend:
        """Creates a ContainerBackend for the named resource folder."""
        context = str(self._resources_dir / name)
        wrapper = ContainerWrapper(self.docker_client, ContainerConfig(name), context)
        return ContainerBackend(wrapper, SOCKET_PARAMS)

    def proxy(self, host: str, port: int = 80) -> StreamBackend:
        return StreamBackend(host, port)
