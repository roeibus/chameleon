from dataclasses import dataclass


@dataclass
class ContainerConfig:
    image: str
    detach: bool = True
    tty: bool = True
    stdin_open: bool = True
    network_disabled: bool = True
    mem_limit: str | None = None
    cpu_period: int | None = None
    cpu_quota: int | None = None
    pids_limit: int | None = None
    labels: dict[str, str] | None = None
