"""Stage 3 (movies): turn cached TMDB JSON into data/movies/items.parquet.

Every domain writes the same core columns so the shared stages (embed,
project, label) don't need to know which domain they're running on:

    id, name, year, text, word_count, short_text, thumbnail

followed by domain-specific overlay columns. As with board games, tags
(genres, keywords) stay out of `text` so they can serve as an answer key.

    python -m src.movies.parse
"""

import json

import pandas as pd

from src.common import clean_text, domain_dir, word_count
from src.movies.imdb import FILENAME as IMDB_FILENAME
from src.movies.tmdb import IMAGE_BASE

# TMDB overviews are short (often 40-80 words), so the board-game threshold of
# ~30 words would mute too much of the map.
SHORT_WORDS = 15


def names(items: list[dict], key: str = "name") -> list[str]:
    return [i[key] for i in items or []]


def certification(release_dates: list[dict]) -> str | None:
    """US rating, preferring the theatrical release (type 3)."""
    ranked = sorted(release_dates or [], key=lambda r: r["type"] != 3)
    return ranked[0]["certification"] if ranked else None


def parse_movie(d: dict, wiki: dict | None) -> dict:
    # Fall back to the original-language overview when there's no usable
    # English one; the embedding model is multilingual.
    overview, text_lang = clean_text(d.get("overview")), "en"
    if word_count(overview) < SHORT_WORDS:
        alt = max((clean_text(t["overview"]) for t in d.get("translations", [])), key=word_count, default="")
        if word_count(alt) > word_count(overview):
            overview, text_lang = alt, d.get("original_language")
    if not overview:
        text_lang = None
    wc = word_count(overview)
    text = f"{d['title']}. {overview}" if overview else d["title"]

    plot = (wiki or {}).get("plot")
    # Some Wikipedia plot sections are a single line; only prefer the plot
    # when it says more than the overview.
    use_plot = plot is not None and word_count(plot) > wc
    crew = d.get("credits", {}).get("crew", [])
    release = d.get("release_date") or ""
    return {
        "id": d["id"],
        "name": d["title"],
        "year": int(release[:4]) if release[:4].isdigit() else None,
        "text": text,
        "word_count": wc,
        "short_text": wc < SHORT_WORDS,
        "thumbnail": f"{IMAGE_BASE}w185{d['poster_path']}" if d.get("poster_path") else None,
        # Alternative embedding text: Wikipedia plot, falling back to `text`
        "text_lang": text_lang,
        "plot": plot,
        "plot_word_count": word_count(plot) if plot else 0,
        "text_plot": f"{d['title']}. {plot}" if use_plot else text,
        "text_plot_source": "wikipedia" if use_plot else "tmdb",
        "wikipedia_title": (wiki or {}).get("title"),
        # Identity
        "original_title": d.get("original_title"),
        "original_language": d.get("original_language"),
        "release_date": release or None,
        "tagline": clean_text(d.get("tagline")) or None,
        "imdb_id": d.get("imdb_id"),
        "wikidata_id": (d.get("external_ids") or {}).get("wikidata_id"),
        "certification": certification(d.get("release_dates")),
        # Tags (answer key, not embedded)
        "genres": names(d.get("genres")),
        "keywords": names(d.get("keywords", {}).get("keywords")),
        "collection": (d.get("belongs_to_collection") or {}).get("name"),
        # People and production
        "directors": [c["name"] for c in crew if c["job"] == "Director"],
        "writers": [c["name"] for c in crew if c["job"] in ("Screenplay", "Writer", "Novel")],
        "cast": names(d.get("credits", {}).get("cast"))[:5],
        "companies": names(d.get("production_companies")),
        "countries": names(d.get("production_countries"), "iso_3166_1"),
        # Stats
        "runtime": d.get("runtime") or None,
        "vote_average": d.get("vote_average"),
        "vote_count": d.get("vote_count"),
        "popularity": d.get("popularity"),
        "budget": d.get("budget") or None,
        "revenue": d.get("revenue") or None,
    }


def add_imdb_ratings(items: pd.DataFrame, path) -> pd.DataFrame:
    """Join IMDb's average rating and vote count, if the dataset has been downloaded."""
    if not path.exists():
        print(f"  no {path.name}; run src.movies.imdb to add IMDb ratings")
        return items.assign(imdb_rating=None, imdb_votes=None)
    ratings = pd.read_csv(path, sep="\t", na_values="\\N").rename(
        columns={"tconst": "imdb_id", "averageRating": "imdb_rating", "numVotes": "imdb_votes"}
    )
    items = items.merge(ratings, on="imdb_id", how="left")
    items["imdb_votes"] = items["imdb_votes"].astype("Int64")
    return items


def main() -> None:
    base = domain_dir("movies")
    raw_dir, wiki_dir = base / "raw", base / "wiki"
    ids = pd.read_csv(base / "ids.csv")["id"].tolist()

    rows, absent = [], 0
    for movie_id in ids:
        path = raw_dir / f"{movie_id}.json"
        if not path.exists():
            absent += 1
            continue
        wiki_path = wiki_dir / f"{movie_id}.json"
        wiki = json.loads(wiki_path.read_text(encoding="utf-8")) if wiki_path.exists() else None
        rows.append(parse_movie(json.loads(path.read_text(encoding="utf-8")), wiki))

    items = pd.DataFrame(rows)
    items = add_imdb_ratings(items, base / IMDB_FILENAME)
    out = base / "items.parquet"
    items.to_parquet(out, index=False)
    print(f"Wrote {len(items):,} movies to {out} ({absent:,} IDs have no cached response)")
    print(f"  {items['short_text'].sum():,} have short or missing overviews")
    print(f"  {(items['text_lang'].notna() & (items['text_lang'] != 'en')).sum():,} use an original-language overview")
    print(f"  {items['plot'].notna().sum():,} have a Wikipedia plot")
    print(f"  {items['imdb_rating'].notna().sum():,} have an IMDb rating")


if __name__ == "__main__":
    main()
