from abc import ABC, abstractmethod
from pathlib import Path

from scraper.models import Chart


class BaseChartRenderer(ABC):
    kind: str  # Chart.kind this renderer handles
    workers: int = 1  # how many renders may run in parallel

    @abstractmethod
    def render(self, chart: Chart, path: Path, fmt: str) -> None:
        """Draw the chart to `path` (png or svg). Raise on failure."""
