"""Stage 3: parse cached XML into games.parquet, one row per ranked base game.

Also builds the text that gets embedded, "<name>. <cleaned description>",
and flags games whose description is too short to place reliably.

    python src/parse.py
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pandas as pd
from lxml import etree

from common import GAMES_PARQUET, RAW_DIR

SHORT_DESC_WORDS = 30

LINK_FIELDS = {
    "boardgamecategory": "categories",
    "boardgamemechanic": "mechanics",
    "boardgamefamily": "families",
    "boardgamedesigner": "designers",
    "boardgamepublisher": "publishers",
}

_BBCODE_URL = re.compile(r"\[url=[^\]]*\](.*?)\[/url\]", re.I | re.S)
_BBCODE_THING = re.compile(r"\[(?:thing|person|family|geeklist|user)=[^\]]*\](.*?)\[/\w+\]", re.I | re.S)
_BBCODE_TAG = re.compile(r"\[/?[a-z*]+(?:=[^\]]*)?\]", re.I)
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?)])")


def clean_description(text: str | None) -> str:
    """Strip entities, BBCode, HTML, URLs and repeated whitespace."""
    if not text:
        return ""
    # BGG double-escapes entities (e.g. "&amp;mdash;"); unescape until stable.
    for _ in range(3):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    text = _BBCODE_URL.sub(r"\1", text)
    text = _BBCODE_THING.sub(r"\1", text)
    text = _BBCODE_TAG.sub(" ", text)
    text = _HTML_TAG.sub(" ", text)
    text = _URL.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    # Removed tags leave gaps like "Catan[/i]," -> "Catan ,".
    return _SPACE_BEFORE_PUNCT.sub(r"\1", text).replace("( ", "(")


def _value(item, tag: str, cast=str):
    el = item.find(tag)
    if el is None:
        return None
    raw = el.get("value")
    if raw in (None, "", "Not Ranked"):
        return None
    try:
        return cast(raw)
    except ValueError:
        return None


def best_player_count(item) -> int | None:
    """Player count with the most "Best" votes in the suggested_numplayers poll."""
    poll = item.find("poll[@name='suggested_numplayers']")
    if poll is None:
        return None
    best, best_votes = None, 0
    for results in poll.iterfind("results"):
        count = results.get("numplayers", "")
        if not count.isdigit():  # skip "4+" style buckets
            continue
        el = results.find("result[@value='Best']")
        votes = int(el.get("numvotes", 0)) if el is not None else 0
        if votes > best_votes:
            best, best_votes = int(count), votes
    return best


def parse_item(item) -> dict:
    ratings = item.find("statistics/ratings")
    rank = None
    if ratings is not None:
        el = ratings.find("ranks/rank[@name='boardgame']")
        if el is not None and el.get("value", "").isdigit():
            rank = int(el.get("value"))

    def stat(tag, cast=float):
        return _value(ratings, tag, cast) if ratings is not None else None

    name_el = item.find("name[@type='primary']")
    name = name_el.get("value") if name_el is not None else None
    description = clean_description(item.findtext("description"))
    thumb = (item.findtext("thumbnail") or "").strip() or None

    row = {
        "id": int(item.get("id")),
        "type": item.get("type"),
        "name": name,
        "year": _value(item, "yearpublished", int),
        "thumbnail": thumb,
        "description": description,
        "min_players": _value(item, "minplayers", int),
        "max_players": _value(item, "maxplayers", int),
        "best_players": best_player_count(item),
        "playing_time": _value(item, "playingtime", int),
        "min_age": _value(item, "minage", int),
        "rank": rank,
        "bayes_average": stat("bayesaverage"),
        "average": stat("average"),
        "users_rated": stat("usersrated", int),
        "owned": stat("owned", int),
        "weight": stat("averageweight"),
    }
    for field in LINK_FIELDS.values():
        row[field] = []
    for link in item.iterfind("link"):
        field = LINK_FIELDS.get(link.get("type"))
        if field:
            row[field].append(link.get("value"))
    # BGG uses 0 for "unknown" in several numeric fields.
    for key in ("year", "min_players", "max_players", "playing_time", "min_age", "weight"):
        if row[key] == 0:
            row[key] = None
    return row


def parse_files(paths: list[Path]) -> pd.DataFrame:
    rows: dict[int, dict] = {}
    for path in paths:
        root = etree.parse(str(path)).getroot()
        for item in root.iterfind("item"):
            row = parse_item(item)
            rows[row["id"]] = row  # later fetches win
    return pd.DataFrame(list(rows.values()))


def finalize(df: pd.DataFrame) -> pd.DataFrame:
    """Ranked base games only, plus embedding text and quality flags."""
    df = df[(df["type"] == "boardgame") & df["rank"].notna()].drop(columns="type")
    df = df.sort_values("id").reset_index(drop=True)
    df["desc_words"] = df["description"].str.split().str.len().fillna(0).astype(int)
    df["short_desc"] = df["desc_words"] < SHORT_DESC_WORDS
    df["embed_text"] = df["name"].fillna("") + ". " + df["description"]
    for col in ("year", "min_players", "max_players", "best_players", "playing_time",
                "min_age", "rank", "users_rated", "owned"):
        df[col] = df[col].astype("Int64")
    return df


def main() -> None:
    paths = sorted(RAW_DIR.glob("batch_*.xml"))
    if not paths:
        raise SystemExit(f"no cached XML in {RAW_DIR}; run src/fetch.py (or src/make_stub.py) first.")
    df = finalize(parse_files(paths))
    GAMES_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(GAMES_PARQUET, index=False)
    print(f"{len(paths)} files -> {len(df):,} ranked base games "
          f"({df['short_desc'].sum():,} with short descriptions) -> {GAMES_PARQUET}")


if __name__ == "__main__":
    main()
