"""Stage 1 (movies): build the ID list from TMDB's discover endpoint.

TMDB has no ranked list like BGG's, so a minimum vote count stands in for
"ranked". Discover caps results at 500 pages (10,000 movies) per query, so we
query one release year at a time.

    python -m src.movies.ids --min-votes 100
"""

import argparse
import datetime as dt

import pandas as pd

from src.common import domain_dir
from src.movies.tmdb import TMDB

MAX_PAGES = 500


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-votes", type=int, default=100)
    ap.add_argument("--start-year", type=int, default=1900)
    ap.add_argument("--end-year", type=int, default=dt.date.today().year)
    args = ap.parse_args()

    client = TMDB()
    rows = {}
    for year in range(args.start_year, args.end_year + 1):
        page = 1
        while True:
            data = client.get(
                "/discover/movie",
                primary_release_year=year,
                sort_by="vote_count.desc",
                include_adult="false",
                include_video="false",
                page=page,
                **{"vote_count.gte": args.min_votes},
            )
            for m in data["results"]:
                rows[m["id"]] = {
                    "id": m["id"],
                    "title": m["title"],
                    "year": year,
                    "vote_count": m["vote_count"],
                    "vote_average": m["vote_average"],
                    "popularity": m["popularity"],
                }
            if data["total_results"] > MAX_PAGES * 20 and page == 1:
                print(f"  warning: {year} has {data['total_results']} results; only 10,000 are reachable")
            if page >= min(data["total_pages"], MAX_PAGES):
                break
            page += 1
        if data["total_results"]:
            print(f"{year}: {data['total_results']}")

    out = domain_dir("movies") / "ids.csv"
    ids = pd.DataFrame(rows.values()).sort_values("vote_count", ascending=False)
    ids.to_csv(out, index=False)
    print(f"Wrote {len(ids):,} movies to {out}")


if __name__ == "__main__":
    main()
