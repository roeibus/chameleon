from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Protocol(StrEnum):
    TELNET = "telnet"
    SSH = "ssh"
    HTTP_PROXY = "http_proxy"


class ServiceConfig(BaseModel):
    """
    Base service config — covers any protocol with no extra fields (Telnet, SSH, ...).
    """

    listen_port: int = Field(ge=1, le=65535)


class ContainerServiceConfig(ServiceConfig):
    """
    Config for container-based services.
    """

    protocol: Literal[Protocol.TELNET, Protocol.SSH]


class HttpProxyConfig(ServiceConfig):
    """Extends ServiceConfig with proxy-target fields."""

    protocol: Literal[Protocol.HTTP_PROXY]
    target_host: str
    target_port: int = Field(default=80, ge=1, le=65535)
    name: str = ""


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
