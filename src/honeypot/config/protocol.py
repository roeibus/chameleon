from enum import StrEnum


class Protocol(StrEnum):
    TELNET = "telnet"
    SSH = "ssh"
    HTTP_PROXY = "http_proxy"
