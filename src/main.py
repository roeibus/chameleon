import asyncio

import docker
from loguru import logger

from honeypot.config import Settings
from honeypot.core.builder import BackendBuilder
from honeypot.protocols.telnet import TelnetBridge
from honeypot.protocols.ssh import SshBridge
from honeypot.backends.container_wrapper import LOCAL_RESOURCES_DIR
from honeypot.logger.logger import resolve_log_dir, setup_logging
from honeypot.protocols.http_proxy import HttpProxyBridge


async def start_server():
    settings = Settings()
    setup_logging(resolve_log_dir(settings.log_dir))
    docker_client = docker.from_env()
    builder = BackendBuilder(docker_client, LOCAL_RESOURCES_DIR)
    telnet_bridge = TelnetBridge(backend=builder.container("telnet"))
    http_bridge = HttpProxyBridge(
        backend=builder.proxy(settings.iot_host, settings.iot_http_port)
    )
    ssh_bridge = SshBridge(backend=builder.container("ssh"))

    telnet_server = await asyncio.start_server(
        telnet_bridge.handle_client,
        host=settings.bind_host,
        port=settings.telnet_port,
    )
    http_server = await asyncio.start_server(
        http_bridge.handle_client,
        host=settings.bind_host,
        port=settings.http_port,
    )
    # asyncssh manages its own listener; starts serving immediately.
    ssh_server = await ssh_bridge.start_server(
        host=settings.bind_host, port=settings.ssh_port
    )

    telnet_addr = telnet_server.sockets[0].getsockname()
    logger.info(f"[*] Telnet Honeypot listening on {telnet_addr}")
    http_addr = http_server.sockets[0].getsockname()
    logger.info(f"[*] HTTP Proxy Honeypot listening on {http_addr}")
    ssh_addrs = ssh_server.get_addresses()
    logger.info(f"[*] SSH Honeypot listening on {ssh_addrs}")

    try:
        async with telnet_server, http_server:
            await asyncio.gather(  # pyright: ignore[reportUnusedCallResult]
                telnet_server.serve_forever(), http_server.serve_forever()
            )
    finally:
        ssh_server.close()
        await ssh_server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopping...")
