import shutil
import subprocess
from pathlib import Path

from scraper.models import Chart
from scraper.rendering.base import BaseChartRenderer

WINDOWS_DEFAULTS = (r"C:\Program Files\Graphviz\bin\dot.exe", r"C:\Program Files (x86)\Graphviz\bin\dot.exe")


def find_dot() -> str | None:
    found = shutil.which("dot")
    if found:
        return found
    return next((p for p in WINDOWS_DEFAULTS if Path(p).exists()), None)


class GraphvizRenderer(BaseChartRenderer):
    """DOT source -> picture via the `dot` executable."""

    kind = "graphviz"
    workers = 4  # dot is a short-lived subprocess; threads are enough

    def __init__(self, dot_path: str | None = None, dpi: int = 150):
        self._dot = dot_path or find_dot()
        if not self._dot:
            raise RuntimeError("Graphviz 'dot' not found: install Graphviz and add it to PATH")
        self._dpi = dpi

    def render(self, chart: Chart, path: Path, fmt: str) -> None:
        # the second attempt uses the newer ranking algorithm, which fixes "install_in_rank" errors
        for extra in ([], ["-Gnewrank=true"]):
            result = subprocess.run(
                [self._dot, f"-T{fmt}", f"-Gdpi={self._dpi}", *extra, "-o", str(path)],
                input=chart.definition.encode("utf-8"), capture_output=True, timeout=120,
            )
            if result.returncode == 0:
                return
        path.unlink(missing_ok=True)
        errors = [line for line in result.stderr.decode("utf-8", errors="replace").splitlines()
                  if not line.startswith("Warning")]
        raise RuntimeError(" | ".join(errors)[:300])
