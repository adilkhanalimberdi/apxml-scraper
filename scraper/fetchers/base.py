from abc import ABC, abstractmethod


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self, url: str) -> str:
        """Return the page HTML for the given URL."""

    def release(self, url: str) -> None:
        """Free anything stored for a finished course (no-op unless the fetcher caches)."""

    @abstractmethod
    def fetch_bytes(self, url: str) -> bytes:
        """Return the raw body (images and other assets) for the given URL."""
