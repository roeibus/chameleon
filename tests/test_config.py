import pytest
from pydantic import ValidationError

from honeypot.config import HttpProxyConfig, Protocol, ServiceConfig, Settings


def test_settings_valid_ports():
    settings = Settings(
        container_services=[ServiceConfig(protocol=Protocol.TELNET, listen_port=23)],
        proxy_services=[
            HttpProxyConfig(
                protocol=Protocol.HTTP_PROXY,
                listen_port=8080,
                target_host="example.com"
            )
        ],
    )
    assert len(settings.container_services) == 1
    assert len(settings.proxy_services) == 1


def test_settings_duplicate_ports():
    with pytest.raises(ValidationError, match="Port 23 conflicts"):
        Settings(
            container_services=[
                ServiceConfig(protocol=Protocol.TELNET, listen_port=23)
            ],
            proxy_services=[
                HttpProxyConfig(
                    protocol=Protocol.HTTP_PROXY,
                    listen_port=23,
                    target_host="example.com"
                )
            ],
        )

def test_settings_duplicate_ports_in_same_list():
    with pytest.raises(ValidationError, match="Port 22 conflicts"):
        Settings(
            container_services=[
                ServiceConfig(protocol=Protocol.TELNET, listen_port=22),
                ServiceConfig(protocol=Protocol.SSH, listen_port=22),
            ],
            proxy_services=[],
        )
