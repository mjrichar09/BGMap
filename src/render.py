"""Render a labelled map: a static PNG and datamapplot's interactive HTML.

The PNG uses the broad regions only; the HTML has both label levels (fine
labels appear on zoom), hover cards, search, and points sized by popularity.

    python -m src.render --domain movies --map qwen3__text_plot__nn30_md0.1
"""

import argparse
import html

import datamapplot
import numpy as np
import pandas as pd

from src.common import domain_dir

NOISE = "Unlabelled"


def movie_card(r) -> str:
    def esc(v):
        return html.escape(str(v)) if v is not None and v == v else ""

    poster = f'<img src="{esc(r.thumbnail)}" style="width:80px;float:left;margin-right:8px">' if r.thumbnail else ""
    rating = f"IMDb {r.imdb_rating:.1f}" if pd.notna(r.imdb_rating) else ""
    year = f" ({int(r.year)})" if pd.notna(r.year) else ""
    return (
        f"{poster}<b>{esc(r.name)}</b>{year}<br>"
        f"{esc(', '.join(r.genres))}<br>{esc(', '.join(r.directors[:2]))}<br>{rating} · {esc(r.certification)}"
        f'<div style="clear:both;margin-top:6px;font-size:90%;color:#666">'
        f"<i>{esc(r.label_coarse)} › {esc(r.label_fine)}</i><br>Like: {esc(r.examples_fine)}</div>"
    )


DOMAINS = {
    "movies": {"title": "Movie Map", "card": movie_card, "size": "imdb_votes"},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--map", required=True, help="file stem in data/<domain>/maps/")
    ap.add_argument("--static-only", action="store_true", help="skip the interactive HTML")
    args = ap.parse_args()

    cfg = DOMAINS[args.domain]
    base = domain_dir(args.domain)
    m = pd.read_parquet(base / "maps" / f"{args.map}.parquet")
    coords = m[["x", "y"]].to_numpy()
    fine, coarse = m["label_fine"].to_numpy(dtype=object), m["label_coarse"].to_numpy(dtype=object)
    subtitle = f"{len(m):,} items · {args.map}"
    out_dir = base / "renders"
    out_dir.mkdir(exist_ok=True)

    fig, _ = datamapplot.create_plot(coords, coarse, title=cfg["title"], sub_title=subtitle, noise_label=NOISE)
    fig.savefig(out_dir / f"{args.map}.png", dpi=150, bbox_inches="tight")
    print(f"Wrote {out_dir / args.map}.png")
    if args.static_only:
        return

    size = np.log1p(m[cfg["size"]].fillna(0).to_numpy(dtype=float))
    plot = datamapplot.create_interactive_plot(
        coords,
        fine,
        coarse,
        hover_text=m["name"].tolist(),
        hover_text_html_template="{card}",
        extra_point_data=pd.DataFrame({"card": [cfg["card"](r) for r in m.itertuples()]}),
        marker_size_array=1 + 3 * size / size.max(),
        enable_search=True,
        title=cfg["title"],
        sub_title=subtitle,
        noise_label=NOISE,
    )
    plot.save(str(out_dir / f"{args.map}.html"))
    print(f"Wrote {out_dir / args.map}.html")


if __name__ == "__main__":
    main()
