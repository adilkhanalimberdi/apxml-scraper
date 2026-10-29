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
        self.failed_pages = 0  # lesson pages that failed in the last scrape()

    def scrape(self, course_url: str) -> Course:
        course = self._course_parser.parse(self._fetcher.fetch(course_url), course_url)
        total = sum(len(chapter.lessons) or 1 for chapter in course.chapters)
        logger.info("%s: %d chapters, %d pages", course.slug, len(course.chapters), total)

        self._fill_overview(course, course_url, self._fetcher.fetch(course_url))
        if self._image_downloader:
            self._image_downloader.download_preview(course)

        done = 0
        self.failed_pages = 0
        for chapter in course.chapters:
            # Chapter overview pages (e.g. the final project) are stored as a pseudo-lesson
            # only when the chapter has no lessons of its own.
            if not chapter.lessons:
                chapter.lessons.append(self._chapter_as_lesson(chapter))
            else:
                self._safe_chapter_overview(chapter)
            for lesson in chapter.lessons:
                done += 1
                try:
                    html = self._fetcher.fetch(lesson.url)
                    self._lesson_parser.parse_into(lesson, html)
                except Exception as exc:
                    self.failed_pages += 1
                    logger.error("[%d/%d] failed %s: %s", done, total, lesson.url, exc)
                else:
                    logger.info("[%d/%d] %s", done, total, lesson.title)
                    if self._image_downloader and lesson.images:
                        self._image_downloader.download_lesson(
                            course.slug, lesson, refresh=lambda lesson=lesson: self._fresh_image_urls(lesson))

        for storage in self._storages:
            storage.save(course)
        return course

    def _fresh_image_urls(self, lesson: Lesson) -> dict[str, str]:
        """Re-read the lesson page (bypassing the cache) and return {clean src: signed URL}."""
        page = Lesson(slug=lesson.slug, title=lesson.title, url=lesson.url, order=lesson.order)
        self._lesson_parser.parse_into(page, self._fetcher.fetch_fresh(lesson.url))
        return {image.src: image.fetch_url for image in page.images}

    def _safe_chapter_overview(self, chapter: Chapter) -> None:
        try:
            self._fill_overview(chapter, chapter.url, self._fetcher.fetch(chapter.url))
        except Exception as exc:
            logger.error("chapter overview failed %s: %s", chapter.url, exc)

    def _fill_overview(self, target: Course | Chapter, url: str, html: str) -> None:
        page = Lesson(slug=target.slug, title=target.title, url=url, order=0)
        self._lesson_parser.parse_into(page, html)
        target.overview_html = page.content_html
        target.overview_markdown = page.content_markdown
        if page.images or page.charts:
            logger.warning("%s: images/charts on overview page are not stored", url)

    @staticmethod
    def _chapter_as_lesson(chapter: Chapter) -> Lesson:
        return Lesson(slug=chapter.slug, title=chapter.title, url=chapter.url, order=1,
                      lesson_type=LessonType.LESSON)
