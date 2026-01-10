import logging

from honeypot.container import HoneypotContainer

logger = logging.getLogger(__name__)

class TelnetContainer(HoneypotContainer):

    @property
    def image_name(self) -> str:
        return "telnet"

    def setup(self) -> None:
        self._build_image()
        logger.info(f"[*] Spawning container from {self.image_name}...")
        self._container = self._client.containers.run(
            self.image_name,
            detach=True,
            tty=True,
            stdin_open=True,
        )
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

