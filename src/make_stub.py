"""Generate synthetic BGG-format XML so stages 3-6 can run before API approval.

Games are invented, drawn from a handful of genres with their own vocabulary,
mechanics and categories, so a working pipeline should recover the genres
as clusters. Output mirrors a real fetch: data/stub/raw/batch_*.xml.

    python src/make_stub.py               # writes to data/stub
    BGMAP_DATA=data/stub python src/parse.py
"""

from __future__ import annotations

import argparse
import html
import random
import zlib
from pathlib import Path

from common import ROOT

GENRES = {
    "euro": {
        "words": ["farm", "harvest", "workers", "resources", "village", "trade goods", "buildings", "grain",
                  "livestock", "craftsmen", "market", "guild", "victory points", "efficient engine"],
        "mechanics": ["Worker Placement", "Resource Management", "End Game Bonuses", "Variable Set-up"],
        "categories": ["Economic", "Farming", "Medieval"],
    },
    "wargame": {
        "words": ["divisions", "front line", "supply", "artillery", "campaign", "hex map", "battle",
                  "commanders", "invasion", "historical scenario", "combat results", "armored units"],
        "mechanics": ["Hexagon Grid", "Dice Rolling", "Simulation", "Campaign / Battle Card Driven"],
        "categories": ["Wargame", "World War II", "Modern Warfare"],
    },
    "party": {
        "words": ["teams", "guess", "laugh", "friends", "word", "clue", "timer", "drawing", "bluff",
                  "silly", "quick rounds", "large groups", "shout"],
        "mechanics": ["Team-Based Game", "Communication Limits", "Voting", "Real-Time"],
        "categories": ["Party Game", "Word Game", "Humor"],
    },
    "dungeon": {
        "words": ["heroes", "dungeon", "monsters", "loot", "quest", "dragon", "spells", "campaign book",
                  "level up", "dark lord", "miniatures", "cooperative adventure", "boss fight"],
        "mechanics": ["Cooperative Game", "Dice Rolling", "Grid Movement", "Campaign / Battle Card Driven"],
        "categories": ["Fantasy", "Adventure", "Fighting", "Miniatures"],
    },
    "space": {
        "words": ["galaxy", "starships", "planets", "alien species", "technology", "empire", "fleet",
                  "colonize", "wormholes", "research", "interstellar", "sectors"],
        "mechanics": ["Area Majority / Influence", "Tech Trees / Tech Tracks", "Variable Player Powers"],
        "categories": ["Science Fiction", "Space Exploration", "Civilization"],
    },
    "abstract": {
        "words": ["board", "pieces", "pattern", "opponent", "perfect information", "tiles", "line",
                  "capture", "elegant rules", "geometry", "two players", "strategy depth"],
        "mechanics": ["Pattern Building", "Tile Placement", "Grid Movement"],
        "categories": ["Abstract Strategy"],
    },
    "trains": {
        "words": ["railroad", "track", "stations", "shares", "locomotives", "routes", "stock market",
                  "dividends", "companies", "network", "cities", "freight"],
        "mechanics": ["Network and Route Building", "Stock Holding", "Auction/Bidding"],
        "categories": ["Trains", "Economic", "Transportation"],
    },
    "horror": {
        "words": ["investigators", "cult", "madness", "eldritch", "mansion", "clues", "sanity", "haunted",
                  "ritual", "ancient one", "mystery", "1920s"],
        "mechanics": ["Cooperative Game", "Dice Rolling", "Scenario / Mission / Campaign Game"],
        "categories": ["Horror", "Exploration", "Novel-based"],
    },
}

FILLER = ["Players take turns", "Each round", "During the game", "Over several rounds", "At the end",
          "In this game", "Throughout play"]
NAME_A = ["Iron", "Golden", "Lost", "Twilight", "Crimson", "Silent", "Grand", "Hidden", "Ancient", "Wild"]
NAME_B = ["Empire", "Harvest", "Frontier", "Crown", "Realm", "Express", "Tides", "Legacy", "Gambit", "Hollow"]
PUBLISHERS = ["Stub Games", "Placeholder Press", "Mock Meeple Co.", "Example Editions"]
DESIGNERS = ["A. Designer", "B. Maker", "C. Inventor", "D. Creator", "E. Author"]


def description(genre: dict, rng: random.Random, n_sentences: int) -> str:
    sentences = []
    for _ in range(n_sentences):
        words = rng.sample(genre["words"], 3)
        sentences.append(f"{rng.choice(FILLER)}, players deal with {words[0]}, {words[1]} and {words[2]}.")
    # Real descriptions arrive double-escaped with BBCode and &#10; line breaks.
    text = "&#10;&#10;".join(" ".join(sentences[k : k + 3]) for k in range(0, len(sentences), 3))
    return "[b]" + text + "[/b] &amp;mdash; see [url=https://example.com]the rules[/url]."


def item_xml(gid: int, name: str, genre_key: str, rng: random.Random) -> str:
    genre = GENRES[genre_key]
    n_sent = rng.choice([1, 2, 6, 9, 12])  # some short descriptions on purpose
    lo = rng.choice([1, 2, 2, 3])
    hi = lo + rng.choice([0, 1, 2, 3])
    rank = gid - 99
    links = []
    for kind, pool, k in [("boardgamecategory", genre["categories"], 2),
                          ("boardgamemechanic", genre["mechanics"], 3),
                          ("boardgamedesigner", DESIGNERS, 1),
                          ("boardgamepublisher", PUBLISHERS, 1)]:
        for value in rng.sample(pool, min(k, len(pool))):
            links.append(f'<link type="{kind}" id="{zlib.crc32(value.encode()) % 10000}" value="{html.escape(value)}"/>')
    polls = "".join(
        f'<results numplayers="{p}"><result value="Best" numvotes="{rng.randint(0, 50)}"/>'
        f'<result value="Recommended" numvotes="{rng.randint(0, 50)}"/>'
        f'<result value="Not Recommended" numvotes="{rng.randint(0, 50)}"/></results>'
        for p in range(lo, hi + 1)
    ) + f'<results numplayers="{hi}+"><result value="Best" numvotes="99"/></results>'
    return f"""<item type="boardgame" id="{gid}">
<thumbnail>https://example.com/thumb/{gid}.jpg</thumbnail>
<name type="primary" sortindex="1" value="{html.escape(name)}"/>
<description>{html.escape(description(genre, rng, n_sent), quote=False)}</description>
<yearpublished value="{rng.randint(1980, 2025)}"/>
<minplayers value="{lo}"/><maxplayers value="{hi}"/>
<poll name="suggested_numplayers" title="User Suggested Number of Players" totalvotes="100">{polls}</poll>
<playingtime value="{rng.choice([20, 45, 60, 90, 120, 240])}"/><minage value="{rng.choice([8, 10, 12, 14])}"/>
{''.join(links)}
<statistics page="1"><ratings>
<usersrated value="{rng.randint(30, 50000)}"/><average value="{rng.uniform(5, 9):.3f}"/>
<bayesaverage value="{rng.uniform(5.5, 8.5):.3f}"/>
<ranks><rank type="subtype" id="1" name="boardgame" friendlyname="Board Game Rank" value="{rank}" bayesaverage="7"/></ranks>
<owned value="{rng.randint(50, 80000)}"/><averageweight value="{rng.uniform(1, 4.5):.4f}"/>
</ratings></statistics>
</item>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "stub")
    ap.add_argument("--per-genre", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    items = []
    gid = 100
    for genre_key in GENRES:
        for k in range(args.per_genre):
            name = f"{rng.choice(NAME_A)} {rng.choice(NAME_B)} {genre_key.title()} {k + 1}"
            items.append(item_xml(gid, name, genre_key, rng))
            gid += 1
    # One expansion, which parse.py must drop.
    items.append(f'<item type="boardgameexpansion" id="{gid}"><name type="primary" value="Stub Expansion"/>'
                 '<description>Adds more.</description></item>')
    rng.shuffle(items)

    raw = args.out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for old in raw.glob("batch_*.xml"):
        old.unlink()
    for n, start in enumerate(range(0, len(items), 20)):
        body = "\n".join(items[start : start + 20])
        (raw / f"batch_{n:05d}.xml").write_text(
            f'<?xml version="1.0" encoding="utf-8"?>\n<items termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">\n{body}\n</items>\n'
        )
    print(f"{len(items)} stub items -> {raw}")


if __name__ == "__main__":
    main()
