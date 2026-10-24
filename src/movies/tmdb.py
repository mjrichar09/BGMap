"""Minimal TMDB API client: auth, a shared rate limit, and retries.

Set TMDB_API_KEY in the environment or in .env. Either credential from
themoviedb.org/settings/api works: the v4 "API Read Access Token" (starts with
"eyJ", sent as a Bearer header) or the short v3 "API Key" (sent as ?api_key=).
"""

import os
import threading
import time

import requests

from src.common import load_dotenv

BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/"


class TMDB:
    def __init__(self, rate: float = 20.0):
        load_dotenv()
        key = os.environ.get("TMDB_API_KEY", "").strip()
        if not key:
            raise SystemExit("Set TMDB_API_KEY in the environment or in .env")

        self.session = requests.Session()
        self.params = {}
        if key.startswith("eyJ"):
            self.session.headers["Authorization"] = f"Bearer {key}"
        else:
            self.params["api_key"] = key

        # TMDB allows roughly 50 requests/s per IP; stay well under it.
        self._interval = 1.0 / rate
        self._next = 0.0
        self._lock = threading.Lock()

    def _wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next)
            self._next = slot + self._interval
        time.sleep(max(0.0, slot - now))

    def get(self, path: str, **params) -> dict:
        """GET a TMDB path. Retries 429s and 5xx; raises HTTPError on other failures."""
        for attempt in range(6):
            self._wait()
            try:
                r = self.session.get(f"{BASE}{path}", params={**self.params, **params}, timeout=30)
            except requests.RequestException:
                time.sleep(2**attempt)
                continue
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2**attempt)))
                continue
            if r.status_code >= 500:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"TMDB request kept failing: {path}")
