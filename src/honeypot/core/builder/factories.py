from pathlib import Path
from typing import override

from docker import DockerClient

from honeypot.backends.container_backend import ContainerBackend
from honeypot.backends.container_config import ContainerConfig
from honeypot.backends.container_wrapper import ContainerWrapper
from honeypot.backends.stream_backend import StreamBackend
from honeypot.core.backend import Backend, BackendFactory


class ContainerBackendFactory(BackendFactory):
    def __init__(
        self, docker_client: DockerClient, resources_dir: Path, name: str
    ) -> None:
        self._docker_client: DockerClient = docker_client
        self._resources_dir: Path = resources_dir
        self._name: str = name

    @override
    def create(self) -> Backend:
        context = str(self._resources_dir / self._name)
        wrapper = ContainerWrapper(
            self._docker_client, ContainerConfig(self._name), context
        )
        return ContainerBackend(wrapper)


class ProxyBackendFactory(BackendFactory):
    def __init__(self, host: str, port: int) -> None:
        self._host: str = host
        self._port: int = port

    @override
    def create(self) -> Backend:
        return StreamBackend(self._host, self._port)
