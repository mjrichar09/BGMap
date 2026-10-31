"""Chart for src/fit.py: every film by predicted rating (x) and predicted box office (y) from the brand-free
models, as a density, with a few clusters labelled and the scored pitches on top.

    python -m src.fit_chart --domain movies     (after src.fit and src.fit --score)
"""

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.common import domain_dir
from src.gaps import MAP

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
AIMS = {  # validated with the dataviz skill's validate_palette.js (light); every mark is also labelled and shaped
    "rating": ("#2a78d6", "o", "Aimed at rating"),
    "box": ("#eb6834", "s", "Aimed at box office"),
    "both": ("#1baf7a", "D", "Aimed at both"),
    "control": ("#8a8984", "X", "Control"),
}
CLUSTERS = ["japan, anime", "superhero, based on comic", "ancient rome, bible", "zombie, zombie apocalypse",
            "christmas, santa claus", "true crime, murder", "music documentary, concert", "slasher, serial killer",
            "magic, princess", "samurai, jidaigeki"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    base = domain_dir(ap.parse_args().domain)
    preds = pd.read_parquet(base / "fit" / "preds.parquet")
    m = pd.read_parquet(base / "maps" / f"{MAP}.parquet", columns=["label_fine"])
    pitches = json.loads((base / "fit" / "pitch_scores.json").read_text(encoding="utf-8"))
    x, y = preds["rating_original"].to_numpy(), preds["box_original"].to_numpy()

    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.hexbin(x, y, gridsize=70, cmap="Greys", mincnt=1, bins="log", linewidths=0, alpha=0.55, extent=(4.8, 8.2, -1.6, 1.0))
    for lab in CLUSTERS:  # cluster means, labelled in muted ink
        sel = m["label_fine"].to_numpy() == lab
        if sel.sum():
            cx, cy = x[sel].mean(), y[sel].mean()
            ax.plot(cx, cy, "+", color=MUTED, ms=9, mew=1.5)
            ax.annotate(lab.split(",")[0], (cx, cy), xytext=(5, -11), textcoords="offset points", fontsize=8.5, color=MUTED, style="italic")
    for aim, (col, mk, name) in AIMS.items():
        ps = [p for p in pitches if p.get("aim") == aim]
        ax.scatter([p["rating_original"]["score"] for p in ps], [p["box_original"]["score"] for p in ps], s=70, c=col, marker=mk,
                   edgecolors=SURFACE, linewidths=2, zorder=3, label=name)
        for p in ps:
            ax.annotate(p["title"], (p["rating_original"]["score"], p["box_original"]["score"]), xytext=(7, 5),
                        textcoords="offset points", fontsize=9, color=INK, zorder=4)
    ticks = [-1.5, -1, -0.5, 0, 0.5, 1]
    ax.set_yticks(ticks, [f"×{10 ** t:.2g}" for t in ticks])
    ax.set_xlim(4.8, 8.2); ax.set_ylim(-1.6, 1.0)
    ax.set_xlabel("Predicted TMDB rating, from the plot alone", color=INK)
    ax.set_ylabel("Predicted box office vs. a typical film of its year", color=INK)
    ax.set_title("What the plot predicts: rating vs. box office\n(models fitted on non-franchise films; grey = all 36,841 films)",
                 loc="left", color=INK, fontsize=12)
    ax.grid(color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    for s in ax.spines.values(): s.set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.legend(loc="lower right", frameon=False, labelcolor=INK)
    out = base / "fit" / "rating_vs_box.png"
    fig.tight_layout(); fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
