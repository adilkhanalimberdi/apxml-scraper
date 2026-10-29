import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

from scraper.models import Chapter, Chart, Course, Image, Lesson, LessonType


class SqliteReader:
    """Rebuilds Course objects from apxml.db, so exports/renders never need the website."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def course_slugs(self) -> list[str]:
        with closing(sqlite3.connect(self._db_path)) as db:
            return [row[0] for row in db.execute("SELECT slug FROM courses ORDER BY slug")]

    def load_courses(self, slugs: list[str] | None = None) -> Iterator[Course]:
        for slug in slugs or self.course_slugs():
            yield self.load_course(slug)

    def load_course(self, slug: str) -> Course:
        with closing(sqlite3.connect(self._db_path)) as db:
            have = {col[1] for col in db.execute("PRAGMA table_info(courses)")}
            extra = [c if c in have else "NULL" for c in ("description", "preview_url", "preview_path", "structured_data")]
            row = db.execute("SELECT title, url, overview_markdown, overview_html, " + ", ".join(extra)
                             + " FROM courses WHERE slug = ?", (slug,)).fetchone()
            if row is None:
                raise KeyError(f"Course not in database: {slug}")
            course = Course(slug=slug, title=row[0], url=row[1], overview_markdown=row[2] or "",
                            overview_html=row[3] or "", description=row[4] or "", preview_url=row[5] or "",
                            preview_path=row[6], structured_data=row[7] or "")

            chapters = {}
            for r in db.execute('SELECT slug, "order", title, url, overview_markdown, overview_html '
                                'FROM chapters WHERE course_slug = ? ORDER BY "order"', (slug,)):
                chapters[r[0]] = Chapter(slug=r[0], order=r[1], title=r[2], url=r[3],
                                         overview_markdown=r[4] or "", overview_html=r[5] or "")
                course.chapters.append(chapters[r[0]])

            lessons = {}
            for r in db.execute('SELECT chapter_slug, slug, "order", type, title, url, content_markdown, content_html '
                                'FROM lessons WHERE course_slug = ? ORDER BY chapter_slug, "order"', (slug,)):
                lesson = Lesson(slug=r[1], order=r[2], lesson_type=LessonType(r[3]), title=r[4], url=r[5],
                                content_markdown=r[6] or "", content_html=r[7] or "")
                lessons[(r[0], r[1])] = lesson
                chapters[r[0]].lessons.append(lesson)

            for r in db.execute("SELECT chapter_slug, lesson_slug, src, alt, local_path FROM images "
                                "WHERE course_slug = ?", (slug,)):
                lessons[(r[0], r[1])].images.append(Image(src=r[2], alt=r[3] or "", local_path=r[4]))
            # databases written before charts got a local_path column are still readable
            has_path = any(col[1] == "local_path" for col in db.execute("PRAGMA table_info(charts)"))
            for r in db.execute("SELECT chapter_slug, lesson_slug, chart_id, kind, definition, "
                                f"{'local_path' if has_path else 'NULL'} FROM charts WHERE course_slug = ?", (slug,)):
                lessons[(r[0], r[1])].charts.append(
                    Chart(chart_id=r[2], kind=r[3], definition=r[4], local_path=r[5]))
        return course
