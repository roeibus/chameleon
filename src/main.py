import asyncio

import docker
from loguru import logger

from honeypot.core.builder import BackendBuilder
from honeypot.protocols.telnet import TelnetBridge
from honeypot.backends.container_wrapper import LOCAL_RESOURCES_DIR
from honeypot.logger.logger import resolve_log_dir, setup_logging
from honeypot.protocols.http_proxy import HttpProxyBridge

docker_client = docker.from_env()
IOT_HOST = "192.168.1.1"
IOT_HTTP_PORT = 80
HTTP_PORT = 8080
TELNET_PORT = 2323


async def start_server():
    setup_logging(resolve_log_dir())
    builder = BackendBuilder(docker_client, LOCAL_RESOURCES_DIR)
    telnet_bridge = TelnetBridge(backend=builder.container("telnet"))
    http_bridge = HttpProxyBridge(backend=builder.proxy(IOT_HOST, IOT_HTTP_PORT))

    telnet_server = await asyncio.start_server(
        telnet_bridge.handle_client, host="0.0.0.0", port=TELNET_PORT
    )
    http_server = await asyncio.start_server(
        http_bridge.handle_client, host="0.0.0.0", port=HTTP_PORT
    )

    telnet_addr = telnet_server.sockets[0].getsockname()
    logger.info(f"[*] Telnet Honeypot listening on {telnet_addr}")
    http_addr = http_server.sockets[0].getsockname()
    logger.info(f"[*] HTTP Proxy Honeypot listening on {http_addr}")

    async with telnet_server, http_server:
        await asyncio.gather(  # pyright: ignore[reportUnusedCallResult]
            telnet_server.serve_forever(),
            http_server.serve_forever()
        )


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopping...")
