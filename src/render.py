"""Render the map: a static PNG to judge the layout, and datamapplot's
interactive HTML page (hover card, search, zoom) as the first web version.

    python src/render.py --model qwen3
    -> data/map_qwen3.png, web/map_qwen3.html
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from common import DATA_DIR, WEB_DIR, map_path
from label import NOISE_LABEL

HOVER_TEMPLATE = """
<div style="display:flex;gap:8px;max-width:340px">
  <img src="{thumbnail}" style="width:64px;height:64px;object-fit:cover" onerror="this.style.display='none'">
  <div>
    <div style="font-weight:600">{hover_text} <span style="font-weight:400">({year})</span></div>
    <div>Rank {rank} · Weight {weight} · {players} players · {playing_time} min</div>
    <div style="font-size:85%;opacity:.8">{mechanics}</div>
  </div>
</div>
"""


def fmt(value, spec: str = "") -> str:
    return "?" if pd.isna(value) else format(value, spec)


def player_range(row) -> str:
    lo, hi = row.min_players, row.max_players
    if pd.isna(lo):
        return "?"
    return f"{lo}" if pd.isna(hi) or hi == lo else f"{lo}–{hi}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen3")
    ap.add_argument("--no-static", action="store_true")
    args = ap.parse_args()

    import datamapplot

    df = pd.read_parquet(map_path(args.model))
    if "cluster_label" not in df:
        raise SystemExit("no cluster labels yet; run src/label.py first.")
    coords = df[["x", "y"]].to_numpy()
    fine = df["cluster_label"].fillna(NOISE_LABEL).to_numpy()
    coarse = df["cluster_coarse_label"].fillna(NOISE_LABEL).to_numpy()
    title = f"Board games by description ({args.model})"

    if not args.no_static:
        fig, _ = datamapplot.create_plot(coords, fine, title=title, sub_title=f"{len(df):,} ranked base games",
                                         noise_label=NOISE_LABEL, label_wrap_width=14)
        png = DATA_DIR / f"map_{args.model}.png"
        fig.savefig(png, bbox_inches="tight")
        print(f"-> {png}")

    extra = pd.DataFrame({
        "thumbnail": df["thumbnail"].fillna(""),
        "year": df["year"].map(fmt),
        "rank": df["rank"].map(fmt),
        "weight": df["weight"].map(lambda v: fmt(v, ".1f")),
        "players": [player_range(r) for r in df.itertuples()],
        "playing_time": df["playing_time"].map(fmt),
        "mechanics": df["mechanics"].map(lambda m: ", ".join(list(m)[:4])),
    })
    sizes = np.log1p(df["users_rated"].fillna(0).astype(float).to_numpy())
    # datamapplot can't draw a label layer with no clusters in it.
    layers = [layer for layer in (fine, coarse) if (layer != NOISE_LABEL).any()]
    plot = datamapplot.create_interactive_plot(
        coords, *layers,
        hover_text=df["name"].fillna("").to_numpy(),
        extra_point_data=extra,
        hover_text_html_template=HOVER_TEMPLATE,
        marker_size_array=1 + 2 * sizes / max(sizes.max(), 1),
        noise_label=NOISE_LABEL,
        enable_search=True,
        title=title,
        sub_title="Hover for details · search to find a game",
    )
    WEB_DIR.mkdir(exist_ok=True)
    html = WEB_DIR / f"map_{args.model}.html"
    plot.save(str(html))
    print(f"-> {html}")


if __name__ == "__main__":
    main()
