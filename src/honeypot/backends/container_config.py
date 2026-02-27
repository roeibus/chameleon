from dataclasses import dataclass


@dataclass
class ContainerConfig:
    image: str
    detach: bool = True
    tty: bool = True
    stdin_open: bool = True
    network_disabled: bool = False
