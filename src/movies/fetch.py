"""Stage 2 (movies): fetch details for every ID and cache one JSON per movie.

Resumable: movies already in data/movies/raw/ are skipped, and IDs that
returned 404 on an earlier run are not retried. Other failures are logged to
data/movies/fetch_errors.csv and retried on the next run.

    python -m src.movies.fetch --workers 8 --rate 20
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

from src.common import domain_dir
from src.movies.tmdb import TMDB

APPEND = "keywords,credits,external_ids,translations,release_dates"
CREW_JOBS = {"Director", "Screenplay", "Writer", "Novel", "Original Music Composer", "Director of Photography"}
TOP_CAST = 10
# TMDB tags Cantonese films "cn", but their translations are filed under "zh".
LANG_ALIASES = {"cn": "zh"}


def trim_credits(credits: dict) -> dict:
    """Full credits run to hundreds of KB; keep only the people we use."""
    return {
        "cast": [
            {"name": c["name"], "character": c.get("character")}
            for c in sorted(credits.get("cast", []), key=lambda c: c.get("order", 999))[:TOP_CAST]
        ],
        "crew": [{"name": c["name"], "job": c["job"]} for c in credits.get("crew", []) if c.get("job") in CREW_JOBS],
    }


def trim_translations(translations: dict, original_language: str) -> list[dict]:
    """Keep only original-language overviews, the fallback for films with no English one."""
    lang = LANG_ALIASES.get(original_language, original_language)
    if lang == "en":
        return []
    return [
        {
            "iso_639_1": t["iso_639_1"],
            "iso_3166_1": t["iso_3166_1"],
            "title": t["data"].get("title"),
            "overview": t["data"].get("overview"),
        }
        for t in translations.get("translations", [])
        if t["iso_639_1"] == lang and t["data"].get("overview")
    ]


def trim_release_dates(release_dates: dict) -> list[dict]:
    """Keep only US certifications (G, PG, R, ...)."""
    for country in release_dates.get("results", []):
        if country["iso_3166_1"] == "US":
            return [
                {"certification": r["certification"], "type": r["type"]}
                for r in country["release_dates"]
                if r.get("certification")
            ]
    return []


def fetch_one(client: TMDB, movie_id: int, raw_dir) -> None:
    data = client.get(f"/movie/{movie_id}", append_to_response=APPEND, language="en-US")
    data["credits"] = trim_credits(data.get("credits", {}))
    data["translations"] = trim_translations(data.get("translations", {}), data.get("original_language", ""))
    data["release_dates"] = trim_release_dates(data.get("release_dates", {}))
    tmp = raw_dir / f"{movie_id}.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(raw_dir / f"{movie_id}.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rate", type=float, default=20.0, help="max requests per second")
    ap.add_argument("--limit", type=int, help="only fetch the first N missing IDs (for testing)")
    args = ap.parse_args()

    base = domain_dir("movies")
    raw_dir = base / "raw"
    raw_dir.mkdir(exist_ok=True)
    errors_path = base / "fetch_errors.csv"

    missing = set()
    if errors_path.exists():
        prev = pd.read_csv(errors_path)
        missing = set(prev.loc[prev["status"] == 404, "id"])

    ids = pd.read_csv(base / "ids.csv")["id"].tolist()
    todo = [i for i in ids if i not in missing and not (raw_dir / f"{i}.json").exists()]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(ids):,} IDs, {len(ids) - len(todo):,} done or missing, fetching {len(todo):,}")

    client = TMDB(rate=args.rate)
    errors = [{"id": i, "status": 404, "message": "not found"} for i in missing]
    with ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(fetch_one, client, i, raw_dir): i for i in todo}
        for n, fut in enumerate(as_completed(futures), 1):
            try:
                fut.result()
            except requests.HTTPError as e:
                errors.append({"id": futures[fut], "status": e.response.status_code, "message": str(e)})
            except Exception as e:
                errors.append({"id": futures[fut], "status": 0, "message": str(e)})
            if n % 500 == 0 or n == len(todo):
                print(f"  {n:,}/{len(todo):,}")

    pd.DataFrame(errors, columns=["id", "status", "message"]).to_csv(errors_path, index=False)
    print(f"Done. {len(errors) - len(missing)} new errors; see {errors_path}")


if __name__ == "__main__":
    main()
