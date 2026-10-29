import atexit
import json
from pathlib import Path

from scraper.models import Chart
from scraper.rendering.base import BaseChartRenderer


class PlotlyRenderer(BaseChartRenderer):
    """Plotly figure JSON -> picture via kaleido (uses the installed Chrome/Edge)."""

    kind = "plotly"
    workers = 1  # kaleido drives one headless browser per process; parallelism comes from --shard

    def __init__(self, scale: float = 2):
        import kaleido  # imported lazily: only needed when rendering Plotly
        import plotly.graph_objects as go
        self._go = go
        self._scale = scale
        # one long-lived browser per process: ~0.3 s per chart instead of 5-40 s for a fresh browser each time
        kaleido.start_sync_server(silence_warnings=True)
        atexit.register(self._stop, kaleido)

    @staticmethod
    def _stop(kaleido) -> None:
        try:
            kaleido.stop_sync_server()
        except Exception:
            pass  # the browser is gone anyway when the process exits

    def render(self, chart: Chart, path: Path, fmt: str) -> None:
        figure = self._go.Figure(json.loads(chart.definition), skip_invalid=True)  # old charts use retired properties
        figure.write_image(str(path), format=fmt, scale=self._scale)
