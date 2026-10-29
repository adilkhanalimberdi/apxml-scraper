import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from scraper.config import Settings
from scraper.layout import chapter_dir, lesson_stem, safe_id
from scraper.models import Chapter, Chart, Course, Lesson
from scraper.rendering.base import BaseChartRenderer

logger = logging.getLogger(__name__)


@dataclass
class RenderStats:
    rendered: int = 0
    skipped: int = 0
    failed: int = 0


class ChartRenderService:
    """Renders every chart of a course to output/<course>/images/<chapter>/<lesson>/<id>.<fmt>
    and records the path in Chart.local_path. Charts of one kind run in a thread pool."""

    def __init__(self, renderers: list[BaseChartRenderer], settings: Settings, fmt: str = "png", force: bool = False):
        self._renderers = {renderer.kind: renderer for renderer in renderers}
        self._output_dir = settings.output_dir
        self._fmt = fmt
        self._force = force

    def render_course(self, course: Course) -> RenderStats:
        stats = RenderStats()
        for kind, renderer in self._renderers.items():
            jobs = [(chapter, lesson, chart) for chapter, lesson in course.iter_lessons()
                    for chart in lesson.charts if chart.kind == kind]
            if not jobs:
                continue
            with ThreadPoolExecutor(max_workers=renderer.workers) as pool:
                outcomes = list(pool.map(lambda job: self._render_one(renderer, course, *job), jobs))
            for outcome in outcomes:
                setattr(stats, outcome, getattr(stats, outcome) + 1)
        return stats

    def _render_one(self, renderer: BaseChartRenderer, course: Course,
                    chapter: Chapter, lesson: Lesson, chart: Chart) -> str:
        relative = f"images/{chapter_dir(chapter)}/{lesson_stem(lesson)}/{safe_id(chart.chart_id)}.{self._fmt}"
        path = self._output_dir / course.slug / relative
        if path.exists() and not self._force:
            chart.local_path = relative
            return "skipped"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            renderer.render(chart, path, self._fmt)
        except Exception as exc:
            logger.warning("%s/%s %s failed: %s", course.slug, lesson.slug, chart.chart_id, exc)
            return "failed"
        chart.local_path = relative
        return "rendered"
