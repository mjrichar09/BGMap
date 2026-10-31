"""Compare plot embeddings: what each one predicts and what its neighbourhoods are made of.

For each embedding (data/<domain>/embeddings/<name>.npy, rows in items.parquet order):
    r2_*        5-fold CV R^2 of a ridge regression to rating, box office and brand-free box office
                (targets as in src/fit.py)
    franchise   films in a TMDB collection: share of their K nearest films from the same collection
    genre       mean Jaccard overlap of genre sets with the K nearest films
    era         share of the K nearest films released within 10 years
and the K nearest films of a few well-known ones.

    python -m src.compare --domain movies qwen3__text_plot__inst qwen3__plot_masked__inst ...
"""

import argparse

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, cross_val_predict

from src.common import domain_dir
from src.fit import ALPHAS, SEED, r2, targets
from src.gaps import MAP

K = 15
SHOW = ["GoodFellas", "Avengers: Endgame", "Harry Potter and the Philosopher's Stone", "Toy Story", "The Notebook"]


def neighbours(v, k):
    V = torch.tensor(v, device="cuda", dtype=torch.float16)
    out = []
    for s in range(0, len(v), 2048):
        sims = V[s:s + 2048] @ V.T
        sims[torch.arange(sims.shape[0]), torch.arange(s, s + sims.shape[0])] = -2
        out.append(sims.topk(k, dim=1).indices.cpu().numpy())
    return np.vstack(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    ap.add_argument("names", nargs="+")
    args = ap.parse_args()
    base = domain_dir(args.domain)
    m = pd.read_parquet(base / "maps" / f"{MAP}.parquet")
    items_ids = pd.read_parquet(base / "items.parquet", columns=["id"])["id"].to_numpy()
    assert (m["id"].to_numpy() == items_ids).all()
    tg = targets(m)
    genres = [set(g) for g in m["genres"]]
    coll = m["collection"].fillna("").astype(str).to_numpy()
    year = m["year"].to_numpy(dtype=float)
    cv = KFold(5, shuffle=True, random_state=SEED)
    rows, shows = [], {}
    for name in args.names:
        v = np.load(base / "embeddings" / f"{name}.npy").astype(np.float32)
        row = {"embedding": name}
        for t in ("rating", "box", "box_original"):
            y, ok = tg[t]
            row[f"r2_{t}"] = round(r2(y[ok], cross_val_predict(RidgeCV(alphas=ALPHAS), v[ok], y[ok], cv=cv)), 3)
        nb = neighbours(v, K)
        inc = np.flatnonzero(coll != "")
        row["franchise"] = round(float(np.mean([(coll[nb[i]] == coll[i]).mean() for i in inc])), 3)
        row["genre"] = round(float(np.mean([np.mean([len(genres[i] & genres[j]) / max(1, len(genres[i] | genres[j])) for j in nb[i]]) for i in range(len(m))])), 3)
        row["era"] = round(float(np.mean(np.abs(year[nb] - year[:, None]) <= 10)), 3)
        rows.append(row)
        for s in SHOW:
            i = int(np.flatnonzero(m["name"].to_numpy() == s)[0])
            shows.setdefault(s, {})[name] = ", ".join(m["name"].iloc[j] for j in nb[i][:6])
        print(row, flush=True)
    print(pd.DataFrame(rows).to_string(index=False))
    for s, by in shows.items():
        print(f"\n{s}")
        for name, ns in by.items():
            print(f"  {name}: {ns}")


if __name__ == "__main__":
    main()
