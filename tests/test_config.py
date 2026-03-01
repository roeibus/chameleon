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


def test_settings_metrics_port_invalid():
    with pytest.raises(ValidationError):
        Settings(metrics_port=70000)
    with pytest.raises(ValidationError):
        Settings(metrics_port=0)


def test_settings_metrics_port_collision():
    # SSH is in default container_services with port 2222
    with pytest.raises(ValidationError, match="Port 2222 conflicts: 'metrics' and 'ssh'"):
        Settings(
            container_services=[
                ContainerServiceConfig(protocol=Protocol.SSH, listen_port=2222)
            ],
            metrics_port=2222,
            enable_metrics=True,
        )


def test_settings_metrics_port_no_collision_if_disabled():
    # Should not raise
    Settings(
        container_services=[
            ContainerServiceConfig(protocol=Protocol.SSH, listen_port=2222)
        ],
        metrics_port=2222,
        enable_metrics=False,
    )
