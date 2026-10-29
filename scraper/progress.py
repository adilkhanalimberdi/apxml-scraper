from pathlib import Path


class DoneRegistry:
    """Remembers which courses are fully saved, so --all can resume after the cache is purged."""

    def __init__(self, path: Path):
        self._path = path
        self._done = set(path.read_text(encoding="utf-8").split()) if path.exists() else set()

    def __contains__(self, slug: str) -> bool:
        return slug in self._done

    def add(self, slug: str) -> None:
        self._done.add(slug)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as file:
            file.write(slug + "\n")
