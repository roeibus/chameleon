import asyncio
from asyncio import StreamReader, StreamWriter
from contextlib import AsyncExitStack

from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

from honeypot.utils import close_writer


class MetricsManager:
    # Connection metrics
    ACTIVE_SESSIONS: Gauge = Gauge(
        "chameleon_active_sessions",
        "Active honeypot sessions",
        ["protocol"],
    )
    CONNECTIONS_TOTAL: Counter = Counter(
        "chameleon_connections_total",
        "Total connections",
        ["protocol", "status"],
    )
    BYTES_TRANSFERRED: Counter = Counter(
        "chameleon_bytes_total",
        "Bytes transferred",
        ["protocol", "direction"],
    )

    # Backend health metrics
    BACKEND_UP: Gauge = Gauge(
        "chameleon_backend_up",
        "Backend status (1=up, 0=down)",
        ["protocol", "type"],
    )

    @classmethod
    async def _handle_metrics(cls, _reader: StreamReader, writer: StreamWriter) -> None:
        try:
            content = generate_latest()
            header = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {CONTENT_TYPE_LATEST}\r\n"
                f"Content-Length: {len(content)}\r\n"
                f"Connection: close\r\n\r\n"
            )
            writer.write(header.encode())
            writer.write(content)
            await writer.drain()
        except Exception as e:
            logger.error(f"Error serving metrics: {e}")
        finally:
            await close_writer(writer)

    @classmethod
    async def start_server(cls, host: str, port: int, stack: AsyncExitStack) -> None:
        try:
            server = await asyncio.start_server(cls._handle_metrics, host, port)
            await stack.enter_async_context(server)
            logger.info(f"[*] Metrics server listening on {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server on {host}:{port}: {e}")
            raise

    @classmethod
    def record_rejected_connection(cls, protocol: str) -> None:
        cls.CONNECTIONS_TOTAL.labels(protocol=protocol, status="rejected").inc()

    @classmethod
    def record_connection(cls, protocol: str) -> None:
        cls.CONNECTIONS_TOTAL.labels(protocol=protocol, status="success").inc()
        cls.ACTIVE_SESSIONS.labels(protocol=protocol).inc()

    @classmethod
    def record_disconnection(cls, protocol: str) -> None:
        cls.ACTIVE_SESSIONS.labels(protocol=protocol).dec()

    @classmethod
    def record_bytes(cls, protocol: str, direction: str, num_bytes: int) -> None:
        if num_bytes > 0:
            cls.BYTES_TRANSFERRED.labels(
                protocol=protocol, direction=direction
            ).inc(num_bytes)

    @classmethod
    def set_backend_status(cls, protocol: str, backend_type: str, is_up: bool) -> None:
        cls.BACKEND_UP.labels(protocol=protocol, type=backend_type).set(
            1 if is_up else 0
        )
