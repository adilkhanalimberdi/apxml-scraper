import json
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scraper.models import Chapter, Course, Lesson, LessonType
from scraper.parsers.base import BaseParser
from utils.url import course_slug, normalize, to_absolute


class CoursePageParser(BaseParser[Course]):
    """Parses a course page into a Course with chapters and lesson stubs (no content)."""

    def parse(self, html: str, url: str) -> Course:
        soup = BeautifulSoup(html, "html.parser")
        slug = course_slug(url)
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        course = Course(slug=slug, title=self._title(soup), url=normalize(url))
        self._fill_metadata(course, soup)

        chapters: dict[str, Chapter] = {}
        seen: set[str] = set()
        for link in soup.select(f'a[href^="/courses/{slug}/"]'):
            href = normalize(link["href"])
            if href in seen:
                continue
            seen.add(href)

            parts = href.split("/")[3:]  # courses, <slug>, <chapter>[, <lesson>]
            title = link.get_text(" ", strip=True)
            if len(parts) == 1:
                chapter = Chapter(slug=parts[0], title=title, url=to_absolute(base_url, href),
                                  order=len(chapters) + 1)
                chapters[parts[0]] = chapter
                course.chapters.append(chapter)
            elif len(parts) == 2 and parts[0] in chapters:
                chapter = chapters[parts[0]]
                chapter.lessons.append(Lesson(
                    slug=parts[1], title=title, url=to_absolute(base_url, href),
                    order=len(chapter.lessons) + 1, lesson_type=self._lesson_type(parts[1]),
                ))
        return course

    @staticmethod
    def _fill_metadata(course: Course, soup: BeautifulSoup) -> None:
        image = soup.find("meta", attrs={"property": "og:image"})
        course.preview_url = image["content"] if image and image.get("content") else ""
        description = soup.find("meta", attrs={"name": "description"})
        course.description = description["content"] if description and description.get("content") else ""
        blocks = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                blocks.append(json.loads(script.string or ""))
            except ValueError:
                continue
        course.structured_data = json.dumps(blocks, ensure_ascii=False) if blocks else ""

    @staticmethod
    def _title(soup: BeautifulSoup) -> str:
        h1 = soup.find("h1")
        return h1.get_text(strip=True) if h1 else ""

    @staticmethod
    def _lesson_type(slug: str) -> LessonType:
        if slug == "quiz":
            return LessonType.QUIZ
        if slug.startswith("practice"):
            return LessonType.PRACTICE
        return LessonType.LESSON
