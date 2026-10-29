import sqlite3
from contextlib import closing
from pathlib import Path

from scraper.models import Course
from scraper.storage.base import BaseStorage

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    slug TEXT PRIMARY KEY, title TEXT, url TEXT, overview_markdown TEXT, overview_html TEXT,
    description TEXT, preview_url TEXT, preview_path TEXT, structured_data TEXT
);
CREATE TABLE IF NOT EXISTS chapters (
    course_slug TEXT, slug TEXT, "order" INTEGER, title TEXT, url TEXT,
    overview_markdown TEXT, overview_html TEXT,
    PRIMARY KEY (course_slug, slug)
);
CREATE TABLE IF NOT EXISTS lessons (
    course_slug TEXT, chapter_slug TEXT, slug TEXT, "order" INTEGER, type TEXT,
    title TEXT, url TEXT, content_markdown TEXT, content_html TEXT,
    PRIMARY KEY (course_slug, chapter_slug, slug)
);
CREATE TABLE IF NOT EXISTS images (
    course_slug TEXT, chapter_slug TEXT, lesson_slug TEXT, src TEXT, alt TEXT, local_path TEXT
);
CREATE TABLE IF NOT EXISTS charts (
    course_slug TEXT, chapter_slug TEXT, lesson_slug TEXT, chart_id TEXT, kind TEXT, definition TEXT, local_path TEXT
);
"""


class SqliteStorage(BaseStorage):
    """Stores all courses in one SQLite file; re-saving a course replaces its rows."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def save(self, course: Course) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._db_path, timeout=120)) as db, db:  # `with db` = one transaction
            self._migrate(db)
            db.executescript(SCHEMA)
            for table in ("courses", "chapters", "lessons", "images", "charts"):
                column = "slug" if table == "courses" else "course_slug"
                db.execute(f"DELETE FROM {table} WHERE {column} = ?", (course.slug,))

            db.execute("INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (course.slug, course.title, course.url, course.overview_markdown, course.overview_html,
                        course.description, course.preview_url, course.preview_path, course.structured_data))
            for chapter in course.chapters:
                db.execute("INSERT INTO chapters VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (course.slug, chapter.slug, chapter.order, chapter.title, chapter.url,
                            chapter.overview_markdown, chapter.overview_html))
            for chapter, lesson in course.iter_lessons():
                key = (course.slug, chapter.slug, lesson.slug)
                db.execute("INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           key + (lesson.order, lesson.lesson_type.value, lesson.title, lesson.url,
                                  lesson.content_markdown, lesson.content_html))
                db.executemany("INSERT INTO images VALUES (?, ?, ?, ?, ?, ?)",
                               [key + (i.src, i.alt, i.local_path) for i in lesson.images])
                db.executemany("INSERT INTO charts VALUES (?, ?, ?, ?, ?, ?, ?)",
                               [key + (c.chart_id, c.kind, c.definition, c.local_path) for c in lesson.charts])

    @staticmethod
    def _migrate(db: sqlite3.Connection) -> None:
        """Recreate tables from older versions of the schema (re-run the courses to refill)."""
        for table, new_column in (("charts", "kind"), ("courses", "overview_markdown"),
                                  ("chapters", "overview_markdown")):
            columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
            if columns and new_column not in columns:
                db.execute(f"DROP TABLE {table}")
        # columns added later: keep the rows
        for table, column in (("charts", "local_path"), ("courses", "description"), ("courses", "preview_url"),
                              ("courses", "preview_path"), ("courses", "structured_data")):
            columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
            if columns and column not in columns:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
