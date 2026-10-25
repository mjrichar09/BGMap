"""Stage 7 (shared): export a labelled map as compact JSON for the interactive page.

The page (web/<domain>_map.html) is a static file that fetches its data, so
the output folder can be served or deployed as is. Writes into <out>/:

  index.html      the page
  data/manifest.json   title, layouts, tag vocabularies
  data/films.json      per-item fields shared by every layout (columnar arrays)
  data/blurbs.json     overviews and links, loaded after the map is up
  data/<layout>.json   x/y, cluster ids and labels, label positions, and each
                       item's 15 nearest neighbors with similarities (the
                       neighbor list and the graph routes are found on)

    python -m src.export --domain movies --map qwen3__text_plot__inst__nn30_md0.05
    cd data/movies/site && python -m http.server    # then open http://localhost:8000
"""

import argparse
import json
from collections import Counter

import numpy as np
import pandas as pd

from src.common import ROOT, domain_dir

ROUTE_K = 15
POSTER_PREFIX = "https://image.tmdb.org/t/p/w185/"
BLURB_CHARS = 320
CAST = 4  # top-billed actors kept per film for the people lens
CERTS = ["G", "PG", "PG-13", "R", "NC-17", "NR"]


def _clean(values) -> list:
    """JSON-safe list: NaN/NA -> None, numpy scalars -> Python."""
    out = []
    for v in values:
        if v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v)):
            out.append(None)
        elif isinstance(v, np.integer):
            out.append(int(v))
        elif isinstance(v, (np.floating, float)):
            out.append(round(float(v), 3))
        else:
            out.append(v)
    return out


def vocab_indices(series: pd.Series, min_count: int = 1) -> tuple[list[str], list[list[int]]]:
    """Tags as indices into a vocabulary sorted by frequency; tags rarer than min_count are dropped."""
    counts = Counter(t for tags in series for t in tags)
    vocab = [t for t, k in counts.most_common() if k >= min_count]
    index = {t: i for i, t in enumerate(vocab)}
    return vocab, [[index[t] for t in tags if t in index] for tags in series]


def films_payload(df: pd.DataFrame) -> tuple[dict, dict]:
    tags = lambda col: df[col].map(lambda a: list(a) if a is not None else [])
    genre_vocab, genres = vocab_indices(tags("genres"))
    kw_vocab, kws = vocab_indices(tags("keywords").map(lambda a: a[:8]), min_count=2)
    # One people vocabulary for directors and cast, so the lens can search both.
    directors, cast = tags("directors"), tags("cast").map(lambda a: a[:CAST])
    people_vocab, _ = vocab_indices(directors + cast)
    person = {p: i for i, p in enumerate(people_vocab)}
    cert = df["certification"].fillna("").str.strip()
    films = {
        "id": _clean(df["id"]),
        "name": df["name"].fillna("").tolist(),
        "year": _clean(df["year"].astype("Float64")),
        "rating": _clean(df["imdb_rating"]),
        "votes": _clean(df["imdb_votes"].astype("Float64")),
        "runtime": _clean(df["runtime"].where(df["runtime"] > 0)),
        "cert": [CERTS.index(c) if c in CERTS else None for c in cert],
        "imdb": df["imdb_id"].fillna("").str.removeprefix("tt").tolist(),
        # The shared CDN prefix is restored by the page.
        "thumb": df["thumbnail"].fillna("").str.removeprefix(POSTER_PREFIX).tolist(),
        "genre": genres,
        "kw": kws,
        "dir": [[person[p] for p in a] for a in directors],
        "cast": [[person[p] for p in a] for a in cast],
    }
    return films, {"genres": genre_vocab, "keywords": kw_vocab, "people": people_vocab, "certs": CERTS}


def blurbs_payload(df: pd.DataFrame, items: pd.DataFrame) -> dict:
    """Overview without its leading title, trimmed; plus the Wikipedia title for links."""
    text = items.set_index("id").loc[df["id"], ["name", "text", "tagline", "wikipedia_title"]].reset_index()
    overview = [t[len(n) + 2 :] if t.startswith(f"{n}. ") else t for t, n in zip(text["text"].fillna(""), text["name"])]
    trim = lambda s: s if len(s) <= BLURB_CHARS else s[: BLURB_CHARS - 1].rsplit(" ", 1)[0] + "…"
    return {
        "overview": [trim(s) for s in overview],
        "tagline": text["tagline"].fillna("").tolist(),
        "wiki": text["wikipedia_title"].fillna("").tolist(),
    }


def label_positions(xy: np.ndarray, clusters: np.ndarray, labels: pd.Series) -> list[dict]:
    out = []
    for cid in sorted(c for c in np.unique(clusters) if c >= 0):
        mask = clusters == cid
        out.append({"id": int(cid), "label": str(labels[mask].iloc[0]), "size": int(mask.sum()),
                    "x": round(float(np.median(xy[mask, 0])), 3), "y": round(float(np.median(xy[mask, 1])), 3)})
    return out


def nearest_neighbors(vecs: np.ndarray, k: int, chunk: int = 2048) -> tuple[np.ndarray, np.ndarray]:
    """Exact cosine kNN (vectors are unit length), excluding each item itself."""
    nbrs = np.empty((len(vecs), k), dtype=np.int32)
    sims = np.empty((len(vecs), k), dtype=np.float32)
    for start in range(0, len(vecs), chunk):
        s = vecs[start : start + chunk] @ vecs.T
        rows = np.arange(len(s))
        s[rows, start + rows] = -np.inf
        top = np.argpartition(-s, k, axis=1)[:, :k]
        order = np.argsort(-s[rows[:, None], top], axis=1)
        nbrs[start : start + chunk] = top[rows[:, None], order]
        sims[start : start + chunk] = s[rows[:, None], nbrs[start : start + chunk]]
    return nbrs, sims


def layout_payload(df: pd.DataFrame, nbrs: np.ndarray, sims: np.ndarray) -> dict:
    xy = df[["x", "y"]].to_numpy(dtype=float)
    return {
        "x": np.round(xy[:, 0], 3).tolist(),
        "y": np.round(xy[:, 1], 3).tolist(),
        **({f"{c}3": np.round(df[f"{c}3"].to_numpy(dtype=float), 3).tolist() for c in "xyz"} if "z3" in df else {}),
        "cluster": df["cluster_fine"].astype(int).tolist(),
        "coarse": df["cluster_coarse"].astype(int).tolist(),
        "labels": label_positions(xy, df["cluster_fine"].to_numpy(), df["label_fine"]),
        "coarseLabels": label_positions(xy, df["cluster_coarse"].to_numpy(), df["label_coarse"]),
        "neighbors": nbrs.astype(int).ravel().tolist(),
        "sims": np.clip(np.round(sims * 100), 0, 100).astype(int).ravel().tolist(),  # cosine x 100
        "k": int(nbrs.shape[1]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    ap.add_argument("--map", nargs="+", required=True, help="file stems in data/<domain>/maps/; the first opens by default")
    ap.add_argument("--labels", nargs="*", help="display name for each map in the layout picker")
    ap.add_argument("--out", help="default: data/<domain>/site")
    ap.add_argument("--title", default="Movie Map")
    args = ap.parse_args()

    base = domain_dir(args.domain)
    out = base / "site" if args.out is None else ROOT / args.out
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    frames = {m: pd.read_parquet(base / "maps" / f"{m}.parquet") for m in args.map}
    first = frames[args.map[0]]
    layouts = []
    for k, (m, df) in enumerate(frames.items()):
        if df["id"].tolist() != first["id"].tolist():
            raise SystemExit(f"{m}'s rows differ from {args.map[0]}'s; rerun label.py for both.")
        emb = m.rsplit("__nn", 1)[0]  # the embedding the layout was made from
        meta = json.loads((base / "embeddings" / f"{emb}.json").read_text(encoding="utf-8"))
        if meta["ids"] != df["id"].tolist():
            raise SystemExit(f"{emb}'s rows aren't in {m}'s order.")
        vecs = np.load(base / "embeddings" / f"{emb}.npy").astype(np.float32)
        key = f"layout{k}"
        payload = layout_payload(df, *nearest_neighbors(vecs, ROUTE_K))
        (data_dir / f"{key}.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        layouts.append({"key": key, "label": (args.labels or [])[k] if k < len(args.labels or []) else m, "source": m})

    films, vocab = films_payload(first)
    (data_dir / "films.json").write_text(json.dumps(films, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    items = pd.read_parquet(base / "items.parquet", columns=["id", "name", "text", "tagline", "wikipedia_title"])
    blurbs = blurbs_payload(first, items)
    (data_dir / "blurbs.json").write_text(json.dumps(blurbs, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    manifest = {"title": args.title, "count": len(first), "posterPrefix": POSTER_PREFIX, "models": layouts, **vocab}
    (data_dir / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    page = (ROOT / "web" / f"{args.domain}_map.html").read_text(encoding="utf-8")
    (out / "index.html").write_text(page.replace("<title>Movie Map</title>", f"<title>{args.title}</title>", 1), encoding="utf-8")
    sizes = ", ".join(f"{p.name} {p.stat().st_size / 1e6:.1f} MB" for p in sorted(data_dir.glob("*.json")))
    print(f"{len(first):,} items, {len(layouts)} layout(s) -> {out} ({sizes})")


if __name__ == "__main__":
    main()
