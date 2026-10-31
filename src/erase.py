"""Erase an attribute from an embedding: iterative null-space projection (INLP).

Animation is a medium, not a kind of story, but animated films still find each other in the plot embedding
(talking animals, toys, anime tropes, a younger register). Each round fits a linear classifier for the
attribute, removes its direction from every vector, and refits on what's left, until a film's nearest
neighbours share the attribute little more than chance, no classifier can find it (CHANCE), or ROUNDS.
For animation the linear part goes in ~13 rounds (neighbours animated 49% -> 39%, base rate 8%); what's
left is stories mostly told in animation (talking animals, toys, magical creatures), which is story. Everything orthogonal to the
removed directions is untouched.

Writes data/<domain>/embeddings/<embedding>__no<attr>.npy and .json (the source's metadata plus the
erasure record), rows in the same order.

    python -m src.erase --domain movies --embedding qwen3__plot_masked_meta__inst --genre Animation
"""

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.common import domain_dir
from src.compare import neighbours

ROUNDS = 40
TARGET = 2.0   # stop once animated films' neighbours are at most this many times the base rate animated,
CHANCE = 0.55  # or once a linear classifier can barely tell (balanced accuracy at or below this): nothing linear is left
K = 15


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    ap.add_argument("--embedding", required=True)
    ap.add_argument("--genre", default="Animation")
    args = ap.parse_args()
    base = domain_dir(args.domain)
    meta = json.loads((base / "embeddings" / f"{args.embedding}.json").read_text(encoding="utf-8"))
    items = pd.read_parquet(base / "items.parquet", columns=["id", "genres"]).set_index("id").loc[meta["ids"]]
    y = items["genres"].map(lambda g: g is not None and args.genre in g).to_numpy()
    v = np.load(base / "embeddings" / f"{args.embedding}.npy").astype(np.float64)
    rate = lambda x: float(y[neighbours((x / np.linalg.norm(x, axis=1, keepdims=True)).astype(np.float32), K)[y]].mean())
    base_rate, history, removed = y.mean(), [], []
    print(f"{args.genre}: {y.sum():,} films ({base_rate * 100:.1f}%); neighbours sharing it {rate(v) * 100:.0f}%")
    for r in range(ROUNDS):
        clf = LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0).fit(v, y)
        acc = clf.score(v, y)
        norm = np.linalg.norm(clf.coef_[0])
        if acc <= CHANCE or not np.isfinite(norm) or norm < 1e-9:
            print(f"  stop: classifier accuracy {acc:.3f}, no linear direction left")
            break
        w = clf.coef_[0] / norm
        v = v - np.outer(v @ w, w)
        removed.append(w)
        share = rate(v)
        history.append({"round": r + 1, "train_acc": round(acc, 3), "neighbour_share": round(share, 3)})
        print(f"  round {r + 1}: classifier accuracy {acc:.3f}, neighbours sharing it {share * 100:.0f}%")
        if share <= TARGET * base_rate:
            break
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    name = f"{args.embedding}__no{args.genre.lower()}"
    np.save(base / "embeddings" / f"{name}.npy", v.astype(np.float16))
    np.save(base / "embeddings" / f"{name}__directions.npy", np.array(removed, dtype=np.float32))
    meta = {**meta, "erased": {"genre": args.genre, "method": "INLP", "directions": len(removed), "file": f"{name}__directions.npy", "history": history}}
    (base / "embeddings" / f"{name}.json").write_text(json.dumps(meta), encoding="utf-8")
    print(f"wrote {name}: {len(removed)} directions removed")


if __name__ == "__main__":
    main()
