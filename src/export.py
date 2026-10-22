"""Export labeled maps as compact JSON for the interactive page (site/index.html).

Writes into <out>/data/:
  manifest.json   title, models, tag vocabularies
  games.json      per-game fields shared by every model (columnar arrays)
  <model>.json    x/y, cluster ids and labels, label positions, and each game's
                  15 nearest neighbors with similarities (the page's neighbor
                  list and the graph its routes are found on)

    python src/export.py --models qwen3 bge --out site
    cd site && python -m http.server    # then open http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from common import EMBED_DIR, ROOT, WEB_DIR, embedding_paths, map_path
from project import nearest_neighbors

ROUTE_K = 15

THUMB_PREFIX = "https://cf.geekdo-images.com/"
MODEL_LABELS = {"qwen3": "Qwen3 0.6B", "nomic": "Nomic v1.5", "bge": "BGE base (512 tok)", "tfidf": "TF-IDF baseline"}


def _clean(values) -> list:
    """JSON-safe list: NaN/NA -> None, numpy scalars -> Python."""
    out = []
    for v in values:
        if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
            out.append(None)
        elif isinstance(v, (np.integer,)):
            out.append(int(v))
        elif isinstance(v, (np.floating, float)):
            out.append(round(float(v), 3))
        else:
            out.append(v)
    return out


def vocab_indices(series: pd.Series) -> tuple[list[str], list[list[int]]]:
    counts = Counter(t for tags in series for t in tags)
    vocab = [t for t, _ in counts.most_common()]
    index = {t: i for i, t in enumerate(vocab)}
    return vocab, [[index[t] for t in tags] for tags in series]


def games_payload(df: pd.DataFrame) -> tuple[dict, dict]:
    mech_vocab, mech = vocab_indices(df["mechanics"])
    cat_vocab, cat = vocab_indices(df["categories"])
    des_vocab, des = vocab_indices(df["designers"].map(lambda d: [x for x in d if x != "(Uncredited)"]))
    games = {
        "id": _clean(df["id"]),
        "name": df["name"].fillna("").tolist(),
        "year": _clean(df["year"].astype("Float64")),
        "weight": _clean(df["weight"]),
        "rating": _clean(df["bayes_average"]),
        "avg": _clean(df["average"]),
        "users": _clean(df["users_rated"].astype("Float64")),
        "rank": _clean(df["rank"].astype("Float64")),
        "minp": _clean(df["min_players"].astype("Float64")),
        "maxp": _clean(df["max_players"].astype("Float64")),
        "bestp": _clean(df["best_players"].astype("Float64")),
        "time": _clean(df["playing_time"].astype("Float64")),
        # The shared CDN prefix is restored by the page (saves ~1 MB).
        "thumb": df["thumbnail"].fillna("").str.removeprefix(THUMB_PREFIX).tolist(),
        "short": df["short_desc"].astype(bool).tolist(),
        "mech": mech,
        "cat": cat,
        "des": des,
    }
    return games, {"mechanics": mech_vocab, "categories": cat_vocab, "designers": des_vocab}


def label_positions(xy: np.ndarray, clusters: np.ndarray, labels: pd.Series) -> list[dict]:
    out = []
    for cid in sorted(c for c in np.unique(clusters) if c >= 0):
        mask = clusters == cid
        out.append({"id": int(cid), "label": str(labels[mask].iloc[0]), "size": int(mask.sum()),
                    "x": round(float(np.median(xy[mask, 0])), 3), "y": round(float(np.median(xy[mask, 1])), 3)})
    return out


def neighbors_with_similarity(model: str, k: int = ROUTE_K) -> tuple[np.ndarray, np.ndarray]:
    vecs = np.load(embedding_paths(model)[0]).astype(np.float32)
    vecs /= np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)
    nbrs = nearest_neighbors(vecs, k)
    sims = np.einsum("ij,ikj->ik", vecs, vecs[nbrs])
    return nbrs, sims


def model_payload(df: pd.DataFrame, nbrs: np.ndarray, sims: np.ndarray) -> dict:
    xy = df[["x", "y"]].to_numpy(dtype=float)
    return {
        "x": np.round(xy[:, 0], 3).tolist(),
        "y": np.round(xy[:, 1], 3).tolist(),
        "cluster": df["cluster"].astype(int).tolist(),
        "coarse": df["cluster_coarse"].astype(int).tolist(),
        "labels": label_positions(xy, df["cluster"].to_numpy(), df["cluster_label"]),
        "coarseLabels": label_positions(xy, df["cluster_coarse"].to_numpy(), df["cluster_coarse_label"]),
        "neighbors": nbrs.astype(int).ravel().tolist(),
        "sims": np.clip(np.round(sims * 100), 0, 100).astype(int).ravel().tolist(),  # cosine x 100
        "k": int(nbrs.shape[1]),
    }


def write_page(out: Path, title: str, fragment_only: bool = False) -> None:
    """web/map.html is a body fragment (the Artifact viewer adds its own shell); wrap it for static hosting."""
    fragment = (WEB_DIR / "map.html").read_text().replace("<title>BGMap</title>", f"<title>{title}</title>", 1)
    if fragment_only:
        (out / "index.html").write_text(fragment)
        return
    shell = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
             "</head>\n<body>\n")
    (out / "index.html").write_text(shell + fragment + "\n</body>\n</html>\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="*", help="default: every model with a labeled map")
    ap.add_argument("--out", type=Path, default=ROOT / "site")
    ap.add_argument("--title", default="BGMap")
    ap.add_argument("--fragment", action="store_true", help="write the page without its HTML shell (for an Artifact)")
    ap.add_argument("--note", default="", help="one line shown under the title, e.g. the data source")
    args = ap.parse_args()

    models = args.models or sorted(p.stem for p in EMBED_DIR.glob("*.npy") if map_path(p.stem).exists())
    frames = {m: pd.read_parquet(map_path(m)) for m in models}
    base = frames[models[0]]
    for m, df in frames.items():
        if "cluster_label" not in df:
            raise SystemExit(f"{m} has no cluster labels; run label.py --model {m}.")
        if df["id"].tolist() != base["id"].tolist():
            raise SystemExit(f"{m}'s rows differ from {models[0]}'s; rerun embed/project for both.")

    data_dir = args.out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    games, vocab = games_payload(base)
    (data_dir / "games.json").write_text(json.dumps(games, separators=(",", ":")))
    for m, df in frames.items():
        payload = model_payload(df, *neighbors_with_similarity(m))
        (data_dir / f"{m}.json").write_text(json.dumps(payload, separators=(",", ":")))
    manifest = {"title": args.title, "note": args.note, "count": len(base), "thumbPrefix": THUMB_PREFIX,
                "models": [{"key": m, "label": MODEL_LABELS.get(m, m)} for m in models], **vocab}
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    write_page(args.out, args.title, args.fragment)
    sizes = ", ".join(f"{p.name} {p.stat().st_size / 1e6:.1f} MB" for p in sorted(data_dir.glob("*.json")))
    print(f"{len(base):,} games, models {models} -> {data_dir} ({sizes})")


if __name__ == "__main__":
    main()
