from abc import ABC, abstractmethod
from types import TracebackType


class Backend(ABC):
    """Async context manager that owns a single connection."""

    @abstractmethod
    async def __aenter__(self) -> "Backend": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def read(self, size: int) -> bytes: ...

    @abstractmethod
    async def write(self, data: bytes) -> None: ...
