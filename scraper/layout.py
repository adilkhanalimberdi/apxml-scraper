"""Folder/file naming shared by every writer, so all outputs line up (and stay under Windows' path limit)."""
from scraper.models import Chapter, Lesson

MAX_SLUG = 36


def chapter_dir(chapter: Chapter) -> str:
    return f"{chapter.order:02d}-{chapter.slug[:MAX_SLUG]}"


def lesson_stem(lesson: Lesson) -> str:
    return f"{lesson.order:02d}-{lesson.slug[:MAX_SLUG]}"


def safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)[:40] or "chart"
