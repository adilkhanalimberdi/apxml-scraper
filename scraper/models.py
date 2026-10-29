from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class LessonType(str, Enum):
    LESSON = "lesson"
    PRACTICE = "practice"
    QUIZ = "quiz"


@dataclass
class Image:
    src: str
    alt: str = ""
    local_path: str | None = None
    fetch_url: str = ""  # pre-signed URL (expires in ~1h), used for the download only, never stored


@dataclass
class Chart:
    chart_id: str
    kind: str  # "plotly" or "graphviz"
    definition: str  # Plotly figure as JSON, or Graphviz DOT source


@dataclass
class Lesson:
    slug: str
    title: str
    url: str
    order: int
    lesson_type: LessonType = LessonType.LESSON
    content_html: str = ""
    content_markdown: str = ""
    images: list[Image] = field(default_factory=list)
    charts: list[Chart] = field(default_factory=list)


@dataclass
class Chapter:
    slug: str
    title: str
    url: str
    order: int
    overview_html: str = ""
    overview_markdown: str = ""
    lessons: list[Lesson] = field(default_factory=list)


@dataclass
class Course:
    slug: str
    title: str
    url: str
    overview_html: str = ""  # description, level, prerequisites, what you'll learn
    overview_markdown: str = ""
    chapters: list[Chapter] = field(default_factory=list)

    def iter_lessons(self) -> Iterator[tuple[Chapter, Lesson]]:
        for chapter in self.chapters:
            for lesson in chapter.lessons:
                yield chapter, lesson
