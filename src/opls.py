"""PLS and OPLS on the plot embedding: the same targets as src/fit.py, as latent-component models.

PLS (scikit-learn PLSRegression, no scaling: the embedding's dimensions share a scale) builds k latent
components that maximize covariance with the target; k is chosen by the same 5-fold cross-validation as
src/fit.py's ridge models, so the R^2 values compare directly (k is picked on the CV score, so the best
value is slightly optimistic).

OPLS (Trygg & Wold 2002, one target) splits the embedding's variation into ONE predictive component and
n_orth orthogonal components that vary independently of the target. For one target it predicts exactly as
PLS with 1 + n_orth components; what it adds is the predictive axis: a single direction through story space
per target (a "box office axis"), with the target-unrelated variation peeled off first. Each film's score
on that axis, the films and clusters at either end, and the axis itself are kept for interpretation (and,
later, layouts or steering pitches along it).

Writes data/<domain>/fit/opls.json (scores, axis ends) and opls_axes.npz (per target: mean, orthogonal
weights and loadings, predictive weight, coefficient, so new vectors can be projected).

    python -m src.opls --domain movies
    python -m src.opls --domain movies --proposals   # score the curated pitches for the site's Fit view

--proposals embeds every curated pitch (content/<domain>_unmade.json, _deserts.json, _extra_pitches.json)
like the films (src.pitch), ranks it among real films scored the same way (src.fit reference) for rating,
box office and popularity, places it on each Fit axis where films with that percentile sit, and writes
data/<domain>/fit/proposals.json.
"""

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import KFold

from src.common import ROOT, domain_dir
from src.fit import SEED, r2, targets
from src.gaps import load

KS = [1, 2, 4, 8, 16, 32, 64]
TARGETS = ["rating_original", "box_original", "roi_original", "votes_original"]
AXES = {"rating": "rating_original", "box": "box_original", "votes": "votes_original"}   # the Fit view's x, y, z


def axis_scores(base, X):
    """Rows of X on each Fit axis, standardized on the films' own scores (0 = typical film, 1 = one SD)."""
    z = np.load(base / "fit" / "opls_axes.npz")
    _, v, _ = load(base)
    out = {}
    for short, t in AXES.items():
        def proj(A):
            A = A.astype(np.float64) - z[f"{t}__mx"]
            for wo, po in zip(z[f"{t}__Wo"], z[f"{t}__Po"]):
                A = A - np.outer(A @ wo, po)
            return A @ z[f"{t}__w"]
        films = proj(v)
        out[short] = (proj(X) - films.mean()) / films.std()
    return out


def proposals(base, domain):
    import joblib

    from src.fit import reference
    from src.pitch import embed_texts

    m, v, meta = load(base)
    label = m.groupby("cluster_fine")["label_fine"].first()
    rows = []
    for p in json.loads((ROOT / "content" / f"{domain}_unmade.json").read_text(encoding="utf-8")):
        rows.append({"kind": "unmade", "title": p["title"], "logline": p["logline"], "plot": p["plot"], "between": [label[a] for a in p["parents"]]})
    for p in json.loads((ROOT / "content" / f"{domain}_deserts.json").read_text(encoding="utf-8")):
        rows.append({"kind": "desert", "title": p["title"], "logline": p["logline"], "plot": p["plot"], "between": [f"films like {p['seed'].rsplit(' (', 1)[0]}", label[p["cluster"]]]})
    extra = ROOT / "content" / f"{domain}_extra_pitches.json"
    for p in json.loads(extra.read_text(encoding="utf-8")) if extra.exists() else []:
        rows.append({"kind": "horror", "title": p["title"], "logline": p["logline"], "plot": p["plot"], "between": p["between"]})
    e = embed_texts(base, meta, [f"{r['title']}. {r['plot']}" for r in rows])
    models = joblib.load(base / "fit" / "models.joblib")
    ref = reference(base, meta, models)
    # Placed on each axis where the films with the same (calibrated) percentile sit: a pitch's plot-only text
    # projects lower than a film's full map vector, so raw axis scores would sink every pitch (see src.fit reference).
    films = axis_scores(base, v)
    for k, r in enumerate(rows):
        r["pct"] = {a: round(float((ref[t].to_numpy() < models[t].predict(e[k:k + 1])[0]).mean() * 100)) for a, t in AXES.items()}
        r["axes"] = {a: round(float(np.quantile(films[a], min(max(r["pct"][a], 0.5), 99.5) / 100)), 3) for a in AXES}
    out = base / "fit" / "proposals.json"
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out}: {len(rows)} proposals")


class OPLS:
    """One-target OPLS. fit(X, y) peels n_orth orthogonal components, then one predictive component."""

    def __init__(self, n_orth):
        self.n_orth = n_orth

    def fit(self, X, y):
        self.mx, self.my = X.mean(0), y.mean()
        X, y = X - self.mx, y - self.my
        self.Wo, self.Po = [], []
        for _ in range(self.n_orth):
            w = X.T @ y; w /= np.linalg.norm(w)
            t = X @ w; p = X.T @ t / (t @ t)
            wo = p - (w @ p) * w; wo /= np.linalg.norm(wo)
            to = X @ wo; po = X.T @ to / (to @ to)
            X = X - np.outer(to, po)
            self.Wo.append(wo); self.Po.append(po)
        w = X.T @ y; self.w = w / np.linalg.norm(w)
        t = X @ self.w
        self.c = (y @ t) / (t @ t)
        self.p = X.T @ t / (t @ t)   # predictive loading: what the axis looks like in the (filtered) embedding
        return self

    def filtered(self, X):
        X = X - self.mx
        for wo, po in zip(self.Wo, self.Po):
            X = X - np.outer(X @ wo, po)
        return X

    def score(self, X):
        """Each row's position on the predictive axis."""
        return self.filtered(X) @ self.w

    def predict(self, X):
        return self.my + self.c * self.score(X)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    ap.add_argument("--proposals", action="store_true", help="score the curated pitches on the Fit axes")
    args = ap.parse_args()
    base = domain_dir(args.domain)
    if args.proposals:
        return proposals(base, args.domain)
    m, v, _ = load(base)
    v = v.astype(np.float64)
    tg = targets(m)
    ridge = json.loads((base / "fit" / "fit.json").read_text(encoding="utf-8"))
    cv = KFold(5, shuffle=True, random_state=SEED)
    labels, names, years = m["label_fine"].to_numpy(), m["name"].to_numpy(), m["year"].to_numpy()
    report, axes = {}, {}
    for t in TARGETS:
        y, ok = tg[t]
        X, Y = v[ok], y[ok]
        folds = list(cv.split(X))
        pls = {}
        for k in KS:
            pred = np.zeros_like(Y)
            for tr, te in folds:
                pred[te] = PLSRegression(n_components=k, scale=False).fit(X[tr], Y[tr]).predict(X[te]).ravel()
            pls[k] = r2(Y, pred)
        best = max(pls, key=pls.get)
        # OPLS with the same total number of components: same predictions as PLS (checked on fold 1).
        tr, te = folds[0]
        o = OPLS(best - 1).fit(X[tr], Y[tr])
        p_pls = PLSRegression(n_components=best, scale=False).fit(X[tr], Y[tr]).predict(X[te]).ravel()
        same = float(np.max(np.abs(o.predict(X[te]) - p_pls)))
        full = OPLS(best - 1).fit(X, Y)
        s = full.score(v)                                  # every film's position on the axis
        s = (s - s[ok].mean()) / s[ok].std()
        order = np.argsort(-s)
        film = lambda i: {"name": names[i], "year": int(years[i]), "axis": round(float(s[i]), 2)}
        cl = pd.DataFrame({"label": labels, "axis": s}).groupby("label")["axis"].agg(["size", "mean"])
        cl = cl[cl["size"] >= 30].sort_values("mean")
        report[t] = {
            "n": int(ok.sum()), "ridge_r2": ridge[t]["cv_r2"]["plot"], "pls_r2": {str(k): round(r, 3) for k, r in pls.items()},
            "best_components": best, "opls": {"orthogonal": best - 1, "predictive": 1},
            "opls_vs_pls_max_diff": same,
            "axis_r2_alone": round(r2(Y, np.poly1d(np.polyfit(s[ok], Y, 1))(s[ok])), 3),
            "top_films": [film(i) for i in order[:15]], "bottom_films": [film(i) for i in order[-10:][::-1]],
            "top_clusters": [{"label": l, "axis": round(a, 2)} for l, a in cl["mean"].tail(10).iloc[::-1].items()],
            "bottom_clusters": [{"label": l, "axis": round(a, 2)} for l, a in cl["mean"].head(10).items()],
        }
        axes[t] = {"mx": full.mx, "w": full.w, "p": full.p, "c": full.c, "my": full.my,
                   "Wo": np.array(full.Wo) if full.Wo else np.zeros((0, v.shape[1])), "Po": np.array(full.Po) if full.Po else np.zeros((0, v.shape[1]))}
        print(f"{t}: ridge R^2 {report[t]['ridge_r2']} | PLS " + " ".join(f"k{k}={r:.3f}" for k, r in pls.items())
              + f" | best k={best}; OPLS = 1 predictive + {best - 1} orthogonal (max diff vs PLS {same:.1e})", flush=True)
    out = base / "fit"
    (out / "opls.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    np.savez(out / "opls_axes.npz", **{f"{t}__{k}": a for t, d in axes.items() for k, a in d.items()})
    print(f"wrote {out / 'opls.json'}, {out / 'opls_axes.npz'}")


if __name__ == "__main__":
    main()
