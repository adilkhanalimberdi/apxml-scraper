import logging

from scraper.fetchers.base import BaseFetcher
from scraper.images import ImageDownloader
from scraper.models import Chapter, Course, Lesson, LessonType
from scraper.parsers.course import CoursePageParser
from scraper.parsers.lesson import LessonPageParser
from scraper.storage.base import BaseStorage

logger = logging.getLogger(__name__)


class CourseScraper:
    """Wires fetcher -> parsers -> (images) -> storages. Knows only the abstractions."""

    def __init__(
        self,
        fetcher: BaseFetcher,
        course_parser: CoursePageParser,
        lesson_parser: LessonPageParser,
        storages: list[BaseStorage],
        image_downloader: ImageDownloader | None = None,
    ):
        self._fetcher = fetcher
        self._course_parser = course_parser
        self._lesson_parser = lesson_parser
        self._storages = storages
        self._image_downloader = image_downloader

    def scrape(self, course_url: str) -> Course:
        course = self._course_parser.parse(self._fetcher.fetch(course_url), course_url)
        total = sum(len(chapter.lessons) or 1 for chapter in course.chapters)
        logger.info("%s: %d chapters, %d pages", course.slug, len(course.chapters), total)

        done = 0
        for chapter in course.chapters:
            # Chapter overview pages (e.g. the final project) are stored as a pseudo-lesson
            # only when the chapter has no lessons of its own.
            if not chapter.lessons:
                chapter.lessons.append(self._chapter_as_lesson(chapter))
            for lesson in chapter.lessons:
                done += 1
                try:
                    html = self._fetcher.fetch(lesson.url)
                    self._lesson_parser.parse_into(lesson, html)
                except Exception as exc:
                    logger.error("[%d/%d] failed %s: %s", done, total, lesson.url, exc)
                else:
                    logger.info("[%d/%d] %s", done, total, lesson.title)

        if self._image_downloader:
            self._image_downloader.download_all(course)
        for storage in self._storages:
            storage.save(course)
        return course

    @staticmethod
    def _chapter_as_lesson(chapter: Chapter) -> Lesson:
        return Lesson(slug=chapter.slug, title=chapter.title, url=chapter.url, order=1,
                      lesson_type=LessonType.LESSON)
