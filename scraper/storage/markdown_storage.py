import json
import re
import shutil
from pathlib import Path

from scraper.layout import chapter_dir, lesson_stem
from scraper.models import Chapter, Course, Lesson
from scraper.storage.base import BaseStorage

MARKER_RE = re.compile(r"\[(plotly|graphviz): ([^\]]+)\]")
FENCE_LANG = {"graphviz": "dot", "plotly": "json"}


class MarkdownStorage(BaseStorage):
    """Writes output/<course>/markdown/<NN-chapter>/<NN-lesson>.md, one file per page.

    Rendered charts/images are linked relative to the file; charts that were not rendered
    are embedded as a fenced code block so no information is lost.
    """

    def __init__(self, output_dir: Path):
        self._output_dir = output_dir

    def save(self, course: Course) -> None:
        root = self._output_dir / course.slug / "markdown"
        shutil.rmtree(root, ignore_errors=True)  # so renamed/removed pages do not linger
        root.mkdir(parents=True)
        (root / "README.md").write_text(self._course_index(course), encoding="utf-8")

        for chapter in course.chapters:
            folder = root / chapter_dir(chapter)
            folder.mkdir()
            if chapter.overview_markdown:
                (folder / "00-overview.md").write_text(self._chapter_page(course, chapter), encoding="utf-8")
            for lesson in chapter.lessons:
                (folder / f"{lesson_stem(lesson)}.md").write_text(
                    self._lesson_page(course, chapter, lesson), encoding="utf-8")

    @staticmethod
    def _front_matter(**fields: str | int) -> str:
        lines = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()]
        return "---\n" + "\n".join(lines) + "\n---\n\n"

    def _course_index(self, course: Course) -> str:
        parts = [self._front_matter(title=course.title, url=course.url, description=course.description),
                 f"# {course.title}\n\n"]
        if course.preview_path:
            parts.append(f"![preview](../{course.preview_path})\n\n")
        parts += [course.overview_markdown, "\n\n## Contents\n\n"]
        for chapter in course.chapters:
            parts.append(f"### {chapter.title}\n\n")
            for lesson in chapter.lessons:
                link = f"{chapter_dir(chapter)}/{lesson_stem(lesson)}.md"
                parts.append(f"- [{lesson.title}]({link})\n")
            parts.append("\n")
        return "".join(parts)

    def _chapter_page(self, course: Course, chapter: Chapter) -> str:
        return (self._front_matter(title=chapter.title, course=course.title, url=chapter.url)
                + f"# {chapter.title}\n\n{chapter.overview_markdown}\n")

    def _lesson_page(self, course: Course, chapter: Chapter, lesson: Lesson) -> str:
        body = self._link_media(lesson)
        # quiz/project pages already start with their own heading
        heading = "" if body.lstrip().startswith("# ") else f"# {lesson.title}\n\n"
        return (self._front_matter(title=lesson.title, course=course.title, chapter=chapter.title,
                                   type=lesson.lesson_type.value, order=lesson.order, url=lesson.url)
                + heading + body + "\n")

    @staticmethod
    def _link_media(lesson: Lesson) -> str:
        up = "../"  # markdown/<chapter>/<lesson>.md -> course folder
        text = lesson.content_markdown
        for image in lesson.images:
            if image.local_path:
                text = text.replace(f"]({image.src})", f"]({up}{up}{image.local_path})")
        charts = {chart.chart_id: chart for chart in lesson.charts}

        def replace(match: re.Match) -> str:
            chart = charts.get(match.group(2))
            if chart is None:
                return match.group(0)
            if chart.local_path:
                return f"![{chart.chart_id}]({up}{up}{chart.local_path})"
            return f"```{FENCE_LANG[chart.kind]}\n{chart.definition}\n```"

        return MARKER_RE.sub(replace, text)
