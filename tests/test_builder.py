from pathlib import Path

import docker

from honeypot.core.builder import BackendBuilder, ProxyBackendFactory, ContainerBackendFactory
from honeypot.backends.container_backend import ContainerBackend
from honeypot.backends.stream_backend import StreamBackend

def test_builder_creates_stream_backend_for_proxy(mocker):
    mock_client = mocker.Mock(spec=docker.DockerClient)
    builder = BackendBuilder(docker_client=mock_client)
    factory = builder.proxy("192.168.1.1", 80, name="custom_proxy")
    
    assert isinstance(factory, ProxyBackendFactory)
    
    backend = factory.create()
    assert isinstance(backend, StreamBackend)
    assert backend._protocol == "custom_proxy"

def test_builder_creates_container_backend(mocker):
    mock_client = mocker.Mock(spec=docker.DockerClient)
    test_dir = Path("/tmp/fake_resources")
    builder = BackendBuilder(docker_client=mock_client, resources_dir=test_dir)
    
    factory = builder.container("test_app")
    
    assert isinstance(factory, ContainerBackendFactory)
    
    backend = factory.create()
    assert isinstance(backend, ContainerBackend)
    assert backend._protocol == "test_app"
