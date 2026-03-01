import asyncio

from loguru import logger

from honeypot.backends.container_wrapper import LOCAL_RESOURCES_DIR
from honeypot.config import Settings
from honeypot.core.bridge import ProtocolServer
from honeypot.core.builder import BackendBuilder
from honeypot.core.metrics import MetricsManager
from honeypot.core.runner import HoneypotRunner
from honeypot.logger.logger import resolve_log_dir, setup_logging
from honeypot.protocols import BRIDGE_CLASSES


async def start_server() -> None:
    settings = Settings()
    setup_logging(resolve_log_dir(settings.log_dir))
    
    if settings.enable_metrics:
        MetricsManager.start_server(settings.metrics_host, settings.metrics_port)
        
    builder = BackendBuilder(LOCAL_RESOURCES_DIR)

    servers: list[ProtocolServer] = []
    for svc in settings.container_services:
        factory = builder.container(
            svc.protocol.value,
            mem_limit=svc.mem_limit,
            cpu_period=svc.cpu_period,
            cpu_quota=svc.cpu_quota,
            pids_limit=svc.pids_limit,
        )
        bridge_cls = BRIDGE_CLASSES[svc.protocol]
        servers.append(bridge_cls(factory, settings.bind_host, svc.listen_port))

    for svc in settings.proxy_services:
        factory = builder.proxy(svc.target_host, svc.target_port, svc.protocol.value)
        bridge_cls = BRIDGE_CLASSES[svc.protocol]
        servers.append(bridge_cls(factory, settings.bind_host, svc.listen_port))

    await HoneypotRunner(servers).run()


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopping...")
