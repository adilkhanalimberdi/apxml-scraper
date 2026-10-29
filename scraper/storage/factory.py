from scraper.config import Settings
from scraper.storage.base import BaseStorage
from scraper.storage.csv_storage import CsvStorage
from scraper.storage.markdown_storage import MarkdownStorage
from scraper.storage.sqlite_storage import SqliteStorage

FORMATS = ("csv", "sqlite", "markdown")


def get_storage(name: str, settings: Settings) -> BaseStorage:
    """Register new output formats here (e.g. json, postgres)."""
    if name == "csv":
        return CsvStorage(settings.output_dir)
    if name == "sqlite":
        return SqliteStorage(settings.output_dir / "apxml.db")
    if name == "markdown":
        return MarkdownStorage(settings.output_dir)
    raise ValueError(f"Unknown storage format: {name} (available: {', '.join(FORMATS)})")
