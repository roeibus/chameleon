from honeypot.config import Protocol
from honeypot.core.bridge import ProtocolServer
from honeypot.protocols.http_proxy import HttpProxyBridge
from honeypot.protocols.ssh import SshBridge
from honeypot.protocols.telnet import TelnetBridge

BRIDGE_CLASSES: dict[Protocol, type[ProtocolServer]] = {
    Protocol.TELNET: TelnetBridge,
    Protocol.SSH: SshBridge,
    Protocol.HTTP_PROXY: HttpProxyBridge,
}
