import asyncio
import logging
import docker

from honeypot.connection.telnet import TelnetBridge
from honeypot.container import HoneypotContainer, ContainerConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

docker_client = docker.from_env()
TELNET_CONTAINER = HoneypotContainer(docker_client, ContainerConfig("telnet"))
TELNET = {"port": 2323, "container": TELNET_CONTAINER }

async def start_server():
    async def client_connected_cb(reader, writer):
        bridge = TelnetBridge(TELNET["container"])

        await bridge.handle_client(reader, writer)

    server = await asyncio.start_server(
        client_connected_cb,
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