"""Fill course-level metadata for courses that are already in the database.

Fetches only each course's main page (one request per course): the preview image, the meta
description and the JSON-LD data (instructor, workload, provider). Everything else is reused
from output/apxml.db, so the lessons are not downloaded again.

    python enrich.py                    # all courses
    python enrich.py --course advanced-jax
    python enrich.py --shard 0/3        # parallel workers, like export.py
"""
import argparse
import logging

from scraper.config import Settings
from scraper.fetchers.http import HttpFetcher
from scraper.images import ImageDownloader
from scraper.parsers.course import CoursePageParser
from scraper.storage.factory import get_storage
from scraper.storage.sqlite_reader import SqliteReader

logger = logging.getLogger("enrich")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add preview image and metadata to courses in the database")
    parser.add_argument("--course", nargs="+", metavar="SLUG", help="Only these courses (default: all)")
    parser.add_argument("--shard", metavar="K/N", help="Process every N-th course starting at K (0-based)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    settings = Settings.from_env()
    reader = SqliteReader(settings.output_dir / "apxml.db")
    fetcher = HttpFetcher(settings)  # no cache: these pages are fetched once
    parser = CoursePageParser()
    downloader = ImageDownloader(fetcher, settings)
    storages = [get_storage(name, settings) for name in ("sqlite", "csv", "markdown")]

    slugs = args.course or reader.course_slugs()
    if args.shard:
        first, count = map(int, args.shard.split("/"))
        slugs = slugs[first::count]

    failed = []
    for index, slug in enumerate(slugs, 1):
        course = reader.load_course(slug)
        try:
            page = parser.parse(fetcher.fetch(course.url), course.url)
        except Exception as exc:
            logger.error("(%d/%d) %s: %s", index, len(slugs), slug, exc)
            failed.append(slug)
            continue
        course.description = page.description
        course.preview_url = page.preview_url
        course.structured_data = page.structured_data
        downloader.download_preview(course)
        for storage in storages:
            storage.save(course)
        logger.info("(%d/%d) %s: preview=%s", index, len(slugs), slug, course.preview_path)
    if failed:
        logger.warning("%d course(s) failed: %s", len(failed), ", ".join(failed))


if __name__ == "__main__":
    main()
