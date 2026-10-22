"""Stage 5: UMAP to 2D for display, UMAP to ~10D + HDBSCAN for clusters.

Writes data/map_<model>.parquet (id, x, y, cluster ids, overlay fields) and
data/neighbors_<model>.npy (10 nearest neighbors per game in full embedding
space, as row indices into games.parquet).

    python src/project.py --model qwen3
    python src/project.py --model qwen3 --sweep   # also save a grid of 2D layouts
"""

from __future__ import annotations

import argparse
import itertools

import numpy as np
import pandas as pd
from sklearn.cluster import HDBSCAN

from common import GAMES_PARQUET, LAYOUT_DIR, embedding_paths, map_path, neighbors_path, read_json

OVERLAY_COLS = [
    "id", "name", "year", "thumbnail", "min_players", "max_players", "best_players", "playing_time",
    "min_age", "rank", "bayes_average", "average", "users_rated", "owned", "weight",
    "categories", "mechanics", "designers", "publishers", "desc_words", "short_desc",
]


def load_embeddings(model_key: str) -> tuple[np.ndarray, pd.DataFrame]:
    npy, meta_path = embedding_paths(model_key)
    vecs = np.load(npy)
    meta = read_json(meta_path)
    games = pd.read_parquet(GAMES_PARQUET)
    if meta["ids"] != games["id"].astype(int).tolist():
        raise SystemExit(f"{npy.name} rows don't match games.parquet; rerun embed.py --model {model_key}.")
    return vecs, games


def umap(vecs: np.ndarray, dims: int, n_neighbors: int, min_dist: float, seed: int) -> np.ndarray:
    import warnings

    import umap as umap_lib

    warnings.filterwarnings("ignore", message="n_jobs value", category=UserWarning)

    n_neighbors = min(n_neighbors, len(vecs) - 1)
    reducer = umap_lib.UMAP(n_components=dims, n_neighbors=n_neighbors, min_dist=min_dist,
                            metric="cosine", random_state=seed)
    return reducer.fit_transform(vecs).astype(np.float32)


def cluster(coords: np.ndarray, min_cluster_size: int) -> np.ndarray:
    min_cluster_size = max(2, min(min_cluster_size, len(coords) // 4))
    return HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min(10, min_cluster_size), copy=True).fit_predict(coords)


def nearest_neighbors(vecs: np.ndarray, k: int = 10, chunk: int = 2048) -> np.ndarray:
    """Top-k by cosine similarity (vectors are L2-normalized), excluding self."""
    vecs = vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)
    k = min(k, len(vecs) - 1)
    out = np.empty((len(vecs), k), dtype=np.int32)
    for start in range(0, len(vecs), chunk):
        sims = vecs[start : start + chunk] @ vecs.T
        rows = np.arange(sims.shape[0])
        sims[rows, rows + start] = -np.inf
        top = np.argpartition(-sims, k, axis=1)[:, :k]
        order = np.argsort(-sims[rows[:, None], top], axis=1)
        out[start : start + chunk] = top[rows[:, None], order]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen3")
    ap.add_argument("--n-neighbors", type=int, default=30)
    ap.add_argument("--min-dist", type=float, default=0.1)
    ap.add_argument("--cluster-dims", type=int, default=10)
    ap.add_argument("--min-cluster-size", type=int, default=30, help="fine clusters")
    ap.add_argument("--coarse-cluster-size", type=int, default=150, help="broad regions")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sweep", action="store_true", help="also save 2D layouts for a small parameter grid")
    args = ap.parse_args()

    vecs, games = load_embeddings(args.model)
    print(f"{len(vecs):,} games, dim {vecs.shape[1]}")

    xy = umap(vecs, 2, args.n_neighbors, args.min_dist, args.seed)
    xyz = umap(vecs, 3, args.n_neighbors, args.min_dist, args.seed)  # for the page's 3D view
    high = umap(vecs, args.cluster_dims, args.n_neighbors, 0.0, args.seed)
    fine = cluster(high, args.min_cluster_size)
    coarse = cluster(high, args.coarse_cluster_size)
    print(f"fine: {fine.max() + 1} clusters, {np.mean(fine < 0):.0%} noise; "
          f"coarse: {coarse.max() + 1} clusters, {np.mean(coarse < 0):.0%} noise")

    out = games[[c for c in OVERLAY_COLS if c in games]].copy()
    out["x"], out["y"] = xy[:, 0], xy[:, 1]
    out["x3"], out["y3"], out["z3"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    out["cluster"], out["cluster_coarse"] = fine, coarse
    out.to_parquet(map_path(args.model), index=False)
    np.save(neighbors_path(args.model), nearest_neighbors(vecs))
    print(f"-> {map_path(args.model)}, {neighbors_path(args.model)}")

    if args.sweep:
        LAYOUT_DIR.mkdir(parents=True, exist_ok=True)
        for nn, md in itertools.product([15, 30, 50], [0.05, 0.1, 0.2]):
            coords = umap(vecs, 2, nn, md, args.seed)
            path = LAYOUT_DIR / f"{args.model}_nn{nn}_md{md}.parquet"
            pd.DataFrame({"id": games["id"], "x": coords[:, 0], "y": coords[:, 1]}).to_parquet(path, index=False)
            print(f"  layout -> {path.name}")


if __name__ == "__main__":
    main()
