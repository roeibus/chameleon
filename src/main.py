import asyncio
from contextlib import AsyncExitStack

from loguru import logger

from honeypot.config import Settings
from honeypot.core.bridge import ProtocolServer
from honeypot.core.builder import BackendBuilder
from honeypot.core.metrics import MetricsManager
from honeypot.core.runner import HoneypotRunner
from honeypot.logger.logger import resolve_log_dir, setup_logging
from honeypot.protocols import BRIDGE_CLASSES
from honeypot.utils.docker_utils import cleanup_stale_containers, pre_build_images


async def start_server() -> None:
    settings = Settings()
    setup_logging(resolve_log_dir(settings.log_dir))

    async with AsyncExitStack() as stack:
        if settings.enable_metrics:
            await MetricsManager.start_server(
                settings.metrics_host, settings.metrics_port, stack
            )

        builder = BackendBuilder()
        servers: list[ProtocolServer] = []

        for svc in settings.container_services:
            bridge_cls = BRIDGE_CLASSES.get(svc.protocol)
            if bridge_cls is None:
                raise ValueError(f"No bridge registered for protocol {svc.protocol!r}")
            factory = builder.container(
                svc.protocol.value,
                mem_limit=svc.mem_limit,
                cpu_period=svc.cpu_period,
                cpu_quota=svc.cpu_quota,
                pids_limit=svc.pids_limit,
            )
            servers.append(
                bridge_cls(
                    factory, settings.bind_host, svc.listen_port, svc.max_connections
                )
            )

        for svc in settings.proxy_services:
            bridge_cls = BRIDGE_CLASSES.get(svc.protocol)
            if bridge_cls is None:
                raise ValueError(f"No bridge registered for protocol {svc.protocol!r}")
            factory = builder.proxy(
                svc.target_host, svc.target_port, svc.protocol.value
            )
            servers.append(
                bridge_cls(
                    factory, settings.bind_host, svc.listen_port, svc.max_connections
                )
            )

        await cleanup_stale_containers(builder.docker_client)
        await pre_build_images(builder.container_factories)
        await HoneypotRunner(servers).run(stack)


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopping...")
