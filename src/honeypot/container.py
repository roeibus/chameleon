from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
import logging

from docker import DockerClient
from docker.errors import ImageNotFound
from docker.models.containers import Container

BASE_DIR = Path(__file__).resolve().parent
LOCAL_RESOURCES_DIR = str(BASE_DIR / "resources")  # RESOURCES LOCAL PATH CONST

logger = logging.getLogger(__name__)


@dataclass
class ContainerConfig:
    image_name: str
    detach: bool = True
    tty: bool = True
    stdin_open: bool = True
    network_disabled: bool = False


class HoneypotContainer[Config: ContainerConfig](ABC):

    def __init__(self, client: DockerClient,
                 container_config: ContainerConfig | None = None,
                 context_path: str | None = None) -> None:
        self._client = client
        self._config = container_config
        self._context_path = context_path or LOCAL_RESOURCES_DIR
        self._container: Container | None = None  # none means doesn't exist

    @cached_property
    @abstractmethod
    def config(self) -> ContainerConfig:
        pass

    @abstractmethod
    def setup(self) -> None:
        pass

    @abstractmethod
    def teardown(self) -> None:
        pass

    def _build_image(self) -> None:
        logger.info(f"getting image: {self.config.image_name}")
        try:
            self._client.images.get(self.config.image_name)
        except ImageNotFound:
            logger.info(f"Image not found: {self.config.image_name}, building...")
            self._client.images.build(path=self._context_path,
                                      tag=self.config.image_name)
