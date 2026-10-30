"""Write the chart data for the two follow-up videos from the movie map's data.

    videos/mmm-same-director/assets/data/stats.json   PCA scatter, people ranges
    videos/mmm-hollywood-pays/assets/data/stats.json  originality fifths, money, decade trends

Similarity is plot similarity in the full embedding (mean pairwise cosine between a person's films).
Ratings, box office and budgets are TMDB's; box office is not adjusted for inflation.
Run from the repo root:  .venv/Scripts/python videos/make_video_stats.py
"""
import json
import pathlib

import numpy as np
import pandas as pd
import torch

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAP = ROOT / "data/movies/maps/qwen3__text_plot__inst__nn30_md0.05.parquet"
EMB = ROOT / "data/movies/embeddings/qwen3__text_plot__inst.npy"
SITE = ROOT / "data/movies/site/data"

m = pd.read_parquet(MAP)
V = torch.tensor(np.load(EMB).astype(np.float32)).cuda()


def mean_pairwise(ix):
    s = (V[ix] @ V[ix].T).cpu().numpy(); n = len(ix)
    return float((s.sum() - n) / (n * n - n))


def films_of(col, name):
    return np.array(sorted(m.index[m[col].apply(lambda xs: name in list(xs))]))


# ---------- video 2: same director, same movie? ----------
axes = json.loads((SITE / "axes.json").read_text(encoding="utf-8"))
x, y = np.array(axes["x"]), np.array(axes["y"])
lo, hi = np.percentile(x, 1), np.percentile(x, 99); ylo, yhi = np.percentile(y, 1), np.percentile(y, 99)
norm = lambda i: [round(float((x[i] - lo) / (hi - lo)), 4), round(float((y[i] - ylo) / (yhi - ylo)), 4)]
known = m.index[m.vote_count >= 300].to_numpy()
rng = np.random.default_rng(7)
sample = sorted(rng.choice(known, 1800, replace=False).tolist())


def person(col, name, top=6):
    ix = films_of(col, name)
    best = m.loc[ix].sort_values("vote_count", ascending=False).index[:top]
    return {"name": name, "n": int(len(ix)), "similarity": round(mean_pairwise(ix), 2),
            "films": [{"name": m.name[i], "year": int(m.year[i]), "xy": norm(i), "label": bool(i in best)} for i in ix]}


rows = []
for a, ix in m.explode("cast").groupby("cast").groups.items():
    ix = np.array(sorted(set(ix)))
    if len(ix) >= 25 and m.vote_count[ix].median() >= 1000:
        rows.append({"name": a, "n": int(len(ix)), "similarity": round(mean_pairwise(ix), 3)})
rows.sort(key=lambda r: r["similarity"])
v2 = {
    "pca": {"x_axis": {"low": "romance, comedy", "high": "action, thriller", "variance": axes["axes"][0]["variance"]},
            "y_axis": {"low": "crime, thriller", "high": "animation", "variance": axes["axes"][1]["variance"]},
            "points": [norm(i) for i in sample]},
    "ridley_scott": person("directors", "Ridley Scott"),
    "jason_statham": person("cast", "Jason Statham"),
    "range_rule": "actors with 25+ films on the map and a median of 1,000+ TMDB votes; lower similarity = wider range",
    "widest_range": rows[:5],
    "most_typecast": rows[::-1][:6],
}
out2 = ROOT / "videos/mmm-same-director/assets/data"; out2.mkdir(parents=True, exist_ok=True)
(out2 / "stats.json").write_text(json.dumps(v2, indent=1, ensure_ascii=False), encoding="utf-8")

# ---------- video 3: what Hollywood pays for ----------
o = []
for s in range(0, len(V), 4096):
    S = V[s:s + 4096] @ V.T
    S[torch.arange(S.shape[0]), torch.arange(s, s + S.shape[0])] = -2
    o.append(1 - S.topk(15, dim=1).values.mean(1).cpu())
m["orig"] = torch.cat(o).numpy()
k = m[m.vote_count >= 200].copy()
k["q"] = pd.qcut(k.orig, 5, labels=False)
fifths = [{"fifth": int(q) + 1, "rating": round(float(g.vote_average.mean()), 2),
           "median_box_office_m": round(float(g.revenue[g.revenue > 1e5].median() / 1e6), 1), "films": int(len(g))}
          for q, g in k.groupby("q")]
money = m[(m.revenue > 1e6) & (m.budget > 1e5)].copy(); money["roi"] = money.revenue / money.budget
c = money.groupby("label_fine").agg(n=("id", "size"), rev=("revenue", "median"), roi=("roi", "median")).query("n >= 25")
NAMES = {"james bond, british secret service": "James Bond", "slasher, serial killer": "Slashers",
         "south korea, busan, south korea": "Korean thrillers", "dance, dancing": "Dance movies",
         "superhero, based on comic": "Superheroes", "politics, usa president": "Political dramas",
         "apartheid, 1970s": "Apartheid dramas", "animals, animal behaviour": "Animal adventures",
         "murder, paris, france": "French murder mysteries"}
SKIP_ON_SCREEN = {"rape and revenge, rape"}  # near the bottom too, but not a cluster to headline in a promo
roi = [{"label": NAMES.get(l, l), "cluster": l, "roi": round(float(r.roi), 1), "films": int(r.n)} for l, r in c.sort_values("roi", ascending=False).iterrows() if l not in SKIP_ON_SCREEN]
g = m.explode("genres"); g["dec"] = (g.year // 10) * 10
tot = m[m.year.between(1950, 2029)].groupby((m.year // 10) * 10).size()
share = g[g.dec.between(1950, 2020)].groupby(["dec", "genres"]).size().unstack(fill_value=0).div(tot, axis=0)
trends = {gen: [{"decade": int(d), "share": round(float(share.loc[d, gen]), 3)} for d in share.index]
          for gen in ["Western", "Thriller", "Horror", "Documentary"]}
top_orig = m[m.vote_count >= 5000].nlargest(6, "orig")[["name", "year"]].to_dict("records")
v3 = {
    "originality_rule": "1 - mean plot similarity to a film's 15 nearest neighbours; films with 200+ TMDB votes, split into fifths",
    "fifths": fifths,
    "most_original_popular": [{"name": r["name"], "year": int(r["year"])} for r in top_orig],
    "superheroes_median_box_office_m": round(float(c.loc["superhero, based on comic", "rev"] / 1e6)),
    "roi_rule": "median of box office / budget per fine cluster, clusters with 25+ films with known budget and box office",
    "roi_top": roi[:5], "roi_bottom": roi[::-1][:3],
    "roi_bottom_note": "the rape-and-revenge cluster (0.9x) is also near the bottom and is left off screen",
    "trend_rule": "share of each decade's films tagged with the genre (films can carry several genres)",
    "trends": trends,
}
out3 = ROOT / "videos/mmm-hollywood-pays/assets/data"; out3.mkdir(parents=True, exist_ok=True)
(out3 / "stats.json").write_text(json.dumps(v3, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: v2[k] for k in ("widest_range", "most_typecast")}, ensure_ascii=False))
print(json.dumps({k: v3[k] for k in ("fifths", "roi_top", "roi_bottom", "superheroes_median_box_office_m")}, ensure_ascii=False))
print(v2["ridley_scott"]["n"], v2["ridley_scott"]["similarity"], v2["jason_statham"]["n"], v2["jason_statham"]["similarity"])
