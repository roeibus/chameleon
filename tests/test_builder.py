from pathlib import Path

import docker
import pytest
from docker.errors import ImageNotFound

from honeypot.core.builder import BackendBuilder, ProxyBackendFactory, ContainerBackendFactory
from honeypot.backends.container_backend import ContainerBackend
from honeypot.backends.stream_backend import StreamBackend
from honeypot.utils.docker_utils import pre_build_images

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


def test_ensure_image_skips_build_when_image_exists(mocker):
    mock_client = mocker.Mock(spec=docker.DockerClient)
    mock_client.images.get.return_value = mocker.Mock()
    factory = ContainerBackendFactory(mock_client, Path("/tmp/fake"), "telnet")

    factory.ensure_image()

    mock_client.images.get.assert_called_once_with("telnet")
    mock_client.images.build.assert_not_called()


def test_ensure_image_builds_when_image_missing(mocker):
    mock_client = mocker.Mock(spec=docker.DockerClient)
    mock_client.images.get.side_effect = ImageNotFound("telnet")
    factory = ContainerBackendFactory(mock_client, Path("/tmp/fake"), "telnet")

    factory.ensure_image()

    mock_client.images.get.assert_called_once_with("telnet")
    mock_client.images.build.assert_called_once_with(
        path="/tmp/fake/telnet", tag="telnet"
    )



@pytest.mark.asyncio
async def test_pre_build_images_deduplicates_same_name(mocker):
    """Two factories with the same name → only the last one's ensure_image is called."""
    mock_client = mocker.Mock(spec=docker.DockerClient)
    builder = BackendBuilder(docker_client=mock_client, resources_dir=Path("/tmp/fake"))

    f1 = builder.container("telnet")
    f2 = builder.container("telnet")  # same name — overwrites f1 in the dict

    mocker.patch.object(f1, "ensure_image")
    mocker.patch.object(f2, "ensure_image")

    await pre_build_images(builder.container_factories)

    f1.ensure_image.assert_not_called()
    f2.ensure_image.assert_called_once()


@pytest.mark.asyncio
async def test_pre_build_images_calls_all_unique_factories(mocker):
    """Two factories with distinct names → both ensure_image calls are made."""
    mock_client = mocker.Mock(spec=docker.DockerClient)
    builder = BackendBuilder(docker_client=mock_client, resources_dir=Path("/tmp/fake"))

    f1 = builder.container("telnet")
    f2 = builder.container("ssh")

    mocker.patch.object(f1, "ensure_image")
    mocker.patch.object(f2, "ensure_image")

    await pre_build_images(builder.container_factories)

    f1.ensure_image.assert_called_once()
    f2.ensure_image.assert_called_once()


@pytest.mark.asyncio
async def test_pre_build_images_noop_with_no_factories(mocker):
    """No registered factories → completes without error and calls nothing."""
    mock_client = mocker.Mock(spec=docker.DockerClient)
    builder = BackendBuilder(docker_client=mock_client)

    await pre_build_images(builder.container_factories)  # should not raise
