import pytest


@pytest.fixture(autouse=True)
def _use_temp_host_key_path(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAMELEON_HOST_KEY_PATH", str(tmp_path / "ssh_host_key"))