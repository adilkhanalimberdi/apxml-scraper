from abc import ABC, abstractmethod

from scraper.models import Course


class BaseStorage(ABC):
    @abstractmethod
    def save(self, course: Course) -> None:
        """Persist the whole course."""
