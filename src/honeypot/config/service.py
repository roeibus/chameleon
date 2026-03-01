from typing import Literal

from pydantic import BaseModel, Field

from honeypot.config.protocol import Protocol


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
