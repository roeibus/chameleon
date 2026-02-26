from honeypot.proxy.proxy_bridge import ProxySessionBridge


class HttpProxyBridge(ProxySessionBridge):
    @property
    def name(self) -> str:
        return "http"
