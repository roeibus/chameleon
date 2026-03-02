import asyncio
from pathlib import Path

import docker
from docker import DockerClient

from honeypot.backends.container_wrapper import LOCAL_RESOURCES_DIR
from honeypot.core.builder.factories import ContainerBackendFactory, ProxyBackendFactory


class BackendBuilder:
    def __init__(
        self,
        resources_dir: Path | None = None,
        docker_client: DockerClient | None = None,
    ) -> None:
        self._docker_client: DockerClient | None = docker_client
        self._resources_dir: Path = resources_dir or LOCAL_RESOURCES_DIR
        self._container_factories: list[ContainerBackendFactory] = []

    @property
    def docker_client(self) -> DockerClient:
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    def container(
        self,
        name: str = "telnet",
        *,
        mem_limit: str | None = None,
        cpu_period: int | None = None,
        cpu_quota: int | None = None,
        pids_limit: int | None = None,
    ) -> ContainerBackendFactory:
        factory = ContainerBackendFactory(
            self.docker_client,
            self._resources_dir,
            name,
            mem_limit=mem_limit,
            cpu_period=cpu_period,
            cpu_quota=cpu_quota,
            pids_limit=pids_limit,
        )
        self._container_factories.append(factory)
        return factory

    async def pre_build_images(self) -> None:
        unique = list({f.name: f for f in self._container_factories}.values())
        await asyncio.gather(*(asyncio.to_thread(f.ensure_image) for f in unique))

    def proxy(
        self, host: str, port: int = 80, name: str = "http_proxy"
    ) -> ProxyBackendFactory:
        return ProxyBackendFactory(host, port, name)
