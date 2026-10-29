from scraper.config import Settings
from scraper.storage.base import BaseStorage
from scraper.storage.csv_storage import CsvStorage
from scraper.storage.sqlite_storage import SqliteStorage

FORMATS = ("csv", "sqlite")


def get_storage(name: str, settings: Settings) -> BaseStorage:
    """Register new output formats here (e.g. json, postgres)."""
    if name == "csv":
        return CsvStorage(settings.output_dir)
    if name == "sqlite":
        return SqliteStorage(settings.output_dir / "apxml.db")
    raise ValueError(f"Unknown storage format: {name} (available: {', '.join(FORMATS)})")
