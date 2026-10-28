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


@dataclass
class Lesson:
    slug: str
    title: str
    url: str
    order: int
    lesson_type: LessonType = LessonType.LESSON
    content_html: str = ""
    images: list[Image] = field(default_factory=list)


@dataclass
class Chapter:
    slug: str
    title: str
    url: str
    order: int
    lessons: list[Lesson] = field(default_factory=list)


@dataclass
class Course:
    slug: str
    title: str
    url: str
    chapters: list[Chapter] = field(default_factory=list)

    def iter_lessons(self) -> Iterator[tuple[Chapter, Lesson]]:
        for chapter in self.chapters:
            for lesson in chapter.lessons:
                yield chapter, lesson
