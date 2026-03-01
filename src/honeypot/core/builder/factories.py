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
        self,
        docker_client: DockerClient,
        resources_dir: Path,
        name: str,
        *,
        mem_limit: str | None = None,
        cpu_period: int | None = None,
        cpu_quota: int | None = None,
        pids_limit: int | None = None,
    ) -> None:
        self._docker_client: DockerClient = docker_client
        self._resources_dir: Path = resources_dir
        self._name: str = name
        self._mem_limit: str | None = mem_limit
        self._cpu_period: int | None = cpu_period
        self._cpu_quota: int | None = cpu_quota
        self._pids_limit: int | None = pids_limit

    @override
    def create(self) -> Backend:
        context = str(self._resources_dir / self._name)
        config = ContainerConfig(
            self._name,
            mem_limit=self._mem_limit,
            cpu_period=self._cpu_period,
            cpu_quota=self._cpu_quota,
            pids_limit=self._pids_limit,
        )
        wrapper = ContainerWrapper(self._docker_client, config, context)
        return ContainerBackend(wrapper, self._name)


class ProxyBackendFactory(BackendFactory):
    def __init__(self, host: str, port: int, name: str = "http_proxy") -> None:
        self._host: str = host
        self._port: int = port
        self._name: str = name

    @override
    def create(self) -> Backend:
        return StreamBackend(self._host, self._port, self._name)
