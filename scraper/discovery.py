import re

from scraper.fetchers.base import BaseFetcher
from utils.url import normalize

LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")


class SitemapCourseDiscovery:
    """Finds every course URL (https://host/courses/<slug>) listed in sitemap.xml."""

    def __init__(self, fetcher: BaseFetcher, base_url: str):
        self._fetcher = fetcher
        self._base_url = base_url

    def discover(self) -> list[str]:
        xml = self._fetcher.fetch(f"{self._base_url}/sitemap.xml")
        urls = []
        for loc in LOC_RE.findall(xml):
            url = normalize(loc)
            segments = url.split("/")[3:]
            if len(segments) == 2 and segments[0] == "courses" and url not in urls:
                urls.append(url)
        return urls
