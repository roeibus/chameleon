from pathlib import Path

import docker

from honeypot.core.builder import BackendBuilder, ProxyBackendFactory, ContainerBackendFactory
from honeypot.backends.container_backend import ContainerBackend
from honeypot.backends.stream_backend import StreamBackend

def test_builder_creates_stream_backend_for_proxy(mocker):
    mock_client = mocker.Mock(spec=docker.DockerClient)
    builder = BackendBuilder(docker_client=mock_client)
    factory = builder.proxy("192.168.1.1", 80)
    
    assert isinstance(factory, ProxyBackendFactory)
    assert factory._host == "192.168.1.1"
    assert factory._port == 80
    
    backend = factory.create()
    assert isinstance(backend, StreamBackend)

def test_builder_creates_container_backend(mocker):
    mock_client = mocker.Mock(spec=docker.DockerClient)
    test_dir = Path("/tmp/fake_resources")
    builder = BackendBuilder(docker_client=mock_client, resources_dir=test_dir)
    
    factory = builder.container("test_app")
    
    assert isinstance(factory, ContainerBackendFactory)
    assert factory._name == "test_app"
    assert factory._resources_dir == test_dir
    
    backend = factory.create()
    assert isinstance(backend, ContainerBackend)
    assert backend._container._context_path == str(test_dir / "test_app")
    assert backend._container.config.image == "test_app"