import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from scraper.config import Settings
from scraper.fetchers.base import BaseFetcher
from scraper.models import Course, Image, Lesson

logger = logging.getLogger(__name__)

RETRIES = 3


class ImageDownloader:
    """Saves lesson images to output/<course>/images and fills Image.local_path.

    Image URLs are pre-signed and short-lived, and the site may serve a page whose signatures
    already expired. On failure `refresh` is called to re-read the page and return fresh URLs.
    """

    def __init__(self, fetcher: BaseFetcher, settings: Settings):
        self._fetcher = fetcher
        self._output_dir = settings.output_dir

    def download_lesson(self, course_slug: str, lesson: Lesson,
                        refresh: Callable[[], dict[str, str]] | None = None) -> None:
        target = self._output_dir / course_slug / "images"
        pending = list(lesson.images)
        for attempt in range(1, RETRIES + 1):
            pending = [image for image in pending if not self._save(target, image)]
            if not pending or refresh is None or attempt == RETRIES:
                break
            time.sleep(3)  # let the site regenerate the page, then ask for fresh signed URLs
            try:
                fresh = refresh()
            except Exception as exc:
                logger.warning("Refreshing %s failed: %s", lesson.url, exc)
                break
            for image in pending:
                image.fetch_url = fresh.get(image.src, image.fetch_url)
        for image in pending:
            logger.warning("Image not downloaded: %s", image.src)

    def download_preview(self, course: Course) -> None:
        """Save the course's og:image as output/<course>/preview.<png|jpg|webp>."""
        if not course.preview_url:
            return
        try:
            data = self._fetcher.fetch_bytes(course.preview_url)
        except Exception as exc:
            logger.warning("Preview failed for %s: %s", course.slug, exc)
            return
        extension = self._extension(data)
        target = self._output_dir / course.slug
        target.mkdir(parents=True, exist_ok=True)
        (target / f"preview.{extension}").write_bytes(data)
        course.preview_path = f"preview.{extension}"

    @staticmethod
    def _extension(data: bytes) -> str:
        if data.startswith(b"\x89PNG"):
            return "png"
        if data.startswith(b"\xff\xd8"):
            return "jpg"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "webp"
        return "bin"

    def _save(self, target: Path, image: Image) -> bool:
        name = self._filename(image.src)
        path = target / name
        if not path.exists():
            try:
                data = self._fetcher.fetch_bytes(image.fetch_url or image.src)
            except Exception as exc:
                logger.debug("Image attempt failed %s: %s", image.src, exc)
                return False
            target.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        image.local_path = f"images/{name}"
        return True

    @staticmethod
    def _filename(src: str) -> str:
        original = PurePosixPath(urlparse(src).path).name or "image"
        return f"{hashlib.sha1(src.encode()).hexdigest()[:10]}_{original}"
