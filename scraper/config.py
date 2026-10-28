import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    base_url: str
    user_agent: str
    delay: float
    cache_dir: Path = ROOT_DIR / "cache"
    output_dir: Path = ROOT_DIR / "output"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            base_url=os.environ["BASE_URL"].rstrip("/"),
            user_agent=os.getenv("USER_AGENT") or "apxml-scraper/0.1",
            delay=float(os.getenv("DELAY") or "1.5"),
        )
