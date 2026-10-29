import json
from pathlib import Path

from scraper.models import Chart
from scraper.rendering.base import BaseChartRenderer


class PlotlyRenderer(BaseChartRenderer):
    """Plotly figure JSON -> picture via kaleido (uses the installed Chrome/Edge)."""

    kind = "plotly"
    workers = 2  # each export talks to a headless browser: keep memory low

    def __init__(self, scale: float = 2):
        import plotly.graph_objects as go  # imported lazily: only needed when rendering Plotly
        self._go = go
        self._scale = scale

    def render(self, chart: Chart, path: Path, fmt: str) -> None:
        figure = self._go.Figure(json.loads(chart.definition))
        figure.write_image(str(path), format=fmt, scale=self._scale)
