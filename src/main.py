import asyncio
import logging
import docker

from honeypot.connection.telnet import TelnetBridge
from honeypot.container import HoneypotContainer, ContainerConfig, LOCAL_RESOURCES_DIR

# TODO: configure a better logger than the basic config one
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

docker_client = docker.from_env()
TELNET_CONTEXT_PATH = str(LOCAL_RESOURCES_DIR / "telnet")
TELNET_CONTAINER = HoneypotContainer(docker_client, ContainerConfig("telnet"), TELNET_CONTEXT_PATH)
TELNET = {"port": 2323, "container": TELNET_CONTAINER}


async def start_server():
    bridge = TelnetBridge(TELNET["container"])

    server = await asyncio.start_server(
        bridge.handle_client,
        host='0.0.0.0',
        port=TELNET["port"]
    )

    addr = server.sockets[0].getsockname()
    logger.info(f"[*] Telnet Honeypot listening on {addr}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopping...")
