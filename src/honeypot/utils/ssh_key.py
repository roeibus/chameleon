import os
import stat
from pathlib import Path

import asyncssh
from asyncssh import SSHKey
from loguru import logger


def get_host_key(path: Path | None = None) -> SSHKey:
    if path is None:
        path = Path(os.environ.get("CHAMELEON_HOST_KEY_PATH", "/data/ssh_host_key"))
    if path.exists():
        return asyncssh.read_private_key(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    key = asyncssh.generate_private_key("ssh-rsa")
    key.write_private_key(str(path))
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    logger.info(f"[*] Generated new SSH host key at {path}")
    return key
