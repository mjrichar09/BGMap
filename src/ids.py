"""Stage 1: turn BGG's ranks CSV into the list of game IDs to fetch.

Download the CSV by hand while logged in (it needs an approved application):
https://boardgamegeek.com/data_dumps/bg_ranks  ->  boardgames_ranks.csv
(it usually arrives zipped; this script reads .csv or .zip).

    python src/ids.py path/to/boardgames_ranks.zip
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import IDS_CSV


def ranked_base_games(ranks: pd.DataFrame) -> pd.DataFrame:
    """Keep ranked base games: not an expansion, rank > 0."""
    ranks = ranks.copy()
    ranks["rank"] = pd.to_numeric(ranks["rank"], errors="coerce").fillna(0).astype(int)
    ranks["is_expansion"] = pd.to_numeric(ranks["is_expansion"], errors="coerce").fillna(0).astype(int)
    keep = ranks[(ranks["is_expansion"] == 0) & (ranks["rank"] > 0)]
    cols = [c for c in ["id", "name", "yearpublished", "rank", "bayesaverage", "usersrated"] if c in keep]
    return keep[cols].sort_values("rank").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ranks_csv", type=Path, help="boardgames_ranks.csv or the .zip it comes in")
    args = ap.parse_args()

    ranks = pd.read_csv(args.ranks_csv)  # pandas reads single-file zips directly
    ids = ranked_base_games(ranks)
    IDS_CSV.parent.mkdir(parents=True, exist_ok=True)
    ids.to_csv(IDS_CSV, index=False)
    print(f"{len(ranks):,} rows in ranks file -> {len(ids):,} ranked base games -> {IDS_CSV}")


if __name__ == "__main__":
    main()
