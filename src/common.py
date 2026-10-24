"""Shared paths and helpers used by every domain's pipeline."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

URL_RE = re.compile(r"https?://\S+")
WS_RE = re.compile(r"\s+")
NO_SPACE_RE = re.compile(r"[฀-๿぀-ヿ㐀-䶿一-鿿豈-﫿]")


def domain_dir(domain: str) -> Path:
    """data/<domain>/, created on first use."""
    path = DATA / domain
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Read KEY=value lines from .env into os.environ without overriding real env vars."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def clean_text(text: str | None) -> str:
    """Strip URLs and collapse whitespace."""
    if not text:
        return ""
    return WS_RE.sub(" ", URL_RE.sub("", text)).strip()


def word_count(text: str) -> int:
    """Whitespace words, plus about one word per two characters in scripts
    written without spaces (Chinese, Japanese, Thai)."""
    unspaced = len(NO_SPACE_RE.findall(text))
    return len(NO_SPACE_RE.sub(" ", text).split()) + unspaced // 2
