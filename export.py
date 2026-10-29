"""Post-processing of already scraped data (reads output/apxml.db, never touches the website).

    python export.py markdown                 # one .md per page -> output/<course>/markdown/
    python export.py render                   # Graphviz/Plotly -> PNG in output/<course>/images/
    python export.py all --course advanced-jax
"""
import argparse
import logging

from scraper.config import Settings
from scraper.rendering.graphviz_renderer import GraphvizRenderer
from scraper.rendering.plotly_renderer import PlotlyRenderer
from scraper.rendering.service import ChartRenderService
from scraper.storage.factory import get_storage
from scraper.storage.sqlite_reader import SqliteReader

logger = logging.getLogger("export")

RENDERERS = {"graphviz": GraphvizRenderer, "plotly": PlotlyRenderer}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export markdown pages and render charts from the database")
    parser.add_argument("command", choices=["markdown", "render", "all"])
    parser.add_argument("--course", nargs="+", metavar="SLUG", help="Only these courses (default: all in the database)")
    parser.add_argument("--kind", nargs="+", choices=list(RENDERERS), default=list(RENDERERS), help="Chart kinds to render")
    parser.add_argument("--image-format", default="png", choices=["png", "svg"])
    parser.add_argument("--shard", metavar="K/N", help="Process every N-th course starting at K (0-based), to run N workers in parallel")
    parser.add_argument("--force", action="store_true", help="Re-render pictures that already exist")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    for noisy in ("choreographer", "kaleido", "plotly"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    settings = Settings.from_env()
    reader = SqliteReader(settings.output_dir / "apxml.db")

    service = None
    if args.command in ("render", "all"):
        service = ChartRenderService([RENDERERS[kind]() for kind in args.kind], settings,
                                     fmt=args.image_format, force=args.force)
    markdown = get_storage("markdown", settings) if args.command in ("markdown", "all") else None
    # rendering changes Chart.local_path, so persist it back to the database and the CSVs
    persist = [get_storage(name, settings) for name in ("sqlite", "csv")] if service else []

    slugs = args.course or reader.course_slugs()
    if args.shard:
        first, count = map(int, args.shard.split("/"))
        slugs = slugs[first::count]
    for index, slug in enumerate(slugs, 1):
        course = reader.load_course(slug)
        if service:
            stats = service.render_course(course)
            logger.info("(%d/%d) %s: rendered %d, skipped %d, failed %d", index, len(slugs), slug,
                        stats.rendered, stats.skipped, stats.failed)
            for storage in persist:
                storage.save(course)
        if markdown:
            markdown.save(course)
            logger.info("(%d/%d) %s: markdown written", index, len(slugs), slug)


if __name__ == "__main__":
    main()
