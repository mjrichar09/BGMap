"""Stage 2c (movies): download IMDb's official ratings dataset.

One ~7 MB file with every title's average rating and vote count, joined in
parse on the IMDb IDs from TMDB. IMDb's datasets are for personal,
non-commercial use, and a public page must credit IMDb.

    python -m src.movies.imdb            # skips the download if already cached
    python -m src.movies.imdb --refresh  # fetch the latest (IMDb updates it daily)
"""

import argparse

import requests

from src.common import domain_dir

URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
FILENAME = "imdb_ratings.tsv.gz"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    out = domain_dir("movies") / FILENAME
    if out.exists() and not args.refresh:
        print(f"Already have {out}; pass --refresh to update")
        return
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    tmp = out.with_suffix(".tmp")
    tmp.write_bytes(r.content)
    tmp.replace(out)
    print(f"Wrote {len(r.content) / 1e6:.1f} MB to {out}")


if __name__ == "__main__":
    main()
