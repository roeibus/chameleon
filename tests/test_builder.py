from pathlib import Path

import docker

from honeypot.core.builder import BackendBuilder
from honeypot.backends.container_backend import ContainerBackend
from honeypot.backends.stream_backend import StreamBackend

def test_builder_creates_stream_backend_for_proxy(mocker):
    mock_client = mocker.Mock(spec=docker.DockerClient)
    builder = BackendBuilder(docker_client=mock_client)
    backend = builder.proxy("192.168.1.1", 80)
    
    assert isinstance(backend, StreamBackend)
    assert backend._host == "192.168.1.1"
    assert backend._port == 80

def test_builder_creates_container_backend(mocker):
    mock_client = mocker.Mock(spec=docker.DockerClient)
    test_dir = Path("/tmp/fake_resources")
    builder = BackendBuilder(docker_client=mock_client, resources_dir=test_dir)
    
    backend = builder.container("test_app")
    
    assert isinstance(backend, ContainerBackend)
    assert backend._container._context_path == str(test_dir / "test_app")
    assert backend._container.config.image == "test_app"