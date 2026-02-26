from dataclasses import asdict

import pytest
from docker.errors import APIError, ImageNotFound

from honeypot.containers.config import ContainerConfig
from honeypot.containers.wrapper import ContainerWrapper

@pytest.fixture
def mock_docker_client(mocker):
    client = mocker.Mock()
    client.containers = mocker.Mock()
    client.images = mocker.Mock()
    return client

@pytest.fixture
def mock_container_obj(mocker):
    container = mocker.Mock()
    container.short_id = "abc1234"
    return container

@pytest.fixture
def container_config():
    return ContainerConfig(image="test_image:latest")

@pytest.fixture
def honeypot(mock_docker_client, container_config):
    return ContainerWrapper(
        client=mock_docker_client,
        config=container_config,
        context_path="/tmp/fake_path",
    )

def test_setup_runs_container_successfully(
    honeypot, mock_docker_client, mock_container_obj
):
    mock_docker_client.containers.run.return_value = mock_container_obj

    honeypot.setup()

    mock_docker_client.images.get.assert_called_with("test_image:latest")

    mock_docker_client.containers.run.assert_called_once()

    expected_kwargs = asdict(honeypot.config)
    mock_docker_client.containers.run.assert_called_with(**expected_kwargs)

    assert honeypot._inner_container == mock_container_obj

def test_build_image_found_locally(honeypot, mock_docker_client):
    honeypot._build_image()

    mock_docker_client.images.get.assert_called_once_with("test_image:latest")
    mock_docker_client.images.build.assert_not_called()

def test_build_image_missing_locally(honeypot, mock_docker_client):
    mock_docker_client.images.get.side_effect = ImageNotFound("Missing")
    honeypot._build_image()
    mock_docker_client.images.get.assert_called_once()
    mock_docker_client.images.build.assert_called_once_with(
        path="/tmp/fake_path", tag="test_image:latest"
    )

def test_teardown_kills_and_removes_existing_container(
    honeypot, mock_docker_client, mock_container_obj
):
    honeypot._inner_container = mock_container_obj
    honeypot.teardown()

    mock_container_obj.kill.assert_called_once()
    mock_container_obj.remove.assert_called_once()
    assert honeypot._inner_container is None

def test_teardown_handles_no_container(honeypot):
    honeypot._inner_container = None
    honeypot.teardown()
    assert honeypot._inner_container is None

def test_teardown_handles_exception_gracefully(honeypot, mock_container_obj):
    honeypot._inner_container = mock_container_obj
    mock_container_obj.kill.side_effect = APIError("Docker is dead")
    honeypot.teardown()
    mock_container_obj.kill.assert_called_once()
    assert honeypot._inner_container is None

def test_attach_socket_delegation(honeypot, mock_container_obj):
    honeypot._inner_container = mock_container_obj
    params = {"stdin": 1, "stream": 1}
    honeypot.attach_socket(**params)
    mock_container_obj.attach_socket.assert_called_once_with(**params)