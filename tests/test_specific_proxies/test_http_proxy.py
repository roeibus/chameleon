import pytest
from unittest.mock import MagicMock, AsyncMock
import docker

from honeypot.proxy.http_proxy_bridge import HttpProxyBridge
from honeypot.backend import Backend
from honeypot.proxy.stream_backend import StreamBackend
from honeypot.builder import BackendBuilder


@pytest.fixture
def mock_backend():
    return AsyncMock(spec=Backend)


@pytest.fixture
def bridge(mock_backend):
    return HttpProxyBridge(backend=mock_backend)


def test_name_is_http(bridge):
    assert bridge.name == "http"


def test_greet_not_defined(bridge):
    assert not hasattr(bridge, 'greet')


def test_creates_stream_backend_on_builder_proxy():
    mock_client = MagicMock(spec=docker.DockerClient)
    builder = BackendBuilder(docker_client=mock_client)
    backend = builder.proxy("192.168.1.1", 80)
    assert isinstance(backend, StreamBackend)
