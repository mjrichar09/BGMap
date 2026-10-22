"""Shared paths and settings for the pipeline stages.

Every stage reads and writes under DATA_DIR, which defaults to ./data. Point
BGMAP_DATA somewhere else (e.g. data/stub) to run the pipeline on stub data
without touching the real cache.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("BGMAP_DATA", ROOT / "data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = ROOT / DATA_DIR

RAW_DIR = DATA_DIR / "raw"
IDS_CSV = DATA_DIR / "ids.csv"
GAMES_PARQUET = DATA_DIR / "games.parquet"
EMBED_DIR = DATA_DIR / "embeddings"
LAYOUT_DIR = DATA_DIR / "layouts"
WEB_DIR = ROOT / "web"

# No "www.": BGG ignores the bearer token on www.boardgamegeek.com.
BGG_API = "https://boardgamegeek.com/xmlapi2"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader so tokens can live outside the shell profile."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


# Embedding models. `prefix` is prepended to every document; `max_seq_length`
# caps tokens per text (long BGG descriptions are the point of a long-context
# model, but 32k tokens per text won't fit a 10 GB card at any useful batch).
MODELS = {
    "qwen3": {
        "name": "Qwen/Qwen3-Embedding-0.6B",
        "prefix": "",
        "max_seq_length": 2048,
        "batch_size": 16,
    },
    "nomic": {
        "name": "nomic-ai/nomic-embed-text-v1.5",
        "prefix": "search_document: ",
        "max_seq_length": 2048,
        "batch_size": 32,
        "trust_remote_code": True,
    },
    "bge": {
        "name": "BAAI/bge-base-en-v1.5",
        "prefix": "",
        "max_seq_length": 512,
        "batch_size": 64,
    },
    # Dependency-free TF-IDF + SVD stand-in. Used for stub runs and tests, and
    # as a bag-of-words floor the neural models should clearly beat.
    "tfidf": {"name": "tfidf-svd", "dim": 128},
}
PRIMARY_MODEL = "qwen3"


def embedding_paths(model_key: str) -> tuple[Path, Path]:
    return EMBED_DIR / f"{model_key}.npy", EMBED_DIR / f"{model_key}.json"


def map_path(model_key: str) -> Path:
    return DATA_DIR / f"map_{model_key}.parquet"


def neighbors_path(model_key: str) -> Path:
    return DATA_DIR / f"neighbors_{model_key}.npy"


def labels_cache_path(model_key: str) -> Path:
    return DATA_DIR / f"labels_{model_key}.json"


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    tmp.replace(path)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
