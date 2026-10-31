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

  assets/         logos for the credits

Besides each UMAP map, an "Axes (PCA)" layout places films by the embedding's
three main directions, with each axis's two ends described by the genres that
dominate them. PCA keeps almost no local neighbours (the UMAP map does that)
but its axes have meanings. Unmade movies from src.gaps (if checked) ship with
a position on every layout.

Ratings: the site is public, so it uses TMDB's own rating and vote count and
leaves IMDb data out of every file (IMDb ids, which come from TMDB, stay for
links). IMDb's datasets are for personal, non-commercial use and may not be
republished; --private builds a personal copy with IMDb's ratings into
data/<domain>/site-private, which must never be deployed. The page's
cutoffs (ticket/reel icons, gems, best-rated weighting) are defined on the IMDb
scale and carried to TMDB's by percentile over the same films.

    python -m src.export --domain movies --map qwen3__text_plot__inst__nn30_md0.05
    python -m src.export --domain movies --map qwen3__text_plot__inst__nn30_md0.05 --private
    cd data/movies/site && python -m http.server    # then open http://localhost:8000
"""

import argparse
import json
import shutil
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from src.common import ROOT, domain_dir
from src.gaps import blend, centroids

ROUTE_K = 15
POSTER_PREFIX = "https://image.tmdb.org/t/p/w185/"
BLURB_CHARS = 320
CAST = 4  # top-billed actors kept per film for the people lens
CERTS = ["G", "PG", "PG-13", "R", "NC-17", "NR"]
# TMDB's original_language codes ("cn" is TMDB's code for Cantonese); others show as the code.
LANG_NAMES = {
    "en": "English", "fr": "French", "it": "Italian", "ja": "Japanese", "es": "Spanish", "de": "German",
    "hi": "Hindi", "ko": "Korean", "zh": "Mandarin", "ru": "Russian", "cn": "Cantonese", "pt": "Portuguese",
    "sv": "Swedish", "da": "Danish", "ta": "Tamil", "te": "Telugu", "ml": "Malayalam", "tr": "Turkish",
    "pl": "Polish", "nl": "Dutch", "no": "Norwegian", "fi": "Finnish", "th": "Thai", "id": "Indonesian",
    "fa": "Persian", "ar": "Arabic", "el": "Greek", "hu": "Hungarian", "cs": "Czech", "tl": "Tagalog",
}
# Page cutoffs on IMDb's scale. votes: point size starts at `base`; `rated` is enough votes to trust a
# rating; tickets from `known`, reels from `reel`; gold stars need `award` votes and an `award` rating;
# gems are rated `gem`+ by `rated`–`gemMax` people; best-rated lists pull ratings toward rating `prior`
# with weight `prior` votes; sparse loved areas average `gap`+; movie night offers the `night` minimums.
IMDB_SCALE = {
    "votes": {"base": 100, "rated": 1000, "known": 10000, "award": 25000, "gemMax": 25000, "prior": 25000, "reel": 150000},
    "rating": {"prior": 6.5, "gap": 7.3, "gem": 7.5, "award": 8.0, "night": [6.5, 7.0, 7.5]},
}
RATINGS = {  # source name, rating column, votes column
    "IMDb": ("imdb_rating", "imdb_votes"),
    "TMDB": ("vote_average", "vote_count"),
}


def round_sig(v: float, digits: int = 2) -> int:
    return int(float(f"{v:.{digits}g}"))


def carry_scale(df: pd.DataFrame) -> dict:
    """IMDB_SCALE moved to TMDB's scale: each cutoff goes to the TMDB value at the same percentile."""
    both = df.dropna(subset=["imdb_rating", "imdb_votes"])
    iv, tv = both["imdb_votes"].astype(float), both["vote_count"].astype(float)
    ir, tr = both["imdb_rating"].astype(float), both["vote_average"].astype(float)
    votes = lambda t: max(1, round_sig(tv.quantile((iv < t).mean())))
    rating = lambda t: round(float(tr.quantile((ir < t).mean())), 1)
    return {
        "votes": {k: votes(t) for k, t in IMDB_SCALE["votes"].items()},
        "rating": {k: [rating(x) for x in t] if isinstance(t, list) else rating(t) for k, t in IMDB_SCALE["rating"].items()},
    }


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


def films_payload(df: pd.DataFrame, source: str) -> tuple[dict, dict]:
    rating_col, votes_col = RATINGS[source]
    tags = lambda col: df[col].map(lambda a: list(a) if a is not None else [])
    genre_vocab, genres = vocab_indices(tags("genres"))
    kw_vocab, kws = vocab_indices(tags("keywords").map(lambda a: a[:8]), min_count=2)
    # One people vocabulary for directors and cast, so the lens can search both.
    directors, cast = tags("directors"), tags("cast").map(lambda a: a[:CAST])
    people_vocab, _ = vocab_indices(directors + cast)
    person = {p: i for i, p in enumerate(people_vocab)}
    cert = df["certification"].fillna("").str.strip()
    lang_vocab = df["original_language"].fillna("").value_counts().index.tolist()
    lang_index = {c: i for i, c in enumerate(lang_vocab)}
    films = {
        "id": _clean(df["id"]),
        "name": df["name"].fillna("").tolist(),
        "year": _clean(df["year"].astype("Float64")),
        "rating": _clean(df[rating_col]),
        "votes": _clean(df[votes_col].astype("Float64")),
        "runtime": _clean(df["runtime"].where(df["runtime"] > 0)),
        "cert": [CERTS.index(c) if c in CERTS else None for c in cert],
        # Money in $M, not inflation-adjusted; TMDB stores unknowns as 0, so tiny values count as unknown.
        "revenue": _clean((df["revenue"].where(df["revenue"] > 1e5) / 1e6).round(2)),
        "budget": _clean((df["budget"].where(df["budget"] > 1e5) / 1e6).round(2)),
        "lang": [lang_index[c] for c in df["original_language"].fillna("")],
        "imdb": df["imdb_id"].fillna("").str.removeprefix("tt").tolist(),
        # The shared CDN prefix is restored by the page.
        "thumb": df["thumbnail"].fillna("").str.removeprefix(POSTER_PREFIX).tolist(),
        "genre": genres,
        "kw": kws,
        "dir": [[person[p] for p in a] for a in directors],
        "cast": [[person[p] for p in a] for a in cast],
    }
    languages = [LANG_NAMES.get(c, c.upper() or "Unknown") for c in lang_vocab]
    return films, {"genres": genre_vocab, "keywords": kw_vocab, "people": people_vocab, "certs": CERTS, "languages": languages}


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


PEOPLE_MIN = 5  # films on the map before a director or actor gets a stats card


def people_stats(df: pd.DataFrame, vecs: np.ndarray, sims: np.ndarray, people_vocab: list[str], rating_col: str) -> dict:
    """A stats card for every director or actor with PEOPLE_MIN+ films on the map (directed, or in the top CAST billed).

    Originality is the site's own (1 - mean similarity to a film's ROUTE_K nearest plots, full embedding); range is the
    mean plot similarity between the person's films (lower = more varied). Money is TMDB's, in $M, not inflation-adjusted,
    over films with known figures. Percentiles compare directors with directors and actors with actors (a person counts
    as a director if they directed at least as many of their films as they acted in).
    """
    person = {p: i for i, p in enumerate(people_vocab)}
    films_of: dict[int, set] = {}
    directed: dict[int, int] = {}
    for row, (ds, cs) in enumerate(zip(df["directors"], df["cast"])):
        ds = list(ds) if ds is not None else []
        cs = list(cs)[:CAST] if cs is not None else []
        for p in ds:
            films_of.setdefault(person[p], set()).add(row); directed[person[p]] = directed.get(person[p], 0) + 1
        for p in cs:
            films_of.setdefault(person[p], set()).add(row)
    orig = 1 - sims.mean(axis=1)
    rating, votes = df[rating_col].to_numpy(float), df["vote_count"].to_numpy(float)
    rev = df["revenue"].where(df["revenue"] > 1e5).to_numpy(float) / 1e6
    bud = df["budget"].where(df["budget"] > 1e5).to_numpy(float) / 1e6
    year, genres = df["year"].to_numpy(float), df["genres"]
    cards = {}
    for p, rows in films_of.items():
        if len(rows) < PEOPLE_MIN:
            continue
        ix = np.array(sorted(rows))
        s = vecs[ix] @ vecs[ix].T
        r, b = rev[ix], bud[ix]
        both = ~np.isnan(r) & ~np.isnan(b)
        top_genres = Counter(g for gs in genres.iloc[ix] if gs is not None for g in gs).most_common(3)
        cards[p] = {
            "role": "director" if directed.get(p, 0) >= len(ix) - directed.get(p, 0) else "actor",
            "films": int(len(ix)), "directed": int(directed.get(p, 0)),
            "years": [int(np.nanmin(year[ix])), int(np.nanmax(year[ix]))],
            "rating": round(float(np.nanmean(rating[ix])), 2),
            "boxOffice": round(float(np.nanmedian(r)), 1) if (~np.isnan(r)).any() else None,
            "boxOfficeTotal": round(float(np.nansum(r))) if (~np.isnan(r)).any() else None,
            "budget": round(float(np.nanmedian(b)), 1) if (~np.isnan(b)).any() else None,
            "roi": round(float(np.median(r[both] / b[both])), 2) if both.sum() >= 3 else None,
            "orig": round(float(orig[ix].mean()), 4),
            "range": round(float((s.sum() - len(ix)) / (len(ix) ** 2 - len(ix))), 3),
            "genres": [g for g, _ in top_genres],
            "best": int(ix[np.argmax(votes[ix])]),
        }
    # Percentiles within role: the share of peers this person beats (for range, a wider range = lower similarity beats).
    for role in ("director", "actor"):
        group = [p for p, c in cards.items() if c["role"] == role]
        for key, higher in (("rating", True), ("boxOffice", True), ("roi", True), ("orig", True), ("range", False)):
            vals = np.array([cards[p][key] for p in group if cards[p][key] is not None], float)
            for p in group:
                v = cards[p][key]
                if v is not None and len(vals):
                    beats = (vals < v).mean() if higher else (vals > v).mean()
                    cards[p].setdefault("pct", {})[key] = int(round(100 * beats))
        for p in group:
            cards[p]["peers"] = len(group)
    return cards


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


def axis_poles(df: pd.DataFrame, scores: np.ndarray, extreme: int = 1500) -> dict:
    """Describe each end of an axis by the genres most over-represented there and its best-known films."""
    base = df["genres"].explode().value_counts(normalize=True)
    order = np.argsort(scores)
    def pole(idx):
        share = df["genres"].iloc[idx].explode().value_counts(normalize=True)
        lift = (share / base).where(share >= 0.15).dropna().sort_values(ascending=False)
        known = df.iloc[idx[:300]].sort_values("vote_count", ascending=False)
        return {"genres": lift.index[:2].tolist(), "examples": known["name"].head(3).tolist()}
    return {"low": pole(order[:extreme]), "high": pole(order[::-1][:extreme])}


def pca_layout(df: pd.DataFrame, vecs: np.ndarray) -> tuple[pd.DataFrame, PCA, float, list[dict]]:
    """The embedding's three main directions as a layout, scaled to the UMAP map's spread."""
    pca = PCA(n_components=3, random_state=0).fit(vecs)
    z = pca.transform(vecs)
    scale = float(df[["x", "y"]].to_numpy().std() / z[:, :2].std())
    z *= scale
    out = df[["cluster_fine", "cluster_coarse", "label_fine", "label_coarse"]].copy()
    out["x"], out["y"] = z[:, 0], z[:, 1]
    out["x3"], out["y3"], out["z3"] = z[:, 0], z[:, 1], z[:, 2]
    axes = [{"variance": round(float(pca.explained_variance_ratio_[k]), 3), **axis_poles(df, z[:, k])} for k in range(3)]
    return out, pca, scale, axes


def unmade_positions(df: pd.DataFrame, unmade: list[dict], ids: dict, place) -> list[list[float]]:
    """Where each unmade movie sits on a layout: `place(u)` if given, else the mean of the films nearest its blend."""
    cols = ["x", "y"] + (["x3", "y3", "z3"] if "z3" in df else [])
    out = []
    for u in unmade:
        p = place(u) if place else df.iloc[[ids[c["id"]] for c in u["closest_to_blend"]]][cols].mean().to_numpy()
        out.append([round(float(t), 3) for t in p])
    return out


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
    ap.add_argument("--out", help="default: data/<domain>/site, or data/<domain>/site-private with --private")
    ap.add_argument("--title", default="Massive Movie Map")
    ap.add_argument("--private", action="store_true", help="IMDb ratings instead of TMDB's, for personal use only (never deploy)")
    ap.add_argument("--no-pca", action="store_true", help="skip the Axes (PCA) layout")
    args = ap.parse_args()

    base = domain_dir(args.domain)
    out = base / ("site-private" if args.private else "site") if args.out is None else ROOT / args.out
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    frames = {m: pd.read_parquet(base / "maps" / f"{m}.parquet") for m in args.map}
    first = frames[args.map[0]]
    ids = {i: k for k, i in enumerate(first["id"])}
    unmade_path = base / "gaps" / "unmade.json"
    unmade = json.loads(unmade_path.read_text(encoding="utf-8")) if unmade_path.exists() else []
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
        nbrs = nearest_neighbors(vecs, ROUTE_K)
        if k == 0:
            first_vecs, first_sims = vecs, nbrs[1]  # for the people stats
        payload = layout_payload(df, *nbrs)
        payload["unmade"] = unmade_positions(df, unmade, ids, None)
        (data_dir / f"{key}.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        layouts.append({"key": key, "label": (args.labels or [])[k] if k < len(args.labels or []) else m, "source": m})
        if k == 0 and not args.no_pca:
            pdf, pca, pca_scale, axes = pca_layout(df, vecs)
            cl, cent = centroids(df, vecs)
            payload = layout_payload(pdf, *nbrs)
            payload["kind"], payload["axes"] = "pca", axes
            payload["unmade"] = unmade_positions(pdf, unmade, ids, lambda u: np.r_[
                pca.transform(blend(cent, *u["parents"])[None])[0, :2], pca.transform(blend(cent, *u["parents"])[None])[0]] * pca_scale)
            (data_dir / "axes.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            pca_entry = {"key": "axes", "label": "Axes (PCA)", "source": f"PCA of {emb}"}
    if not args.no_pca:
        layouts.append(pca_entry)

    source = "IMDb" if args.private else "TMDB"
    films, vocab = films_payload(first, source)
    people = people_stats(first, first_vecs, first_sims, vocab["people"], RATINGS[source][0])
    (data_dir / "people.json").write_text(json.dumps({str(k): v for k, v in people.items()}, separators=(",", ":")), encoding="utf-8")
    (data_dir / "films.json").write_text(json.dumps(films, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    items = pd.read_parquet(base / "items.parquet", columns=["id", "name", "text", "tagline", "wikipedia_title"])
    blurbs = blurbs_payload(first, items)
    (data_dir / "blurbs.json").write_text(json.dumps(blurbs, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    deserts_path = base / "gaps" / "deserts.json"
    if deserts_path.exists():  # film deserts (src/deserts.py), loaded by the page only when the tool opens
        d = json.loads(deserts_path.read_text(encoding="utf-8"))
        seeds = {str(ids[int(fid)]): [[cl, gap, near, [ids[i] for i in nids], sims] for cl, gap, near, nids, sims in rows]
                 for fid, rows in d["seeds"].items()}
        used = sorted({r[0] for rows in seeds.values() for r in rows})
        names = first.groupby("cluster_fine")[["label_fine", "examples_fine"]].first()
        clusters = {str(c): {"label": names.loc[c, "label_fine"], "examples": names.loc[c, "examples_fine"]} for c in used}
        pitches = {}  # hand-written pitches that landed in their desert (src/deserts.py --check): seed row -> cluster -> pitch
        pitch_path = base / "gaps" / "desert_pitches.json"
        for p in json.loads(pitch_path.read_text(encoding="utf-8")) if pitch_path.exists() else []:
            pitches.setdefault(str(ids[p["seed"]]), {})[str(p["cluster"])] = {k: p[k] for k in ("title", "logline", "plot")}
        hoods = {str(ids[int(fid)]): [ids[i] for i in h if i in ids] for fid, h in d.get("hoods", {}).items()}  # "films like ..."
        (data_dir / "deserts.json").write_text(json.dumps({"seedVotes": d["seed_votes"], "seeds": seeds, "clusters": clusters, "pitches": pitches, "hoods": hoods},
                                                          separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    scale = IMDB_SCALE if args.private else carry_scale(first)
    for u in unmade:  # film ids -> row indices, which is what the page works in
        for key in ("closest_to_blend", "pitch_neighbors"):
            u[key] = [{"i": ids[c["id"]], "sim": c["sim"]} for c in u[key]]
    manifest = {"title": args.title, "count": len(first), "posterPrefix": POSTER_PREFIX, "models": layouts,
                "ratings": {"source": source, **scale}, "unmade": [u for u in unmade if u["lands"]], **vocab}
    (data_dir / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    page = (ROOT / "web" / f"{args.domain}_map.html").read_text(encoding="utf-8")
    (out / "index.html").write_text(page.replace("<title>Massive Movie Map</title>", f"<title>{args.title}</title>", 1), encoding="utf-8")
    shutil.copytree(ROOT / "web" / "assets", out / "assets", dirs_exist_ok=True)
    shutil.copytree(ROOT / "web" / "root", out, dirs_exist_ok=True)  # robots.txt, sitemap.xml
    sizes = ", ".join(f"{p.name} {p.stat().st_size / 1e6:.1f} MB" for p in sorted(data_dir.glob("*.json")))
    print(f"{len(first):,} items, {len(layouts)} layout(s), {source} ratings -> {out} ({sizes})")
    print(f"rating cutoffs: {json.dumps(scale)}")


if __name__ == "__main__":
    main()
