import asyncio

import typing as t

from docker import DockerClient
from docker.errors import APIError
from loguru import logger

if t.TYPE_CHECKING:
    from honeypot.core.builder.factories import ContainerBackendFactory


async def cleanup_stale_containers(client: DockerClient) -> None:
    """Kill and remove any containers left over from a previous run."""
    containers = await asyncio.to_thread(
        client.containers.list,
        all=True,
        filters={"label": "chameleon=true"},
    )
    if not containers:
        logger.info("[*] No stale chameleon containers found.")
        return
    logger.info(f"[*] Found {len(containers)} stale container(s), cleaning up...")
    for container in containers:
        try:
            await asyncio.to_thread(container.kill)
        except APIError:
            pass
        try:
            await asyncio.to_thread(container.remove)
            logger.info(f"[-] Removed stale container {container.short_id}.")
        except APIError as e:
            logger.warning(f"Failed to remove container {container.short_id}: {e}")


async def pre_build_images(factories: list["ContainerBackendFactory"]) -> None:
    """
    Eagerly build Docker images for all container factories
    before accepting connections.
    """
    unique = list({f.name: f for f in factories}.values())
    await asyncio.gather(*(asyncio.to_thread(f.ensure_image) for f in unique))