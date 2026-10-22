"""Evaluation: score each model's map against BGG's own tags and known games.

Tags were kept out of the embedded text, so they work as an independent
answer key. Writes data/eval/report.md (readable) and data/eval/metrics.json.

Checks (see plan.md, Evaluation):
  * Tag agreement   share of each game's 10 nearest neighbors (full embedding
                    space) sharing a mechanic / a category, vs random neighbors
  * Confound scan   how strongly neighbors share publisher, description length
                    and year, next to a real gameplay signal (weight) for scale;
                    clusters dominated by one publisher
  * 2D faithfulness share of full-space neighbors still neighbors in the 2D map
  * Stability       2D neighbor overlap across UMAP seeds (--stability, slow)
  * Spot check      10 nearest neighbors of hand-picked games (data/spot_check.txt)

    python src/evaluate.py                    # every model with a map file
    python src/evaluate.py --models qwen3 bge --stability
"""

from __future__ import annotations

import argparse
import json
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.neighbors import NearestNeighbors

from common import DATA_DIR, EMBED_DIR, map_path, neighbors_path, write_json

K = 10
MAP_WINDOW = 50  # 2D checks: are the 10 true neighbors within the 50 nearest points on the map?
EVAL_DIR = DATA_DIR / "eval"
SPOT_CHECK_FILE = DATA_DIR / "spot_check.txt"
# Twenty well-known games across genres; edit data/spot_check.txt to change.
DEFAULT_SPOT_CHECK = [
    "CATAN", "Ticket to Ride", "Pandemic", "Gloomhaven", "Twilight Struggle", "Codenames", "Wingspan",
    "Terraforming Mars", "Azul", "Brass: Birmingham", "Dominion", "Arkham Horror: The Card Game", "Root",
    "Twilight Imperium: Fourth Edition", "Hive", "1830: Railways & Robber Barons", "Combat Commander: Europe",
    "Dixit", "Spirit Island", "Patchwork",
]
# Placeholder publishers that say nothing about who wrote the description.
GENERIC_PUBLISHERS = {"(Public Domain)", "(Self-Published)", "(Web published)", "(Unknown)"}


def tag_matrix(tags: pd.Series, drop: set[str] = frozenset()) -> sparse.csr_matrix:
    vocab: dict[str, int] = {}
    rows, cols = [], []
    for i, items in enumerate(tags):
        for t in items:
            if t in drop:
                continue
            rows.append(i)
            cols.append(vocab.setdefault(t, len(vocab)))
    return sparse.csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(len(tags), max(len(vocab), 1)))


def shared_tag_rate(m: sparse.csr_matrix, nbrs: np.ndarray, rows: np.ndarray | None = None) -> float:
    """Mean share of neighbors sharing >= 1 tag, over games (optionally a subset) that have any tag."""
    idx = np.arange(len(nbrs)) if rows is None else np.flatnonzero(rows)
    base = m[idx]
    has = np.asarray(base.sum(1)).ravel() > 0
    if not has.any():
        return float("nan")
    hits = np.zeros(len(idx))
    for c in range(nbrs.shape[1]):
        hits += np.asarray(base.multiply(m[nbrs[idx, c]]).sum(1)).ravel() > 0
    return float((hits / nbrs.shape[1])[has].mean())


def random_neighbors(n: int, k: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    r = rng.integers(0, n - 1, size=(n, k))
    return r + (r >= np.arange(n)[:, None])  # skip self


def neighbor_correlation(values: np.ndarray, nbrs: np.ndarray) -> float:
    """Correlation between a game's value and its neighbors' mean (0 = map ignores it)."""
    v = values.astype(float)
    mean_nbr = np.nanmean(v[nbrs], axis=1)
    ok = ~np.isnan(v) & ~np.isnan(mean_nbr)
    return float(np.corrcoef(v[ok], mean_nbr[ok])[0, 1])


def neighbors_2d(xy: np.ndarray, k: int = K) -> np.ndarray:
    _, idx = NearestNeighbors(n_neighbors=k + 1).fit(xy).kneighbors(xy)
    return idx[:, 1:]


def overlap(a: np.ndarray, b: np.ndarray) -> float:
    """Mean share of each row of `a` found in the same row of `b` (b may be wider)."""
    return float(np.mean([len(set(x) & set(y)) / len(x) for x, y in zip(a, b)]))


def dominant_publisher_clusters(df: pd.DataFrame, min_size: int = 15, share: float = 0.4) -> list[dict]:
    out = []
    for cid, g in df[df["cluster"] >= 0].groupby("cluster"):
        if len(g) < min_size:
            continue
        pubs = pd.Series([p for ps in g["publishers"] for p in set(ps) if p not in GENERIC_PUBLISHERS])
        if pubs.empty:
            continue
        top, count = pubs.value_counts().index[0], pubs.value_counts().iloc[0]
        if count / len(g) >= share:
            out.append({"cluster": int(cid), "label": g.get("cluster_label", pd.Series([""])).iloc[0],
                        "size": len(g), "publisher": top, "share": round(count / len(g), 2)})
    return out


def find_games(df: pd.DataFrame, names: list[str]) -> list[tuple[str, int | None]]:
    lower = df["name"].str.lower()
    found = []
    for name in names:
        hits = df.index[lower == name.lower()]
        if len(hits) == 0:
            hits = df.index[lower.str.startswith(name.lower(), na=False)]
        best = df.loc[hits].sort_values("rank").index[0] if len(hits) else None
        found.append((name, best))
    return found


def evaluate_model(model: str, games_tags: dict, stability_seeds: int) -> tuple[dict, pd.DataFrame, np.ndarray]:
    df = pd.read_parquet(map_path(model))
    nbrs = np.load(neighbors_path(model))
    rand = random_neighbors(len(df), nbrs.shape[1])
    m = {"model": model, "games": len(df), "clusters": int(df["cluster"].max() + 1),
         "noise_share": round(float((df["cluster"] < 0).mean()), 3)}

    for field in ("mechanics", "categories"):
        tm = games_tags[field]
        m[f"{field}_agreement"] = round(shared_tag_rate(tm, nbrs), 3)
        m[f"{field}_random"] = round(shared_tag_rate(tm, rand), 3)
    m["mechanics_agreement_short_desc"] = round(
        shared_tag_rate(games_tags["mechanics"], nbrs, df["short_desc"].to_numpy()), 3)

    pub = games_tags["publishers"]
    m["publisher_shared"] = round(shared_tag_rate(pub, nbrs), 3)
    m["publisher_shared_random"] = round(shared_tag_rate(pub, rand), 3)
    m["designer_shared"] = round(shared_tag_rate(games_tags["designers"], nbrs), 3)
    m["designer_shared_random"] = round(shared_tag_rate(games_tags["designers"], rand), 3)
    for col, values in [("weight", df["weight"]), ("year", df["year"]),
                        ("desc_length", np.log1p(df["desc_words"])), ("bayes_rating", df["bayes_average"])]:
        m[f"nbr_corr_{col}"] = round(neighbor_correlation(pd.to_numeric(values).to_numpy(dtype=float), nbrs), 3)

    xy = df[["x", "y"]].to_numpy()
    m["faithfulness_2d"] = round(overlap(nbrs, neighbors_2d(xy, MAP_WINDOW)), 3)
    m["dominant_publisher_clusters"] = dominant_publisher_clusters(df)

    if stability_seeds:
        from project import load_embeddings, umap

        vecs, _ = load_embeddings(model)
        overlaps = []
        for seed in range(1, stability_seeds + 1):
            other = umap(vecs, 2, 30, 0.1, 1000 + seed)
            overlaps.append(overlap(neighbors_2d(xy), neighbors_2d(other, MAP_WINDOW)))
        m["stability_2d_overlap"] = round(float(np.mean(overlaps)), 3)
    return m, df, nbrs


def spot_check_section(model: str, df: pd.DataFrame, nbrs: np.ndarray, names: list[str]) -> list[str]:
    lines = [f"### Spot check: {model}", ""]
    for name, i in find_games(df, names):
        if i is None:
            lines.append(f"- **{name}**: not found")
            continue
        g = df.loc[i]
        mech = set(g["mechanics"])
        nb = []
        for j in nbrs[i]:
            h = df.loc[j]
            mark = "" if mech & set(h["mechanics"]) else " ✗"
            nb.append(f"{h['name']} ({int(h['year']) if pd.notna(h['year']) else '?'}){mark}")
        lines.append(f"- **{g['name']}** [{g.get('cluster_label', '')}]: " + "; ".join(nb))
    lines += ["", "✗ = shares no mechanic with the game.", ""]
    return lines


def model_overlap(models: list[str]) -> dict:
    loaded = {mk: np.load(neighbors_path(mk)) for mk in models}
    out = {}
    for a in models:
        for b in models:
            if a < b and loaded[a].shape == loaded[b].shape:
                out[f"{a}_vs_{b}"] = round(overlap(loaded[a], loaded[b]), 3)
    return out


def write_report(metrics: list[dict], spot: list[str], cross: dict) -> str:
    rows = [
        ("Clusters (fine) / noise share", lambda m: f"{m['clusters']} / {m['noise_share']:.0%}"),
        ("Neighbors sharing a mechanic", lambda m: f"{m['mechanics_agreement']:.1%} (random {m['mechanics_random']:.1%})"),
        ("Neighbors sharing a category", lambda m: f"{m['categories_agreement']:.1%} (random {m['categories_random']:.1%})"),
        ("…same, short descriptions only", lambda m: f"{m.get('mechanics_agreement_short_desc', float('nan')):.1%}"),
        ("Neighbors sharing a designer", lambda m: f"{m['designer_shared']:.1%} (random {m['designer_shared_random']:.1%})"),
        ("Neighbors sharing a publisher ⚠", lambda m: f"{m['publisher_shared']:.1%} (random {m['publisher_shared_random']:.1%})"),
        ("Neighbor correlation: weight", lambda m: f"{m['nbr_corr_weight']:.2f}"),
        ("Neighbor correlation: bayes rating", lambda m: f"{m['nbr_corr_bayes_rating']:.2f}"),
        ("Neighbor correlation: year ⚠", lambda m: f"{m['nbr_corr_year']:.2f}"),
        ("Neighbor correlation: description length ⚠", lambda m: f"{m['nbr_corr_desc_length']:.2f}"),
        (f"2D: true neighbors within {MAP_WINDOW} nearest map points", lambda m: f"{m['faithfulness_2d']:.1%}"),
        (f"2D: map neighbors kept across seeds (within {MAP_WINDOW})", lambda m: f"{m['stability_2d_overlap']:.1%}" if "stability_2d_overlap" in m else "not run"),
    ]
    header = "| Check | " + " | ".join(m["model"] for m in metrics) + " |"
    lines = ["# BGMap evaluation", "", f"Data: `{DATA_DIR}`, {metrics[0]['games']:,} games, k = {K} neighbors "
             "in full embedding space unless noted.", "", header, "|" + "---|" * (len(metrics) + 1)]
    for title, fmt in rows:
        lines.append(f"| {title} | " + " | ".join(fmt(m) for m in metrics) + " |")
    lines += ["", "Higher mechanic/category agreement is better. ⚠ rows are confounds: they should stay well "
              "below the gameplay signals (weight correlation, tag agreement). A correlation near 1 means the map "
              "is sorted by that attribute.", ""]
    if cross:
        lines += ["**Neighbor overlap between models:** " + ", ".join(f"{k} {v:.0%}" for k, v in cross.items()), ""]
    for m in metrics:
        flagged = m["dominant_publisher_clusters"]
        if flagged:
            lines += [f"**{m['model']}: clusters where one publisher has ≥40% of games**", ""]
            lines += [f"- cluster {c['cluster']} \"{c['label']}\" ({c['size']} games): {c['publisher']} {c['share']:.0%}"
                      for c in flagged[:15]] + [""]
    return "\n".join(lines + spot)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="*", help="default: every model with a map file")
    ap.add_argument("--stability", type=int, nargs="?", const=2, default=0, metavar="SEEDS",
                    help="also re-run UMAP with N other seeds (default 2) and compare")
    args = ap.parse_args()

    models = args.models or sorted(p.stem for p in EMBED_DIR.glob("*.npy") if map_path(p.stem).exists())
    if not models:
        raise SystemExit("no models with map files; run project.py first.")
    names = (SPOT_CHECK_FILE.read_text().splitlines() if SPOT_CHECK_FILE.exists() else DEFAULT_SPOT_CHECK)
    names = [n.strip() for n in names if n.strip() and not n.startswith("#")]

    first = pd.read_parquet(map_path(models[0]))
    tags = {"mechanics": tag_matrix(first["mechanics"]), "categories": tag_matrix(first["categories"]),
            "designers": tag_matrix(first["designers"], {"(Uncredited)"}),
            "publishers": tag_matrix(first["publishers"], GENERIC_PUBLISHERS)}

    metrics, spot = [], []
    for model in models:
        print(f"evaluating {model}...")
        m, df, nbrs = evaluate_model(model, tags, args.stability)
        if df["id"].tolist() != first["id"].tolist():
            raise SystemExit(f"{model}'s map rows differ from {models[0]}'s; rerun embed/project.")
        metrics.append(m)
        spot += spot_check_section(model, df, nbrs, names)
        print(json.dumps({k: v for k, v in m.items() if k != "dominant_publisher_clusters"}))

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    report = write_report(metrics, spot, model_overlap(models))
    (EVAL_DIR / "report.md").write_text(report)
    write_json(EVAL_DIR / "metrics.json", metrics)
    print(f"-> {EVAL_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
