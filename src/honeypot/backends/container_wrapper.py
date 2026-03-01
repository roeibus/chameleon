import typing as t
from dataclasses import asdict
from pathlib import Path
from socket import socket

from docker import DockerClient
from docker.errors import APIError, ImageNotFound, NotFound
from docker.models.containers import Container
from loguru import logger

from honeypot.backends.container_config import ContainerConfig
from honeypot.core.exceptions import ContainerNotInitializedError

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
LOCAL_RESOURCES_DIR = BASE_DIR / "resources"


class ContainerWrapper[Config: ContainerConfig = ContainerConfig]:
    def __init__(self, client: DockerClient, config: Config, context_path: str) -> None:
        self._client: DockerClient = client
        self._config: Config = config
        self._context_path: str = context_path
        self._inner_container: Container | None = None

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def config(self) -> Config:
        return self._config

    @property
    def inner_container(self) -> Container:
        if self._inner_container is None:
            raise ContainerNotInitializedError("Inner container is not initialized.")
        return self._inner_container

    def attach_socket(self, **kwargs: dict[str, int]) -> socket:
        sock_obj = self.inner_container.attach_socket(**kwargs)
        return t.cast(socket, sock_obj._sock)  # pyright: ignore[reportAttributeAccessIssue]

    def setup(self) -> None:
        logger.info("[+] Container Setup was called...")
        self._build_image()
        logger.info(f"[*] Spawning container from {self.config.image}...")
        self._inner_container = self._client.containers.run(**asdict(self.config))
        logger.info(
            f"[+] Container {self.inner_container.short_id} spawned successfully."
        )

    def teardown(self) -> None:
        logger.info("[-] Container Teardown was called...")
        if self._inner_container:
            try:
                logger.info(f"[-] Nuking container {self.inner_container.short_id}...")
                self.inner_container.kill()
                self.inner_container.remove()
            except (APIError, NotFound) as e:
                logger.error(f"Error during removal: {e}")
            finally:
                self._inner_container = None
        else:
            logger.debug("[-] Teardown called, but container does not exist.")

    def _build_image(self) -> None:
        logger.info(f"getting image: {self.config.image}")
        try:
            _ = self._client.images.get(self.config.image)
        except ImageNotFound:
            logger.info(f"Image not found: {self.config.image}, building...")
            _ = self._client.images.build(
                path=self._context_path,
                tag=self.config.image,
            )
