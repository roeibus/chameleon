import asyncio
from contextlib import AsyncExitStack

import docker
from loguru import logger

from honeypot.backends.container_wrapper import LOCAL_RESOURCES_DIR
from honeypot.config import Settings
from honeypot.core.builder import BackendBuilder
from honeypot.logger.logger import resolve_log_dir, setup_logging
from honeypot.protocols.http_proxy import HttpProxyBridge
from honeypot.protocols.ssh import SshBridge
from honeypot.protocols.telnet import TelnetBridge


async def start_server():
    settings = Settings()
    setup_logging(resolve_log_dir(settings.log_dir))
    docker_client = docker.from_env()
    builder = BackendBuilder(docker_client, LOCAL_RESOURCES_DIR)
    telnet_bridge = TelnetBridge(backend=builder.container("telnet"))
    ssh_bridge = SshBridge(backend=builder.container("ssh"))

    telnet_server = await asyncio.start_server(
        telnet_bridge.handle_client,
        host=settings.bind_host,
        port=settings.telnet_port,
    )
    # asyncssh manages its own listener; starts serving immediately.
    ssh_server = await ssh_bridge.start_server(
        host=settings.bind_host, port=settings.ssh_port
    )

    http_servers: list[asyncio.Server] = []
    for device in settings.devices:
        bridge = HttpProxyBridge(
            backend=builder.proxy(device.target_host, device.target_port)
        )
        server = await asyncio.start_server(
            bridge.handle_client,
            host=settings.bind_host,
            port=device.listen_port,
        )
        addr = server.sockets[0].getsockname()
        label = device.name or device.target_host
        logger.info(f"[*] HTTP Proxy ({label}) listening on {addr}")
        http_servers.append(server)

    telnet_addr = telnet_server.sockets[0].getsockname()
    logger.info(f"[*] Telnet Honeypot listening on {telnet_addr}")
    ssh_addrs = ssh_server.get_addresses()
    logger.info(f"[*] SSH Honeypot listening on {ssh_addrs}")

    try:
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(telnet_server)
            for s in http_servers:
                await stack.enter_async_context(s)
            await asyncio.gather(
                telnet_server.serve_forever(),
                *(s.serve_forever() for s in http_servers),
            )
    finally:
        ssh_server.close()
        await ssh_server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopping...")
