from typing import override

from honeypot.proxy.proxy_bridge import ProxySessionBridge


class HttpProxyBridge(ProxySessionBridge):
    @property
    @override
    def name(self) -> str:
        return "http"
