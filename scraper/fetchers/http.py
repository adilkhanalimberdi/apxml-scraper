import logging
import time

import requests

from scraper.config import Settings
from scraper.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpFetcher(BaseFetcher):
    def __init__(self, settings: Settings, timeout: float = 30, max_retries: int = 5):
        self.delay = settings.delay
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_request = 0.0
        self._session = requests.Session()
        self._session.headers["User-Agent"] = settings.user_agent

    def fetch(self, url: str) -> str:
        return self._get(url).content.decode("utf-8", errors="replace")

    def fetch_bytes(self, url: str) -> bytes:
        return self._get(url).content

    def _get(self, url: str) -> requests.Response:
        for attempt in range(1, self.max_retries + 1):
            self._wait()
            try:
                response = self._session.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                logger.warning("Request failed (%s), attempt %d/%d", exc, attempt, self.max_retries)
            else:
                if response.status_code not in RETRY_STATUSES:
                    response.raise_for_status()
                    return response
                logger.warning("HTTP %d for %s, attempt %d/%d", response.status_code, url, attempt, self.max_retries)
                if response.status_code == 429:  # rate limited: back off for real, honour Retry-After
                    time.sleep(self._retry_after(response, default=30 * attempt))
                    continue
            time.sleep(self.delay * 2 ** attempt)
        raise RuntimeError(f"Failed to fetch {url} after {self.max_retries} attempts")

    @staticmethod
    def _retry_after(response: requests.Response, default: float) -> float:
        value = response.headers.get("Retry-After", "")
        return min(float(value), 300) if value.isdigit() else default

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.monotonic()
