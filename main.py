import argparse
import logging

from scraper.config import Settings
from scraper.discovery import SitemapCourseDiscovery
from scraper.fetchers.cached import CachedFetcher
from scraper.fetchers.http import HttpFetcher
from scraper.images import ImageDownloader
from scraper.parsers.course import CoursePageParser
from scraper.parsers.lesson import LessonPageParser
from scraper.pipeline import CourseScraper
from scraper.storage.factory import FORMATS, get_storage
from utils.url import normalize

logger = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape courses from apxml.com")
    parser.add_argument("url", nargs="?", help="Course URL, e.g. https://apxml.com/courses/introduction-to-deep-learning/")
    parser.add_argument("--all", action="store_true", help="Scrape every course listed in the sitemap")
    parser.add_argument("--limit", type=int, help="With --all: only the first N courses")
    parser.add_argument("--format", nargs="+", default=["csv"], choices=FORMATS, help="Output format(s)")
    parser.add_argument("--download-images", action="store_true", help="Save lesson images to output/<course>/images")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    if not args.url and not args.all:
        parser.error("give a course URL or use --all")
    return args


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    settings = Settings.from_env()
    fetcher = CachedFetcher(HttpFetcher(settings), settings.cache_dir)
    scraper = CourseScraper(
        fetcher=fetcher,
        course_parser=CoursePageParser(),
        lesson_parser=LessonPageParser(),
        storages=[get_storage(name, settings) for name in args.format],
        image_downloader=ImageDownloader(fetcher, settings) if args.download_images else None,
    )

    if args.all:
        urls = SitemapCourseDiscovery(fetcher, settings.base_url).discover()[: args.limit]
        logger.info("Found %d courses", len(urls))
    else:
        urls = [normalize(args.url)]

    failed = []
    for url in urls:
        try:
            scraper.scrape(url)
        except Exception:
            logger.exception("Course failed: %s", url)
            failed.append(url)
    if failed:
        logger.warning("%d course(s) failed: %s", len(failed), ", ".join(failed))


if __name__ == "__main__":
    main()
