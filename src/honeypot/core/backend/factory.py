from abc import ABC, abstractmethod

from honeypot.core.backend.interface import Backend


class BackendFactory(ABC):
    """Creates a fresh Backend for each client connection."""

    @abstractmethod
    def create(self) -> Backend: ...
