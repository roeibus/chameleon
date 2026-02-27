from typing import Protocol


class _HasExtraInfo(Protocol):
    def get_extra_info(
        self, name: str, default: object = None
    ) -> tuple[str, int] | None: ...


def extract_ip(transport: _HasExtraInfo) -> str:
    peername = transport.get_extra_info("peername")
    return peername[0] if peername else "UNKNOWN"
