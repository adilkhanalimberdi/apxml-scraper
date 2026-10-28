from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseParser(ABC, Generic[T]):
    @abstractmethod
    def parse(self, html: str, url: str) -> T:
        """Turn page HTML into a model; url is used to resolve relative links."""
