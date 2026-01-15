from asyncio import StreamWriter
from honeypot.client import SessionBridge  # Assuming you saved the bridge code here


class TelnetBridge(SessionBridge):

    async def greet(self, writer: StreamWriter) -> None:
        banner = (
            b"\r\n"
            b"Ubuntu 18.04.6 LTS\r\n"
            b"\r\n"
            b"server login: "
        )
        writer.write(banner)
        await writer.drain()
