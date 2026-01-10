import logging
import os
from abc import ABC, abstractmethod

from docker import DockerClient
from docker.errors import ImageNotFound

logger = logging.getLogger(__name__)

class Container(ABC):

    def __init__(self, client: DockerClient) -> None:
        self._client = client

    @abstractmethod
    @property
    def image_name(self) -> str:
        ...

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
            self._client.images.build(path=os.getcwd(), tag=self.image_name)

os.getcwd()