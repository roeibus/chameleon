from pathlib import Path
from typing import ClassVar

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from honeypot.config.protocol import Protocol
from honeypot.config.service import ContainerServiceConfig, HttpProxyConfig


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CHAMELEON_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    container_services: list[ContainerServiceConfig] = [
        ContainerServiceConfig(protocol=Protocol.TELNET, listen_port=23),
        ContainerServiceConfig(protocol=Protocol.SSH, listen_port=22),
    ]
    proxy_services: list[HttpProxyConfig] = []
    bind_host: str = "0.0.0.0"
    log_dir: Path | None = None

    @model_validator(mode="after")
    def validate_unique_ports(self) -> "Settings":
        seen: dict[int, str] = {}
        for svc in [*self.container_services, *self.proxy_services]:
            if svc.listen_port in seen:
                raise ValueError(
                    f"Port {svc.listen_port} conflicts: "
                    + f"'{seen[svc.listen_port]}' and '{svc.protocol}'"
                )
            seen[svc.listen_port] = svc.protocol
        return self
