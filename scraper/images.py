import hashlib
import logging
from pathlib import PurePosixPath
from urllib.parse import urlparse

from scraper.config import Settings
from scraper.fetchers.base import BaseFetcher
from scraper.models import Course

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Saves lesson images to output/<course>/images and fills Image.local_path."""

    def __init__(self, fetcher: BaseFetcher, settings: Settings):
        self._fetcher = fetcher
        self._output_dir = settings.output_dir

    def download_all(self, course: Course) -> None:
        target = self._output_dir / course.slug / "images"
        for _, lesson in course.iter_lessons():
            for image in lesson.images:
                name = self._filename(image.src)
                path = target / name
                if not path.exists():
                    try:
                        data = self._fetcher.fetch_bytes(image.src)
                    except Exception as exc:
                        logger.warning("Image failed %s: %s", image.src, exc)
                        continue
                    target.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                image.local_path = f"images/{name}"

    @staticmethod
    def _filename(src: str) -> str:
        original = PurePosixPath(urlparse(src).path).name or "image"
        return f"{hashlib.sha1(src.encode()).hexdigest()[:10]}_{original}"
