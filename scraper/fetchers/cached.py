import logging
from pathlib import Path
from urllib.parse import urlparse

from scraper.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)


class CachedFetcher(BaseFetcher):
    """Decorator: serves pages from disk, delegating to the wrapped fetcher on a miss."""

    def __init__(self, fetcher: BaseFetcher, cache_dir: Path):
        self._fetcher = fetcher
        self._cache_dir = cache_dir

    def fetch(self, url: str) -> str:
        path = self._path_for(url, suffix=".html")
        if path.exists():
            logger.debug("Cache hit: %s", url)
            return path.read_text(encoding="utf-8")
        html = self._fetcher.fetch(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return html

    def fetch_bytes(self, url: str) -> bytes:
        path = self._path_for(url, subdir="_assets")
        if path.exists():
            return path.read_bytes()
        data = self._fetcher.fetch_bytes(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return data

    def _path_for(self, url: str, suffix: str = "", subdir: str = "") -> Path:
        relative = urlparse(url).path.strip("/") or "index"
        return self._cache_dir / subdir / f"{relative}{suffix}"
