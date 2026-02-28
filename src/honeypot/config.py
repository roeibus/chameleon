from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CHAMELEON_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Target IoT device
    iot_host: str = "192.168.1.1"
    iot_http_port: int = 80

    # Honeypot listen ports
    http_port: int = 8080
    telnet_port: int = 23
    ssh_port: int = 22

    # Bind address for all servers
    bind_host: str = "0.0.0.0"

    # Log directory (None = auto-resolve via resolve_log_dir)
    log_dir: Path | None = None
