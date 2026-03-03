import pytest
from docker.errors import APIError

from honeypot.utils.docker_utils import cleanup_stale_containers


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock()
    client.containers = mocker.Mock()
    return client


@pytest.fixture(autouse=True)
def patch_to_thread(mocker):
    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    mocker.patch(
        "honeypot.utils.docker_utils.asyncio.to_thread", side_effect=fake_to_thread
    )


@pytest.mark.asyncio
async def test_no_stale_containers_returns_early(mock_client):
    mock_client.containers.list.return_value = []

    await cleanup_stale_containers(mock_client)

    mock_client.containers.list.assert_called_once_with(
        all=True, filters={"label": "chameleon=true"}
    )


@pytest.mark.asyncio
async def test_successful_cleanup(mock_client, mocker):
    container_a = mocker.Mock()
    container_a.short_id = "aaa1111"
    container_b = mocker.Mock()
    container_b.short_id = "bbb2222"
    mock_client.containers.list.return_value = [container_a, container_b]

    await cleanup_stale_containers(mock_client)

    container_a.kill.assert_called_once()
    container_a.remove.assert_called_once()
    container_b.kill.assert_called_once()
    container_b.remove.assert_called_once()


@pytest.mark.asyncio
async def test_kill_apierror_is_silently_ignored(mock_client, mocker):
    container = mocker.Mock()
    container.short_id = "dead1234"
    container.kill.side_effect = APIError("already dead")
    mock_client.containers.list.return_value = [container]

    await cleanup_stale_containers(mock_client)

    container.kill.assert_called_once()
    # remove must still be attempted even when kill failed
    container.remove.assert_called_once()


@pytest.mark.asyncio
async def test_remove_apierror_logs_warning_and_continues(mock_client, mocker):
    container_a = mocker.Mock()
    container_a.short_id = "badc0de1"
    container_a.remove.side_effect = APIError("permission denied")
    container_b = mocker.Mock()
    container_b.short_id = "badc0de2"
    mock_client.containers.list.return_value = [container_a, container_b]

    # Should not raise; second container must still be processed
    await cleanup_stale_containers(mock_client)

    container_a.kill.assert_called_once()
    container_a.remove.assert_called_once()
    container_b.kill.assert_called_once()
    container_b.remove.assert_called_once()