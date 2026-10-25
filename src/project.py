"""Stage 5 (shared): UMAP layouts and HDBSCAN clusters for one embedding.

For each n_neighbors setting, the embedding is reduced to ~10D and clustered
there, so cluster shapes aren't distorted by the squash to 2D. Each
(n_neighbors, min_dist) pair then gets its own 2D display layout.

Clustering: HDBSCAN finds the dense fine clusters. Description spaces are
mostly one continuous mass around dense pockets, so HDBSCAN alone leaves
well over half the points as noise; those are assigned to the cluster most
common among their nearest clustered neighbors (`core` marks points HDBSCAN
placed itself). Broad regions are Ward merges of the fine cluster centres,
so the two levels nest.

Writes data/<domain>/layouts/<embedding>__nn<N>_md<D>.parquet with
id, x, y, cluster_fine, cluster_coarse, core, plus x3, y3, z3 with --three-d
(a separate 3D UMAP on the same settings, for the page's 3D view).

    python -m src.project --domain movies --embedding qwen3__text_plot
    python -m src.project --domain movies --embedding qwen3__text_plot --neighbors 15 30 50 --min-dist 0.05 0.1 0.2
    python -m src.project --domain movies --embedding qwen3__text_plot__inst --min-dist 0.05 --three-d
"""

import argparse
import json
import time

import numpy as np
import pandas as pd
import umap
from sklearn.cluster import HDBSCAN, AgglomerativeClustering
from sklearn.neighbors import KNeighborsClassifier

from src.common import domain_dir

SEED = 42


def reduce(vectors: np.ndarray, dims: int, neighbors: int, min_dist: float) -> np.ndarray:
    return umap.UMAP(
        n_components=dims, n_neighbors=neighbors, min_dist=min_dist, metric="cosine", random_state=SEED
    ).fit_transform(vectors)


def cluster(points: np.ndarray, min_size: int, regions: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (fine, coarse, core) labels for every point."""
    fine = HDBSCAN(min_cluster_size=min_size, min_samples=5).fit_predict(points)
    core = fine >= 0
    knn = KNeighborsClassifier(n_neighbors=15).fit(points[core], fine[core])
    fine[~core] = knn.predict(points[~core])

    centres = np.vstack([points[fine == c].mean(axis=0) for c in range(fine.max() + 1)])
    merge = AgglomerativeClustering(n_clusters=min(regions, len(centres)), linkage="ward").fit_predict(centres)
    return fine, merge[fine], core


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--embedding", required=True, help="file stem in data/<domain>/embeddings/, e.g. qwen3__text_plot")
    ap.add_argument("--neighbors", type=int, nargs="+", default=[30])
    ap.add_argument("--min-dist", type=float, nargs="+", default=[0.1])
    ap.add_argument("--cluster-dims", type=int, default=10)
    ap.add_argument("--fine", type=int, default=40, help="HDBSCAN min_cluster_size for sub-clusters")
    ap.add_argument("--regions", type=int, default=20, help="number of broad regions")
    ap.add_argument("--three-d", action="store_true", help="also compute a 3D layout (x3, y3, z3) for each setting")
    args = ap.parse_args()

    base = domain_dir(args.domain)
    emb_dir = base / "embeddings"
    vectors = np.load(emb_dir / f"{args.embedding}.npy").astype(np.float32)
    ids = json.loads((emb_dir / f"{args.embedding}.json").read_text(encoding="utf-8"))["ids"]
    out_dir = base / "layouts"
    out_dir.mkdir(exist_ok=True)

    for nn in args.neighbors:
        t = time.time()
        high = reduce(vectors, args.cluster_dims, nn, 0.0)
        fine, coarse, core = cluster(high, args.fine, args.regions)
        print(
            f"nn={nn}: {fine.max() + 1} fine clusters ({core.mean():.0%} placed by HDBSCAN, rest by neighbors), "
            f"{coarse.max() + 1} regions in {time.time() - t:.0f}s"
        )
        for md in args.min_dist:
            t = time.time()
            xy = reduce(vectors, 2, nn, md)
            name = f"{args.embedding}__nn{nn}_md{md:g}"
            layout = pd.DataFrame(
                {"id": ids, "x": xy[:, 0], "y": xy[:, 1], "cluster_fine": fine, "cluster_coarse": coarse, "core": core}
            )
            if args.three_d:
                xyz = reduce(vectors, 3, nn, md)
                layout["x3"], layout["y3"], layout["z3"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
            layout.to_parquet(out_dir / f"{name}.parquet", index=False)
            print(f"  wrote {name} in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
