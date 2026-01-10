from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
import logging

from docker import DockerClient
from docker.errors import ImageNotFound
from docker.models.containers import Container

BASE_DIR = Path(__file__).resolve().parent
LOCAL_RESOURCES_DIR = BASE_DIR / "resources"  # RESOURCES LOCAL PATH CONST

logger = logging.getLogger(__name__)


class HoneypotContainer(ABC):

    def __init__(self, client: DockerClient,
                 context_path: str | None = None) -> None:
        self._client = client
        self._context_path = context_path or LOCAL_RESOURCES_DIR

    @cached_property
    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    @property
    def image_name(self) -> str:
        pass

    @abstractmethod
    def setup(self) -> None:
        pass

    @abstractmethod
    def teardown(self) -> None:
        pass

    def _build_image(self) -> None:
        logger.info(f"getting image: {self.image_name}")
        try:
            self._client.images.get(self.image_name)
        except ImageNotFound:
            logger.info(f"Image not found: {self.image_name}, building...")
            self._client.images.build(path=self._context_path, tag=self.image_name)
