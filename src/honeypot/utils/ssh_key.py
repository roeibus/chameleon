import os
from pathlib import Path

import asyncssh
from asyncssh import SSHKey
from loguru import logger

_DEFAULT_HOST_KEY_PATH = os.environ.get("CHAMELEON_HOST_KEY_PATH", "/data/ssh_host_key")
_HOST_KEY_PATH = Path(_DEFAULT_HOST_KEY_PATH)


def get_host_key(path: Path = _HOST_KEY_PATH) -> SSHKey:
    if path.exists():
        return asyncssh.read_private_key(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    key = asyncssh.generate_private_key("ssh-rsa")
    key.write_private_key(str(path))
    logger.info(f"[*] Generated new SSH host key at {path}")
    return key