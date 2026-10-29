from abc import ABC, abstractmethod


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self, url: str) -> str:
        """Return the page HTML for the given URL."""

    @abstractmethod
    def fetch_bytes(self, url: str) -> bytes:
        """Return the raw body (images and other assets) for the given URL."""
