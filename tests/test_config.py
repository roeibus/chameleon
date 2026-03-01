import pytest
from pydantic import ValidationError

from honeypot.config import ContainerServiceConfig, HttpProxyConfig, Protocol, Settings


def test_settings_valid_ports():
    settings = Settings(
        container_services=[
            ContainerServiceConfig(protocol=Protocol.TELNET, listen_port=23)
        ],
        proxy_services=[
            HttpProxyConfig(
                protocol=Protocol.HTTP_PROXY,
                listen_port=8080,
                target_host="example.com",
            )
        ],
    )
    assert len(settings.container_services) == 1
    assert len(settings.proxy_services) == 1


def test_settings_duplicate_ports():
    with pytest.raises(ValidationError, match="Port 23 conflicts"):
        Settings(
            container_services=[
                ContainerServiceConfig(protocol=Protocol.TELNET, listen_port=23)
            ],
            proxy_services=[
                HttpProxyConfig(
                    protocol=Protocol.HTTP_PROXY,
                    listen_port=23,
                    target_host="example.com",
                )
            ],
        )


def test_settings_duplicate_ports_in_same_list():
    with pytest.raises(ValidationError, match="Port 22 conflicts"):
        Settings(
            container_services=[
                ContainerServiceConfig(protocol=Protocol.TELNET, listen_port=22),
                ContainerServiceConfig(protocol=Protocol.SSH, listen_port=22),
            ],
            proxy_services=[],
        )


def test_invalid_service_config_protocol():
    with pytest.raises(ValidationError):
        ContainerServiceConfig(protocol=Protocol.HTTP_PROXY, listen_port=80)


def test_settings_duplicate_proxy_ports_in_same_list():
    with pytest.raises(ValidationError, match="Port 8080 conflicts"):
        Settings(
            container_services=[],
            proxy_services=[
                HttpProxyConfig(
                    protocol=Protocol.HTTP_PROXY,
                    listen_port=8080,
                    target_host="a.example.com",
                ),
                HttpProxyConfig(
                    protocol=Protocol.HTTP_PROXY,
                    listen_port=8080,
                    target_host="b.example.com",
                ),
            ],
        )


def test_invalid_proxy_config_protocol():
    with pytest.raises(ValidationError):
        HttpProxyConfig(
            protocol=Protocol.TELNET, listen_port=8080, target_host="example.com"
        )
