"""Stage 5 (shared): UMAP layouts and HDBSCAN clusters for one embedding.

For each n_neighbors setting, the embedding is reduced to ~10D and clustered
there, so cluster shapes aren't distorted by the squash to 2D. Each
(n_neighbors, min_dist) pair then gets its own 2D display layout.

Clustering: HDBSCAN finds the dense fine clusters. Description spaces are
mostly one continuous mass around dense pockets, so HDBSCAN alone leaves
about half the points as noise. A second pass over the noise with a smaller
minimum size finds the tight groups too small for the first (franchises:
Pokémon, Bond, Saw, Peanuts), keeping only those at least as tight in the full
embedding as the tightest tenth of first-pass clusters; their ids follow the
first pass's, so those keep theirs. The rest are assigned to the cluster most
common among their nearest clustered neighbors (`core` marks points HDBSCAN
placed itself). Broad regions are Ward merges of the fine cluster centres,
so the two levels nest.

Islands: UMAP sets a tight group whose nearest neighbors are all each other
(every Pokémon film's 30 neighbors are other Pokémon films) adrift as a
separate island, at a distance that means nothing. Small islands (up to
--dock films) are moved, shape unchanged, to the nearest free spot beside the
films most similar to them in the full embedding. Larger continents
(Bollywood, sports) stay where UMAP put them.

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
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from sklearn.cluster import HDBSCAN, AgglomerativeClustering
from sklearn.neighbors import KNeighborsClassifier

from src.common import domain_dir

SEED = 42


def reduce(vectors: np.ndarray, dims: int, neighbors: int, min_dist: float) -> np.ndarray:
    return umap.UMAP(
        n_components=dims, n_neighbors=neighbors, min_dist=min_dist, metric="cosine", random_state=SEED
    ).fit_transform(vectors)


def tightness(vectors: np.ndarray, members: np.ndarray) -> float:
    """Mean cosine similarity of members to their normalized centroid."""
    c = vectors[members].mean(axis=0)
    return float((vectors[members] @ (c / np.linalg.norm(c))).mean())


def assign(points: np.ndarray, fine: np.ndarray) -> np.ndarray:
    """Give each noise point (-1) the cluster most common among its nearest clustered neighbors."""
    core = fine >= 0
    out = fine.copy()
    out[~core] = KNeighborsClassifier(n_neighbors=15).fit(points[core], fine[core]).predict(points[~core])
    return out


def cluster(points: np.ndarray, vectors: np.ndarray, min_size: int, small: int, regions: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (fine, coarse, core) labels for every point."""
    fine = HDBSCAN(min_cluster_size=min_size, min_samples=5).fit_predict(points)
    first = fine.max() + 1
    # Regions merge the first-pass clusters only, as filled out by neighbors before the second pass, so
    # they don't move when it's added (and a small group set adrift in the reduced space doesn't make a
    # region of its own). Each second-pass group joins the region of the first-pass cluster it's most
    # similar to in the full embedding.
    filled = assign(points, fine)
    centres = np.vstack([points[filled == c].mean(axis=0) for c in range(first)])
    merge = AgglomerativeClustering(n_clusters=min(regions, len(centres)), linkage="ward").fit_predict(centres)

    noise = np.flatnonzero(fine < 0)
    bar = np.percentile([tightness(vectors, np.flatnonzero(fine == c)) for c in range(first)], 90)
    sub = HDBSCAN(min_cluster_size=small, min_samples=5).fit_predict(points[noise])
    for c in range(sub.max() + 1):
        members = noise[sub == c]
        if tightness(vectors, members) >= bar:
            fine[members] = fine.max() + 1
    core = fine >= 0
    fine = assign(points, fine)

    full = np.vstack([vectors[fine == c].mean(axis=0) for c in range(fine.max() + 1)])
    full /= np.linalg.norm(full, axis=1, keepdims=True)
    merge = np.concatenate([merge, merge[(full[first:] @ full[:first].T).argmax(axis=1)]])
    return fine, merge[fine], core


def dock(xy: np.ndarray, vectors: np.ndarray, max_size: int, reach: float = 10, gap: float = 3) -> list[np.ndarray]:
    """Move small islands of the layout next to their most similar films. Returns the moved groups.

    An island is a group of points no closer than `reach` typical spacings (the median nearest-neighbor
    distance) to the rest. Each one's anchor is where its 30 most similar outside films sit; it's slid
    from the anchor, in whichever direction gets there first, to the nearest spot `gap` spacings clear.
    """
    tree = cKDTree(xy)
    spacing = np.median(tree.query(xy, k=2)[0][:, 1])
    _, comp = connected_components(tree.sparse_distance_matrix(tree, spacing * reach, output_type="coo_matrix"), directed=False)
    sizes = np.bincount(comp)
    islands = [np.flatnonzero(comp == c) for c in np.argsort(-sizes)[1:] if sizes[c] <= max_size]
    dims = xy.shape[1]
    if dims == 2:
        a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
        dirs = np.stack([np.cos(a), np.sin(a)], 1)
    else:  # evenly spread over the sphere
        k = np.arange(96) + 0.5
        phi, theta = np.arccos(1 - 2 * k / 96), np.pi * (1 + 5**0.5) * k
        dirs = np.stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)], 1)
    for members in islands:
        rest = np.setdiff1d(np.arange(len(xy)), members)
        centre = vectors[members].mean(axis=0)
        similar = rest[np.argsort(-(vectors[rest] @ centre))[:30]]
        anchor = np.median(xy[similar], axis=0)
        shape = xy[members] - xy[members].mean(axis=0)
        others = cKDTree(xy[rest])
        best = None
        for d in dirs:
            for t in np.arange(0, 2000) * spacing:
                if best is not None and t >= best[0]:
                    break
                if others.query(shape + anchor + t * d)[0].min() >= gap * spacing:
                    best = (t, anchor + t * d)
                    break
        xy[members] = shape + best[1]
    return islands


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--embedding", required=True, help="file stem in data/<domain>/embeddings/, e.g. qwen3__text_plot")
    ap.add_argument("--neighbors", type=int, nargs="+", default=[30])
    ap.add_argument("--min-dist", type=float, nargs="+", default=[0.1])
    ap.add_argument("--cluster-dims", type=int, default=10)
    ap.add_argument("--fine", type=int, default=40, help="HDBSCAN min_cluster_size for sub-clusters")
    ap.add_argument("--small", type=int, default=12, help="HDBSCAN min_cluster_size for the second pass over noise")
    ap.add_argument("--dock", type=int, default=150, help="largest island (in films) to move next to its neighbors")
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
        fine, coarse, core = cluster(high, vectors, args.fine, args.small, args.regions)
        print(
            f"nn={nn}: {fine.max() + 1} fine clusters ({core.mean():.0%} placed by HDBSCAN, rest by neighbors), "
            f"{coarse.max() + 1} regions in {time.time() - t:.0f}s"
        )
        for md in args.min_dist:
            t = time.time()
            xy = reduce(vectors, 2, nn, md)
            docked = dock(xy, vectors, args.dock)
            name = f"{args.embedding}__nn{nn}_md{md:g}"
            layout = pd.DataFrame(
                {"id": ids, "x": xy[:, 0], "y": xy[:, 1], "cluster_fine": fine, "cluster_coarse": coarse, "core": core}
            )
            if args.three_d:
                xyz = reduce(vectors, 3, nn, md)
                docked += dock(xyz, vectors, args.dock)
                layout["x3"], layout["y3"], layout["z3"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
            layout.to_parquet(out_dir / f"{name}.parquet", index=False)
            print(f"  wrote {name} in {time.time() - t:.0f}s ({len(docked)} islands docked)")


if __name__ == "__main__":
    main()
