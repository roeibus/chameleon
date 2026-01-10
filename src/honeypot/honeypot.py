import asyncio
from abc import ABC, abstractmethod


class Honeypot(ABC):

    @abstractmethod
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        pass


