from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeviceConfig(BaseModel):
    name: str = ""
    target_host: str
    target_port: int = 80
    listen_port: int


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CHAMELEON_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # IoT devices to proxy (set via CHAMELEON_DEVICES as JSON)
    devices: list[DeviceConfig] = []

    # Honeypot listen ports
    telnet_port: int = 23
    ssh_port: int = 22

    # Bind address for all servers
    bind_host: str = "0.0.0.0"

    # Log directory (None = auto-resolve via resolve_log_dir)
    log_dir: Path | None = None
