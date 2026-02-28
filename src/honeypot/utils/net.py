import ipaddress
from typing import Protocol


class _HasExtraInfo(Protocol):
    def get_extra_info(
        self, name: str, default: object = None
    ) -> tuple[str, int] | None: ...


def extract_ip(transport: _HasExtraInfo) -> str:
    peername = transport.get_extra_info("peername")
    if not peername:
        return "UNKNOWN"
    try:
        return str(ipaddress.ip_address(peername[0]))
    except ValueError:
        return "UNKNOWN"
