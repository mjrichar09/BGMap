"""Dry-run input: build games.parquet from a public BGG dump instead of the API.

Takes the "games_detailed_info" CSV format (the XML API's `thing` output
flattened, as in the long-running Kaggle BGG dataset; a 2025 copy is on
Hugging Face as mmpa/board_game_analysis) and writes the same schema as
parse.py, so stages 4-6 and evaluation run on real descriptions before our
own fetch exists. Games are limited to those in data/ids.csv, with rank and
rating stats taken from that (newer) ranks file.

The dump is scraped BGG data with no stated license: keep it local, use it for
tuning only, and replace it with our own fetch once the API token arrives.

    python src/import_external.py data/external/games_detailed_info2025.csv --out data/dryrun
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

import pandas as pd

from common import ROOT
from parse import LINK_FIELDS, clean_description, finalize


def parse_list(value) -> list[str]:
    if not isinstance(value, str) or not value.startswith("["):
        return []
    try:
        return [str(v) for v in ast.literal_eval(value)]
    except (ValueError, SyntaxError):
        return []


def best_from_poll(value) -> int | None:
    """Same rule as parse.best_player_count, on the dump's repr'd poll."""
    if not isinstance(value, str) or not value.startswith("["):
        return None
    try:
        poll = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return None
    best, best_votes = None, 0
    for results in poll if isinstance(poll, list) else []:
        count = str(results.get("@numplayers", ""))
        if not count.isdigit():
            continue
        entries = results.get("result", [])
        votes = next((int(r.get("@numvotes", 0)) for r in entries if r.get("@value") == "Best"), 0)
        if votes > best_votes:
            best, best_votes = int(count), votes
    return best


def num(series: pd.Series, zero_is_null: bool = False) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce")
    return out.mask(out == 0) if zero_is_null else out


def convert(dump: pd.DataFrame, ranks: pd.DataFrame) -> pd.DataFrame:
    dump = dump[dump["type"] == "boardgame"].drop_duplicates("id", keep="last")
    current = ranks[["id", "rank", "bayesaverage", "usersrated"]].rename(
        columns={"bayesaverage": "cur_bayes", "usersrated": "cur_usersrated"})
    dump = dump.merge(current, on="id", how="inner")
    df = pd.DataFrame({
        "id": dump["id"].astype(int),
        "type": "boardgame",
        "name": dump["name"],
        "year": num(dump["yearpublished"], zero_is_null=True),
        "thumbnail": dump["thumbnail"].where(dump["thumbnail"].notna(), None),
        "description": dump["description"].map(clean_description),
        "min_players": num(dump["minplayers"], zero_is_null=True),
        "max_players": num(dump["maxplayers"], zero_is_null=True),
        "best_players": dump["suggested_num_players"].map(best_from_poll),
        "playing_time": num(dump["playingtime"], zero_is_null=True),
        "min_age": num(dump["minage"], zero_is_null=True),
        "rank": dump["rank"],
        "bayes_average": dump["cur_bayes"],
        "average": num(dump["average"]),
        "users_rated": dump["cur_usersrated"],
        "owned": num(dump["owned"]),
        "weight": num(dump["averageweight"], zero_is_null=True),
    })
    for link_type, field in LINK_FIELDS.items():
        df[field] = dump[link_type].map(parse_list).to_numpy()
    return finalize(df)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump_csv", type=Path)
    ap.add_argument("--ids", type=Path, default=ROOT / "data" / "ids.csv", help="output of src/ids.py")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "dryrun")
    args = ap.parse_args()

    dump = pd.read_csv(args.dump_csv, low_memory=False)
    ranks = pd.read_csv(args.ids)
    df = convert(dump, ranks)
    args.out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out / "games.parquet", index=False)
    print(f"{len(dump):,} dump rows, {len(ranks):,} ranked IDs -> {len(df):,} games "
          f"({df['short_desc'].sum():,} short descriptions) -> {args.out / 'games.parquet'}")


if __name__ == "__main__":
    main()
