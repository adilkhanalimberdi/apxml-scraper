import argparse

from scraper.config import Settings
from utils.url import course_slug, normalize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape a course from apxml.com")
    parser.add_argument("url", help="Course URL, e.g. https://apxml.com/courses/introduction-to-deep-learning/")
    parser.add_argument("--format", default="csv", choices=["csv"], help="Output format")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    url = normalize(args.url)
    print(f"Course: {course_slug(url)} ({url}), format={args.format}, delay={settings.delay}s")


if __name__ == "__main__":
    main()
