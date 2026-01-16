from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger
from docker import DockerClient
from docker.errors import ImageNotFound
from docker.models.containers import Container

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_RESOURCES_DIR = BASE_DIR / "resources"  # RESOURCES LOCAL PATH CONST


@dataclass
class ContainerConfig:
    image: str
    detach: bool = True
    tty: bool = True
    stdin_open: bool = True
    network_disabled: bool = False


class HoneypotContainer[Config: ContainerConfig]:

    def __init__(self,
                 client: DockerClient,
                 config: Config,
                 context_path: str) -> None:
        self._client = client
        self._config = config
        self._context_path = context_path
        self._container: Container | None = None  # none means doesn't exist

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def config(self) -> Config:
        return self._config

    def attach_socket(self, **kwargs):
        return self._container.attach_socket(**kwargs)

    def setup(self) -> None:
        self._build_image()
        logger.info(f"[*] Spawning container from {self.config.image}...")
        self._container = self._client.containers.run(**asdict(self.config))
        logger.info(f"[+] Container {self._container.short_id} spawned successfully.")

    def teardown(self) -> None:

        if self._container:
            try:
                logger.info(f"[-] Nuking container {self._container.short_id}...")
                self._container.kill()
                self._container.remove()
            except Exception as e:
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
            self._client.images.build(path=self._context_path,
                                      tag=self.config.image, )
