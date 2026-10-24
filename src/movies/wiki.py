"""Stage 2b (movies): pull Wikipedia plot summaries for richer embedding text.

TMDB overviews are short, so this fetches each film's English Wikipedia "Plot"
section. Wikidata IDs from the cached TMDB responses are resolved to enwiki
article titles (50 per request), then each article's plain text is fetched
and the plot section cut out. Results are cached one JSON per movie in
data/movies/wiki/, including misses, so reruns only fetch what's new.

Wikimedia asks for serial requests and a descriptive User-Agent. Set
WIKI_CONTACT (env or .env) to an email or URL to include in it: since 2026,
clients without contact info are limited to 10 requests/minute, and those
with it get 200 (https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits).

    python -m src.movies.wiki
"""

import argparse
import json
import os
import re
import time

import requests

from src.common import clean_text, domain_dir, load_dotenv

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
PLOT_HEADINGS = {"plot", "plot summary", "synopsis", "summary", "story", "premise"}
H2_RE = re.compile(r"^==\s*([^=].*?)\s*==\s*$", re.M)


class Wiki:
    def __init__(self, delay: float = 0.32):  # just under 200 requests/minute
        load_dotenv()
        contact = os.environ.get("WIKI_CONTACT", "").strip()
        if not contact:
            print("warning: WIKI_CONTACT is not set, so Wikimedia limits this to 10 requests/minute")
        agent = "BGMap/0.1 (personal embedding-map research project"
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"{agent}; {contact})" if contact else f"{agent})"
        self.delay = delay

    def get(self, url: str, maxlag: int | None = 5, **params) -> dict:
        """GET a MediaWiki API. Waiting out replication lag doesn't count toward the retry limit."""
        params = {"format": "json", "formatversion": 2, **params}
        if maxlag is not None:
            params["maxlag"] = maxlag
        attempt = 0
        while attempt < 6:
            time.sleep(self.delay)
            try:
                r = self.session.get(url, params=params, timeout=30)
            except requests.RequestException:
                time.sleep(2**attempt)
                attempt += 1
                continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(float(r.headers.get("Retry-After", 2**attempt)))
                attempt += 1
                continue
            r.raise_for_status()
            data = r.json()
            if data.get("error", {}).get("code") == "maxlag":
                time.sleep(float(r.headers.get("Retry-After", 5)))
                continue
            return data
        raise RuntimeError(f"Wikimedia request kept failing: {params}")


def extract_plot(text: str) -> tuple[str | None, str | None]:
    """Return (heading, body) of the first plot-like level-2 section."""
    heads = list(H2_RE.finditer(text))
    for i, h in enumerate(heads):
        if h.group(1).strip().lower() in PLOT_HEADINGS:
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            body = re.sub(r"^=+.*?=+\s*$", "", text[h.end() : end], flags=re.M)  # drop sub-headings
            return h.group(1).strip(), clean_text(body) or None
    return None, None


def resolve_titles(wiki: Wiki, qids: list[str]) -> dict[str, str]:
    """Map Wikidata IDs to English Wikipedia article titles.

    Wikidata's maxlag includes query-service lag, which routinely sits above
    5s and would block every request, so these light reads skip it.
    """
    titles = {}
    for i in range(0, len(qids), 50):
        data = wiki.get(
            WIKIDATA_API,
            maxlag=None,
            action="wbgetentities",
            ids="|".join(qids[i : i + 50]),
            props="sitelinks",
            sitefilter="enwiki",
        )
        for qid, entity in data.get("entities", {}).items():
            link = entity.get("sitelinks", {}).get("enwiki")
            if link:
                titles[qid] = link["title"]
    return titles


def fetch_plot(wiki: Wiki, title: str) -> dict:
    data = wiki.get(WIKIPEDIA_API, action="query", prop="extracts", explaintext=1, redirects=1, titles=title)
    pages = data.get("query", {}).get("pages", [])
    text = pages[0].get("extract", "") if pages else ""
    heading, plot = extract_plot(text)
    return {"title": title, "heading": heading, "plot": plot}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only fetch the first N missing movies (for testing)")
    args = ap.parse_args()

    base = domain_dir("movies")
    raw_dir, wiki_dir = base / "raw", base / "wiki"
    wiki_dir.mkdir(exist_ok=True)

    todo = {}  # wikidata id -> tmdb id
    no_qid = 0
    for path in raw_dir.glob("*.json"):
        if (wiki_dir / path.name).exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        qid = (d.get("external_ids") or {}).get("wikidata_id")
        if qid:
            todo[qid] = d["id"]
        else:
            no_qid += 1
            (wiki_dir / path.name).write_text(json.dumps({"title": None, "heading": None, "plot": None}), encoding="utf-8")
    if args.limit:
        todo = dict(list(todo.items())[: args.limit])
    print(f"{no_qid:,} new movies have no Wikidata ID; resolving {len(todo):,}")

    wiki = Wiki()
    titles = resolve_titles(wiki, list(todo))
    print(f"{len(titles):,} have an English Wikipedia article")

    found = 0
    for n, (qid, movie_id) in enumerate(todo.items(), 1):
        out = wiki_dir / f"{movie_id}.json"
        try:
            result = fetch_plot(wiki, titles[qid]) if qid in titles else {"title": None, "heading": None, "plot": None}
        except Exception as e:
            print(f"  {movie_id}: {e}")  # not cached, so it's retried next run
            continue
        found += result["plot"] is not None
        out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        if n % 500 == 0 or n == len(todo):
            print(f"  {n:,}/{len(todo):,}, {found:,} plots so far")
    print(f"Done. {found:,} plots found this run")


if __name__ == "__main__":
    main()
