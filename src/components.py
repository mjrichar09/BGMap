"""Principal components of the embedding space, as an analysis tool.

UMAP draws the map; PCA explains it. Each principal component is a direction
along which game descriptions vary most. For each one this reports:

  * how much of the variance it explains
  * the best-known games at each end (so the axis can be named)
  * mechanics and categories over-represented at each end
  * how strongly it tracks weight, year, rating, play time and description
    length (a strong link to description length or year is a confound worth
    knowing about, not a property of the games)

Writes data/eval/components_<model>.md and .json.

    python src/components.py --model qwen3
"""

from __future__ import annotations

import argparse
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from common import DATA_DIR, GAMES_PARQUET, embedding_paths, read_json, write_json

EVAL_DIR = DATA_DIR / "eval"
END_SHARE = 0.05  # each end of an axis = the 5% of games scoring highest / lowest
ATTRIBUTES = {
    "weight": "weight",
    "year": "year",
    "geek rating": "bayes_average",
    "play time (log)": "log_time",
    "description length (log)": "log_words",
    "max players": "max_players",
}


def load(model: str) -> tuple[np.ndarray, pd.DataFrame]:
    npy, meta_path = embedding_paths(model)
    vecs = np.load(npy).astype(np.float32)
    games = pd.read_parquet(GAMES_PARQUET)
    if read_json(meta_path)["ids"] != games["id"].astype(int).tolist():
        raise SystemExit(f"{npy.name} rows don't match games.parquet; rerun embed.py --model {model}.")
    vecs /= np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)
    games["log_time"] = np.log1p(pd.to_numeric(games["playing_time"], errors="coerce"))
    games["log_words"] = np.log1p(games["desc_words"])
    return vecs, games


def famous(games: pd.DataFrame, idx: np.ndarray, n: int) -> list[str]:
    """The n best-known games among idx (most ratings first)."""
    users = pd.to_numeric(games["users_rated"].iloc[idx], errors="coerce").fillna(0)
    return games["name"].iloc[idx[np.argsort(-users.to_numpy())[:n]]].tolist()


def enriched(games: pd.DataFrame, idx: np.ndarray, field: str, n: int = 5, min_share: float = 0.08) -> list[tuple[str, float]]:
    """Tags most over-represented at one end of an axis, with their lift over the whole collection."""
    overall = Counter(t for tags in games[field] for t in tags)
    inside = Counter(t for tags in games[field].iloc[idx] for t in tags)
    total, k = len(games), len(idx)
    scored = [(t, (c / k) / (overall[t] / total)) for t, c in inside.items() if c / k >= min_share]
    return [(t, round(lift, 1)) for t, lift in sorted(scored, key=lambda x: -x[1])[:n]]


def analyse(vecs: np.ndarray, games: pd.DataFrame, n_components: int) -> dict:
    pca = PCA(n_components=n_components, random_state=0)
    scores = pca.fit_transform(vecs)
    k = max(10, int(len(games) * END_SHARE))
    out = {"n_games": len(games), "components": []}
    for c in range(n_components):
        s = scores[:, c]
        order = np.argsort(s)
        low, high = order[:k], order[-k:]
        corr = {}
        for label, col in ATTRIBUTES.items():
            v = pd.to_numeric(games[col], errors="coerce")
            ok = v.notna().to_numpy()
            corr[label] = round(float(pd.Series(s[ok]).corr(pd.Series(v[ok].to_numpy()), method="spearman")), 2)
        out["components"].append({
            "component": c + 1,
            "variance": round(float(pca.explained_variance_ratio_[c]), 4),
            "high": {"games": famous(games, high, 8), "mechanics": enriched(games, high, "mechanics"), "categories": enriched(games, high, "categories")},
            "low": {"games": famous(games, low, 8), "mechanics": enriched(games, low, "mechanics"), "categories": enriched(games, low, "categories")},
            "correlations": corr,
        })
    out["cumulative_variance"] = round(float(np.sum(pca.explained_variance_ratio_)), 4)
    return out


def report(model: str, result: dict) -> str:
    tags = lambda pairs: ", ".join(f"{t} ×{lift}" for t, lift in pairs) or "–"
    lines = [f"# Principal components: {model}", "",
             f"{result['n_games']:,} games. The first {len(result['components'])} components explain "
             f"{result['cumulative_variance']:.1%} of the variance. Each end lists the best-known games among the "
             f"{END_SHARE:.0%} scoring highest or lowest, and the tags most over-represented there (×lift over all games).", "",
             "Correlations are Spearman, from −1 to 1. A strong link to description length or year means the axis "
             "partly reflects how or when descriptions were written, not what the games are.", ""]
    for c in result["components"]:
        strong = {k: v for k, v in c["correlations"].items() if abs(v) >= 0.3}
        lines += [f"## Component {c['component']} · {c['variance']:.1%} of variance", ""]
        for end, label in (("high", "High end"), ("low", "Low end")):
            e = c[end]
            lines += [f"**{label}:** {', '.join(e['games'])}", "",
                      f"- Mechanics: {tags(e['mechanics'])}", f"- Categories: {tags(e['categories'])}", ""]
        lines += ["Correlations: " + ", ".join(f"{k} {v:+.2f}" for k, v in c["correlations"].items()), ""]
        if strong:
            lines += ["Strongest links: " + ", ".join(f"**{k}** ({v:+.2f})" for k, v in strong.items()), ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen3")
    ap.add_argument("--components", type=int, default=8)
    args = ap.parse_args()

    vecs, games = load(args.model)
    result = analyse(vecs, games, args.components)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / f"components_{args.model}.md").write_text(report(args.model, result))
    write_json(EVAL_DIR / f"components_{args.model}.json", result)
    print(f"-> {EVAL_DIR / f'components_{args.model}.md'}")


if __name__ == "__main__":
    main()
