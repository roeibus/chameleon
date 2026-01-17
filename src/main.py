import asyncio
import docker
from loguru import logger

from honeypot.containers.telnet_bridge import TelnetBridge
from honeypot.container import HoneypotContainer, ContainerConfig, LOCAL_RESOURCES_DIR
from honeypot.logger.logger import setup_logging

docker_client = docker.from_env()
TELNET_CONTEXT_PATH = str(LOCAL_RESOURCES_DIR / "telnet")
TELNET_CONTAINER = HoneypotContainer(docker_client, ContainerConfig("telnet"), TELNET_CONTEXT_PATH)
TELNET = {"port": 2323, "container": TELNET_CONTAINER}


async def start_server():
    setup_logging()
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
