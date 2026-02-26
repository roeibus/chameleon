import pytest

from honeypot.backend import Backend
from honeypot.proxy.http_proxy_bridge import HttpProxyBridge

@pytest.fixture
def mock_backend(mocker):
    return mocker.AsyncMock(spec=Backend)

@pytest.fixture
def bridge(mock_backend):
    return HttpProxyBridge(backend=mock_backend)

def test_name_is_http(bridge):
    assert bridge.name == "http"