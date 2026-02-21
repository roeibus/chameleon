from dataclasses import asdict
from pathlib import Path
from loguru import logger
from docker import DockerClient
from docker.errors import APIError, ImageNotFound, NotFound
from docker.models.containers import Container

from honeypot.containers.config import ContainerConfig

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_RESOURCES_DIR = BASE_DIR / "resources"


class HoneypotContainer[Config: ContainerConfig]:

    def __init__(self,
                 client: DockerClient,
                 config: Config,
                 context_path: str) -> None:
        self._client = client
        self._config = config
        self._context_path = context_path
        self._container: Container | None = None

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def config(self) -> Config:
        return self._config

    def attach_socket(self, **kwargs):
        return self._container.attach_socket(**kwargs)

    def setup(self) -> None:
        logger.info("[+] Container Setup was called...")
        self._build_image()
        logger.info(f"[*] Spawning container from {self.config.image}...")
        self._container = self._client.containers.run(**asdict(self.config))
        logger.info(f"[+] Container {self._container.short_id} spawned successfully.")

    def teardown(self) -> None:
        logger.info("[-] Container Teardown was called...")
        if self._container:
            try:
                logger.info(f"[-] Nuking container {self._container.short_id}...")
                self._container.kill()
                self._container.remove()
            except (APIError, NotFound) as e:
                logger.error(f"Error during removal: {e}")
            finally:
                self._container = None
        else:
            logger.debug("[-] Teardown called, but container does not exist.")

    def _build_image(self) -> None:
        logger.info(f"getting image: {self.config.image}")
        try:
            self._client.images.get(self.config.image)
        except ImageNotFound:
            logger.info(f"Image not found: {self.config.image}, building...")
            _ = self._client.images.build(path=self._context_path,
                                      tag=self.config.image, )
