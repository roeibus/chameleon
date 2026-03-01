from loguru import logger
from prometheus_client import Counter, Gauge, start_http_server


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
    def start_server(cls, host: str, port: int) -> None:
        try:
            start_http_server(port, addr=host)
            logger.info(f"[*] Metrics server listening on {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server on {host}:{port}: {e}")

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
