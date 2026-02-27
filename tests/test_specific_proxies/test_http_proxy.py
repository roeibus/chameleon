import pytest

from honeypot.core.backend import Backend
from honeypot.protocols.http_proxy import HttpProxyBridge

@pytest.fixture
def mock_backend(mocker):
    return mocker.AsyncMock(spec=Backend)

@pytest.fixture
def bridge(mock_backend):
    return HttpProxyBridge(backend=mock_backend)

def test_name_is_http(bridge):
    assert bridge.name == "http"