"""Film deserts: for a seed film, the empty places between it and other kinds of film.

The same idea as src/gaps.py's unmade movies, but starting from one film instead of a pair of
clusters, and computed ahead of time so the page needs no model or LLM: for each well-known film
(SEED_VOTES+ TMDB votes) and each of the RELATED fine clusters most similar to it, blend the film's
vector with the cluster's centroid (normalized sum, in the full embedding) and ask how close the
nearest real film comes to that blend. Related pairs always have films near their blend, so the
score is how much emptier it is than other pairs equally far apart (a quadratic fit of nearest-film
similarity on seed-to-cluster similarity). Each seed keeps its TOP emptiest blends, with the films
nearest each one ("the closest thing already made"), not counting the seed's near-copies
(sequels, remakes: COPY+ similar to the seed), which sit beside every blend of it. Clusters are eligible on the same rules as
gaps.py (MIN_SIZE+ films, not documentary/concert-heavy), and never the seed's own cluster.

Writes data/<domain>/gaps/deserts.json for export.py:
    {"seed_votes", "fit", "seeds": {film_id: [[cluster, gap, nearest_sim, [near ids], [near sims]], ...]}}

--check embeds the hand-written pitches for some deserts (content/<domain>_deserts.json: seed as
"Name (year)", cluster, title, logline, plot) with the map's model and instruction, keeps those that
land (closer to the blend than to the seed or the cluster; among their 8 nearest films, at least one
closer to the seed than to the cluster's centroid and one the other way; no existing film COPY+ similar) and writes data/<domain>/gaps/desert_pitches.json.

    python -m src.deserts --domain movies
    python -m src.deserts --domain movies --check
"""

import argparse
import json

import numpy as np
import pandas as pd
import torch

from src.common import ROOT, domain_dir
from src.gaps import MIN_SIZE, NONFICTION, centroids, load

SEED_VOTES = 300
RELATED = 40      # candidate clusters per seed: the most similar ones (unrelated blends are empty for a reason)
TOP = 3           # deserts kept per seed
NEAR = 4          # closest existing films kept per desert
BATCH = 64        # seeds per GPU batch
COPY = 0.9        # films this similar to the seed count as its near-copies (sequels, remakes), not neighbours


def check(base, domain):
    from sentence_transformers import SentenceTransformer

    m, v, meta = load(base)
    c, cent = centroids(m, v)
    pitches = json.loads((ROOT / "content" / f"{domain}_deserts.json").read_text(encoding="utf-8"))
    deserts = json.loads((base / "gaps" / "deserts.json").read_text(encoding="utf-8"))["seeds"]
    row = {f"{n} ({int(y)})": j for j, (n, y) in reversed(list(enumerate(zip(m["name"], m["year"]))))}
    model = SentenceTransformer(meta["model"], device="cuda", model_kwargs={"torch_dtype": torch.float16})
    emb = model.encode([f"{p['title']}. {p['plot']}" for p in pitches], normalize_embeddings=True,
                       prompt=f"Instruct: {meta['instruct']}\nQuery: ").astype(np.float32)
    kept = []
    for p, e in zip(pitches, emb):
        s, k = row[p["seed"]], p["cluster"]
        sid = str(int(m["id"].iloc[s]))
        assert any(d[0] == k for d in deserts.get(sid, [])), f"{p['title']}: cluster {k} isn't one of {p['seed']}'s deserts"
        mid = v[s] + cent[k]
        mid /= np.linalg.norm(mid)
        sims = v @ e
        top = np.argsort(-sims)[:8]
        nearer_seed = v[top] @ v[s] > v[top] @ cent[k]   # each neighbour counts for the side it's closer to
        seed_side, cluster_side = int(nearer_seed.sum()), int((~nearer_seed).sum())
        b, ps, pc, near = float(e @ mid), float(e @ v[s]), float(e @ cent[k]), float(sims[top[0]])
        lands = b > max(ps, pc) and seed_side >= 1 and cluster_side >= 1 and near < COPY
        print(f"{'lands' if lands else 'MISSES':6} {p['title']}: blend {b:.3f}, seed {ps:.3f}, cluster {pc:.3f}, nearest {near:.3f} "
              f"({m['name'].iloc[top[0]]}), sides {seed_side}/{cluster_side}")
        if lands:
            kept.append({"seed": int(sid), "cluster": k, "title": p["title"], "logline": p["logline"], "plot": p["plot"]})
    path = base / "gaps" / "desert_pitches.json"
    path.write_text(json.dumps(kept, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {path}: {len(kept)} of {len(pitches)} pitches land")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    ap.add_argument("--check", action="store_true", help="embed and check the hand-written desert pitches")
    args = ap.parse_args()
    base = domain_dir(args.domain)
    if args.check:
        return check(base, args.domain)
    m, v, _ = load(base)
    c, cent = centroids(m, v)

    sizes = np.bincount(c)
    nonfiction = m.groupby("cluster_fine")["genres"].apply(lambda s: np.mean([bool(NONFICTION & set(g)) for g in s])).to_numpy()
    eligible = np.flatnonzero((sizes >= MIN_SIZE) & (nonfiction < 0.3))
    seeds = np.flatnonzero(m["vote_count"].to_numpy() >= SEED_VOTES)
    print(f"{len(seeds):,} seed films, {len(eligible)} eligible clusters")

    dev = "cuda"
    V = torch.tensor(v, device=dev, dtype=torch.float16)
    C = torch.tensor(cent[eligible], device=dev, dtype=torch.float32)
    rows = []  # (seed, cluster, parent_sim, nearest, near ids, near sims)
    for s0 in range(0, len(seeds), BATCH):
        idx = seeds[s0:s0 + BATCH]
        S = torch.tensor(v[idx], device=dev, dtype=torch.float32)
        psim = S @ C.T                                                      # seed-to-cluster similarity
        own = torch.tensor(np.isin(eligible[None, :], c[idx][:, None]), device=dev)
        psim_masked = psim.masked_fill(own, -2)
        top = psim_masked.topk(RELATED, dim=1).indices                      # related clusters per seed
        blends = S[:, None, :] + C[top]                                     # (b, RELATED, d)
        blends = blends / blends.norm(dim=2, keepdim=True)
        sims = (blends.reshape(-1, blends.shape[-1]).half() @ V.T).float()  # (b*RELATED, N)
        seed_rows = torch.tensor(np.repeat(idx, RELATED), device=dev)
        # The seed and its near-copies (sequels, remakes, re-adaptations: COPY+ similar to the seed) don't
        # count as "already made": they sit next to every blend of the seed and would hide the desert.
        copies = (S.half() @ V.T).float() >= COPY                            # (b, N)
        sims = sims.masked_fill(copies.repeat_interleave(RELATED, dim=0), -2)
        sims[torch.arange(sims.shape[0], device=dev), seed_rows] = -2
        near_s, near_i = sims.topk(NEAR, dim=1)
        ps = psim.gather(1, top).reshape(-1).cpu().numpy()
        near_s, near_i = near_s.cpu().numpy(), near_i.cpu().numpy()
        cl = eligible[top.cpu().numpy().reshape(-1)]
        for j in range(len(cl)):
            rows.append((int(seed_rows[j]), int(cl[j]), float(ps[j]), float(near_s[j, 0]), near_i[j], near_s[j]))
        if s0 // BATCH % 20 == 0:
            print(f"  {s0 + len(idx):,} / {len(seeds):,} seeds")

    df = pd.DataFrame({"seed": [r[0] for r in rows], "cluster": [r[1] for r in rows], "parent_sim": [r[2] for r in rows], "nearest": [r[3] for r in rows]})
    fit = np.polyfit(df["parent_sim"], df["nearest"], 2)
    df["gap"] = np.polyval(fit, df["parent_sim"]) - df["nearest"]
    ids = m["id"].to_numpy()
    out = {}
    for seed, g in df.groupby("seed"):
        best = g.nlargest(TOP, "gap")
        out[str(int(ids[seed]))] = [[int(r.cluster), round(float(r.gap), 4), round(float(r.nearest), 3),
                                     [int(ids[i]) for i in rows[r.Index][4]], [round(float(x), 3) for x in rows[r.Index][5]]]
                                    for r in best.itertuples()]
    path = base / "gaps" / "deserts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"seed_votes": SEED_VOTES, "fit": [round(float(x), 5) for x in fit], "seeds": out}), encoding="utf-8")
    print(f"wrote {path}: {len(out):,} seeds × {TOP} deserts; gap median {df['gap'].median():.3f}, p90 {df['gap'].quantile(0.9):.3f}")


if __name__ == "__main__":
    main()
