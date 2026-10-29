import csv
from pathlib import Path

from scraper.models import Course
from scraper.storage.base import BaseStorage


class CsvStorage(BaseStorage):
    """Writes output/<course>/{chapters,lessons,images,charts}.csv (UTF-8 with BOM for Excel)."""

    def __init__(self, output_dir: Path):
        self._output_dir = output_dir

    def save(self, course: Course) -> None:
        target = self._output_dir / course.slug
        target.mkdir(parents=True, exist_ok=True)

        chapters, lessons, images, charts = [], [], [], []
        for chapter in course.chapters:
            chapters.append([course.slug, chapter.slug, chapter.order, chapter.title, chapter.url])
        for chapter, lesson in course.iter_lessons():
            key = [course.slug, chapter.slug, lesson.slug]
            lessons.append(key + [lesson.order, lesson.lesson_type.value, lesson.title, lesson.url,
                                  lesson.content_markdown, lesson.content_html])
            images += [key + [i.src, i.alt, i.local_path or ""] for i in lesson.images]
            charts += [key + [c.chart_id, c.kind, c.definition] for c in lesson.charts]

        key_cols = ["course_slug", "chapter_slug", "lesson_slug"]
        self._write(target / "chapters.csv", ["course_slug", "chapter_slug", "order", "title", "url"], chapters)
        self._write(target / "lessons.csv",
                    key_cols + ["order", "type", "title", "url", "content_markdown", "content_html"], lessons)
        self._write(target / "images.csv", key_cols + ["src", "alt", "local_path"], images)
        self._write(target / "charts.csv", key_cols + ["chart_id", "kind", "definition"], charts)

    @staticmethod
    def _write(path: Path, header: list[str], rows: list[list]) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(rows)
