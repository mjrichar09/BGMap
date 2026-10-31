"""Fit outcomes to the plot embedding: how much of a film's rating or box office does its story predict,
and what would a story built to maximize them look like?

Targets (TMDB data only):
    rating   TMDB average, films with RATED_VOTES+ votes
    box      log10 box office relative to the median film of its release year (so 1 = ten times a typical
             film that year; a rough stand-in for inflation and market size), films with MIN_REVENUE+ revenue
    roi      log10(box office / budget), films with MIN_REVENUE+ revenue and budget
    *_original  the same, fitted only on films that aren't part of a franchise (TMDB collection): the
             embedding carries names, and a famous one ("Avengers", "Hogwarts") predicts box office far
             better than any story does, so these answer "what kind of story", with brand names out

For each target, a ridge regression (alpha by RidgeCV) on three feature sets, scored by 5-fold
cross-validated R^2: the plot embedding alone, genres alone (one-hot), and both. The embedding-only model
is then refit on everything and kept: it scores any plot, including ones that don't exist yet.

Writes data/<domain>/fit/: models.joblib (target -> fitted ridge), fit.json (scores, the films and
clusters the models rate highest and lowest), preds.parquet (out-of-fold predictions per film).

    python -m src.fit --domain movies
    python -m src.fit --domain movies --score content/movies_optimal.json   # embed and score pitches
"""

import argparse
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, cross_val_predict

from src.common import ROOT, domain_dir
from src.gaps import load

RATED_VOTES = 100
MIN_REVENUE = 1e5
YEARS = (1970, 2025)
ALPHAS = np.logspace(-1, 3, 13)
SEED = 0


def targets(m):
    """Each target's values and the rows that have one."""
    out = {}
    rated = m["vote_count"].to_numpy() >= RATED_VOTES
    out["rating"] = (m["vote_average"].to_numpy(dtype=float), rated)
    rev, bud, yr = m["revenue"].to_numpy(dtype=float), m["budget"].to_numpy(dtype=float), m["year"].to_numpy(dtype=float)
    ok = (rev >= MIN_REVENUE) & (yr >= YEARS[0]) & (yr <= YEARS[1])
    lrev = np.log10(np.where(ok, rev, 1))
    year_med = pd.Series(lrev[ok]).groupby(yr[ok]).median()
    box = lrev - pd.Series(yr).map(year_med).to_numpy()
    out["box"] = (box, ok & np.isfinite(box))
    roi_ok = ok & (bud >= MIN_REVENUE)
    out["roi"] = (np.log10(np.where(roi_ok, rev, 1) / np.where(roi_ok, bud, 1)), roi_ok)
    original = m["collection"].isna().to_numpy() | (m["collection"].astype(str).str.len() == 0).to_numpy()
    for k in ("rating", "box", "roi"):
        out[k + "_original"] = (out[k][0], out[k][1] & original)
    return out


def genre_matrix(m):
    names = sorted({g for gs in m["genres"] for g in gs})
    col = {g: k for k, g in enumerate(names)}
    X = np.zeros((len(m), len(names)), dtype=np.float32)
    for i, gs in enumerate(m["genres"]):
        for g in gs:
            X[i, col[g]] = 1
    return X


def r2(y, p):
    return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def fit(base):
    m, v, _ = load(base)
    G = genre_matrix(m)
    feats = {"plot": v, "genres": G, "plot+genres": np.hstack([v, G])}
    cv = KFold(5, shuffle=True, random_state=SEED)
    labels = m["label_fine"].to_numpy()
    report, models, preds = {}, {}, pd.DataFrame({"id": m["id"]})
    for name, (y, rows) in targets(m).items():
        scores = {}
        for fname, X in feats.items():
            p = cross_val_predict(RidgeCV(alphas=ALPHAS), X[rows], y[rows], cv=cv)
            scores[fname] = round(r2(y[rows], p), 3)
            if fname == "plot":
                oof = p
        model = RidgeCV(alphas=ALPHAS).fit(v[rows], y[rows])
        models[name] = model
        full = model.predict(v)
        full[rows] = oof  # films with a known value get their out-of-fold prediction
        preds[name] = full
        idx = np.flatnonzero(rows)
        order = np.argsort(-oof)
        film = lambda i: {"name": m["name"].iloc[i], "year": int(m["year"].iloc[i]), "pred": round(float(full[i]), 3), "actual": round(float(y[i]), 3)}
        by_cluster = pd.DataFrame({"label": labels[rows], "pred": oof, "actual": y[rows]}).groupby("label").agg(
            n=("pred", "size"), pred=("pred", "mean"), actual=("actual", "mean"))
        by_cluster = by_cluster[by_cluster["n"] >= 30].sort_values("pred")
        report[name] = {
            "n": int(rows.sum()), "mean": round(float(y[rows].mean()), 3), "sd": round(float(y[rows].std()), 3),
            "alpha": float(model.alpha_), "cv_r2": scores,
            "top_films": [film(idx[k]) for k in order[:15]], "bottom_films": [film(idx[k]) for k in order[-10:]],
            "top_clusters": by_cluster.tail(10).iloc[::-1].round(3).reset_index().to_dict("records"),
            "bottom_clusters": by_cluster.head(10).round(3).reset_index().to_dict("records"),
        }
        print(f"{name}: n={rows.sum():,}  CV R^2 " + ", ".join(f"{k} {s}" for k, s in scores.items()) + f"  (alpha {model.alpha_:g})")
    out = base / "fit"
    out.mkdir(exist_ok=True)
    joblib.dump(models, out / "models.joblib")
    (out / "fit.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    preds.to_parquet(out / "preds.parquet")
    print(f"wrote {out}")


def score(base, path):
    """Embed pitches ({title, plot} list) with the map's model and score them with the fitted models,
    with each score's percentile among real films' out-of-fold predictions."""
    from src.pitch import embed_texts  # masks and erases like the films' text, if the embedding did

    _, _, meta = load(base)
    models = joblib.load(base / "fit" / "models.joblib")
    preds = pd.read_parquet(base / "fit" / "preds.parquet")
    pitches = json.loads(path.read_text(encoding="utf-8"))
    emb = embed_texts(base, meta, [f"{p['title']}. {p['plot']}" for p in pitches])
    scored = []
    for p, e in zip(pitches, emb):
        parts, row = [], {**p}
        for name, mdl in models.items():
            s = float(mdl.predict(e[None])[0])
            pct = (preds[name].to_numpy() < s).mean() * 100
            parts.append(f"{name} {s:.2f} (p{pct:.0f})")
            row[name] = {"score": round(s, 3), "pct": round(pct, 1)}
        scored.append(row)
        print(f"{p['title']}: " + ", ".join(parts))
    (base / "fit" / "pitch_scores.json").write_text(json.dumps(scored, indent=1, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    ap.add_argument("--score", help="JSON list of {title, plot} pitches to embed and score")
    args = ap.parse_args()
    base = domain_dir(args.domain)
    if args.score:
        return score(base, ROOT / args.score)
    fit(base)


if __name__ == "__main__":
    main()
