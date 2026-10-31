"""Find "unmade movies": empty places between two kinds of film, measured in the full embedding.

The 2D/3D map can't show gaps: UMAP spreads crowded areas out and pulls sparse
ones together, so empty-looking patches on the map aren't empty in the model's
space. Here every pair of fine clusters is blended (the normalized mean of
their centroids) and we ask how close the nearest real film is to the blend.
Closely related pairs always have films near their blend, so the score is how
much emptier the blend is than other pairs equally far apart (a quadratic fit
of nearest-film similarity on parent similarity), plus a bonus for parents that
are well rated and well watched. Documentary- and concert-heavy clusters are
left out: their texts read differently from fiction plots, which makes their
blends look emptier than they are.

Two steps, with pitches written in between:

  find   ranks the gaps and writes data/<domain>/gaps/candidates.json
  check  embeds a pitch for each chosen gap (content/<domain>_unmade.json, one
         "Title. Plot..." per gap, written like the films' own texts, naming the
         gap by its two parent clusters, which needn't still be in the top list)
         with the same model and instruction as the map, and verifies it lands in the gap:
         closer to the blend than any existing film is, and not just a copy of
         one parent. Writes data/<domain>/gaps/unmade.json for export.py.

    python -m src.gaps --domain movies find
    python -m src.gaps --domain movies check
"""

import argparse
import json

import numpy as np
import pandas as pd

from src.common import ROOT, domain_dir

EMBEDDING = "qwen3__plot_masked_meta__inst__noanimation"  # masked plot + keywords + tagline, animation erased (src.mask, src.erase)
MAP = "qwen3__plot_masked_meta__inst__noanimation__nn30_md0.05"
NONFICTION = {"Documentary", "Music", "TV Movie"}
MIN_SIZE = 60  # films a parent cluster needs
TOP = 20


def load(base):
    m = pd.read_parquet(base / "maps" / f"{MAP}.parquet")
    v = np.load(base / "embeddings" / f"{EMBEDDING}.npy").astype(np.float32)
    meta = json.loads((base / "embeddings" / f"{EMBEDDING}.json").read_text(encoding="utf-8"))
    assert meta["ids"] == m["id"].tolist(), "embedding rows aren't in the map's order"
    return m, v, meta


def centroids(m, v):
    c = m["cluster_fine"].to_numpy()
    cent = np.vstack([v[c == k].mean(0) for k in range(c.max() + 1)])
    return c, cent / np.linalg.norm(cent, axis=1, keepdims=True)


def blend(cent, a, b):
    mid = cent[a] + cent[b]
    return mid / np.linalg.norm(mid)


def rank(m, v, cent):
    """Score every eligible pair of fine clusters. Returns (pairs table, cluster stats, similarity of every film to each blend)."""
    stats = pd.DataFrame({
        "label": m.groupby("cluster_fine")["label_fine"].first(),
        "examples": m.groupby("cluster_fine")["examples_fine"].first(),
        "n": m.groupby("cluster_fine").size(),
        "rating": m.groupby("cluster_fine")["vote_average"].mean(),
        "votes": m.groupby("cluster_fine")["vote_count"].median(),
        "nonfiction": m.groupby("cluster_fine")["genres"].apply(lambda s: np.mean([bool(NONFICTION & set(g)) for g in s])),
    })
    ok = stats.index[(stats["n"] >= MIN_SIZE) & (stats["nonfiction"] < 0.3)].to_numpy()
    pairs = [(a, b) for i, a in enumerate(ok) for b in ok[i + 1:]]
    mids = np.vstack([blend(cent, a, b) for a, b in pairs])
    sims = mids @ v.T
    df = pd.DataFrame({"a": [p[0] for p in pairs], "b": [p[1] for p in pairs]})
    df["parent_sim"] = [float(cent[a] @ cent[b]) for a, b in pairs]
    df["nearest"] = sims.max(1)
    fit = np.polyfit(df["parent_sim"], df["nearest"], 2)
    df["gap"] = np.polyval(fit, df["parent_sim"]) - df["nearest"]
    # Appeal: the parents' mean rating and median votes, as z-scores across clusters.
    z = lambda s: (s - s.mean()) / s.std()
    appeal = (z(stats["rating"]) + z(np.log1p(stats["votes"]))) / 2
    df["appeal"] = [(appeal[a] + appeal[b]) / 2 for a, b in pairs]
    df["score"] = z(df["gap"]) + 0.5 * df["appeal"]
    return df, stats, sims


def describe(m, stats, r, s):
    """One gap: its parents, how empty it is, and the films closest to its blend (s: every film's similarity to it)."""
    closest = np.argsort(-s)[:5]
    return {
        "parents": [int(r.a), int(r.b)],
        "labels": [stats.loc[r.a, "label"], stats.loc[r.b, "label"]],
        "examples": [stats.loc[r.a, "examples"], stats.loc[r.b, "examples"]],
        "parent_sim": round(r.parent_sim, 3), "nearest": round(float(r.nearest), 3),
        "gap": round(float(r.gap), 3), "score": round(float(r.score), 2),
        "closest": [{"id": int(m["id"].iloc[j]), "name": m["name"].iloc[j], "year": int(m["year"].iloc[j]),
                     "sim": round(float(s[j]), 3)} for j in closest],
    }


def find(base, out_dir):
    m, v, _ = load(base)
    c, cent = centroids(m, v)
    df, stats, sims = rank(m, v, cent)
    # Only blends of related kinds of film are candidates: unrelated pairs are empty for a reason.
    df = df[df["parent_sim"] >= df["parent_sim"].median()].sort_values("score", ascending=False)

    picked, uses = [], {}
    for r in df.itertuples():
        if uses.get(r.a, 0) >= 2 or uses.get(r.b, 0) >= 2:
            continue
        uses[r.a] = uses.get(r.a, 0) + 1
        uses[r.b] = uses.get(r.b, 0) + 1
        picked.append(describe(m, stats, r, sims[r.Index]))
        if len(picked) == TOP:
            break
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "candidates.json").write_text(json.dumps(picked, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, g in enumerate(picked):
        print(f"{k:2} {g['labels'][0]}  x  {g['labels'][1]}  (gap {g['gap']:+.3f}, score {g['score']})")
        print(f"     parents: [{g['examples'][0]}]  x  [{g['examples'][1]}]")
        print(f"     closest existing: " + "; ".join(f"{c['name']} ({c['year']}) {c['sim']}" for c in g["closest"][:3]))
    print(f"wrote {out_dir / 'candidates.json'}")


def check(base, out_dir, domain):
    from src.pitch import embed_texts  # masks and erases like the films' text, if the embedding did

    m, v, meta = load(base)
    c, cent = centroids(m, v)
    df, stats, sims = rank(m, v, cent)
    pitches = json.loads((ROOT / "content" / f"{domain}_unmade.json").read_text(encoding="utf-8"))
    emb = embed_texts(base, meta, [f"{p['title']}. {p['plot']}" for p in pitches])

    unmade = []
    for p, e in zip(pitches, emb):
        a, b = sorted(p["parents"])
        row = df[(df["a"] == a) & (df["b"] == b)]
        assert len(row), f"{p['title']}: clusters {a} and {b} aren't an eligible pair (too small, or nonfiction)"
        g = describe(m, stats, next(row.itertuples()), sims[row.index[0]])
        mid = blend(cent, a, b)
        s = v @ e
        top = np.argsort(-s)[:8]
        from_a, from_b = int((c[top] == a).sum()), int((c[top] == b).sum())
        result = {
            "title": p["title"], "logline": p["logline"], "plot": p["plot"],
            "parents": [a, b], "labels": g["labels"], "examples": g["examples"],
            "blend_sim": round(float(e @ mid), 3),           # how close the pitch is to the blend point
            "parent_sims": [round(float(e @ cent[a]), 3), round(float(e @ cent[b]), 3)],
            "nearest_film": round(float(s[top[0]]), 3),      # how close the nearest real film is
            "closest_to_blend": g["closest"],                # what exists nearest the gap today
            "pitch_neighbors": [{"id": int(m["id"].iloc[j]), "name": m["name"].iloc[j], "year": int(m["year"].iloc[j]),
                                 "sim": round(float(s[j]), 3)} for j in top[:5]],
            "neighbors_from_parents": [from_a, from_b],
            "gap": g["gap"],
        }
        # It lands in the gap if it's closer to the blend than to either parent, its nearest films include
        # both kinds, and nothing already made is a near-copy.
        result["lands"] = bool(result["blend_sim"] > max(result["parent_sims"]) and min(from_a, from_b) >= 1
                               and result["nearest_film"] < 0.9)
        unmade.append(result)
        flag = "lands" if result["lands"] else "MISSES"
        print(f"{flag:6} {p['title']}: blend {result['blend_sim']}, parents {result['parent_sims']}, nearest film "
              f"{result['nearest_film']} ({result['pitch_neighbors'][0]['name']}), neighbors from parents {from_a}/{from_b}")
    (out_dir / "unmade.json").write_text(json.dumps(unmade, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out_dir / 'unmade.json'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    ap.add_argument("step", choices=["find", "check"])
    args = ap.parse_args()
    base = domain_dir(args.domain)
    out_dir = base / "gaps"
    find(base, out_dir) if args.step == "find" else check(base, out_dir, args.domain)


if __name__ == "__main__":
    main()
