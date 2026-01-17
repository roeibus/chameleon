import asyncio
from abc import abstractmethod, ABC
from asyncio import AbstractEventLoop, StreamReader, StreamWriter
from loguru import logger


class SessionBridge(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def loop(self) -> AbstractEventLoop:
        return asyncio.get_running_loop()

    @abstractmethod
    async def handle_bridge(self, reader: StreamReader,
                            writer: StreamWriter) -> None:
        pass

    async def handle_client(self, reader: StreamReader,
                            writer: StreamWriter) -> None:
        addr: tuple = writer.get_extra_info('peername')
        with logger.contextualize(ip=addr[0], bridge=self.name):
            logger.info("[+] New containers detected")
            try:
                await self.handle_bridge(reader, writer)
            except Exception as e:
                logger.error(f"Bridge error: {e}")
            finally:
                logger.info("[-] Connection closed")
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
