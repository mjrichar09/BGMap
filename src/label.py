"""Stage 6 (shared): name clusters and join everything into one map table.

Interim labels, no LLM needed (tags may name clusters because they don't
place items):

- Regions are named by their most distinctive tags against the whole set,
  forced unique so no two regions share a label.
- Fine clusters are named by keywords only, scored against their parent
  region, so siblings inside one region get labels that tell them apart.
- Each cluster also gets example items: its most popular members that
  HDBSCAN placed itself, for hover cards.

Writes data/<domain>/maps/<layout>.parquet: the layout, both cluster levels
with labels and examples, and every overlay column from items.parquet
except the long text columns.

    python -m src.label --domain movies --layout qwen3__text_plot__inst__nn30_md0.05
"""

import argparse
import sys
from collections import Counter

import numpy as np
import pandas as pd

from src.common import domain_dir

DOMAINS = {
    "movies": {
        "region_tags": ["genres", "keywords"],
        "fine_tags": ["keywords"],
        "popularity": "imdb_votes",
        # TMDB keywords that describe the production, not the film
        "stop": {
            "woman director", "duringcreditsstinger", "aftercreditsstinger", "based on novel or book",
            "remake", "sequel", "black and white", "independent film", "short film", "silent film",
        },
    },
    "boardgames": {
        "region_tags": ["categories", "mechanics"],
        "fine_tags": ["mechanics", "categories"],
        "popularity": "usersrated",
        "stop": set(),
    },
}
LONG_TEXT = ["text", "plot", "text_plot"]
EXAMPLES = 3


def tag_sets(items: pd.DataFrame, columns: list[str], stop: set[str]) -> list[set[str]]:
    sets = [set() for _ in range(len(items))]
    for col in columns:
        for i, tags in enumerate(items[col]):
            sets[i].update(t.lower() for t in (tags if tags is not None else []) if t.lower() not in stop)
    return sets


def ranked_tags(members: np.ndarray, background: np.ndarray, tags: list[set[str]], min_share: float = 0.08) -> list[str]:
    """Tags of `members` ranked by share weighted by log-lift over `background`."""
    counts = Counter(t for i in members for t in tags[i])
    base = Counter(t for i in background for t in tags[i])
    scores = {}
    for tag, k in counts.items():
        share = k / len(members)
        lift = share / (base[tag] / len(background))
        if share >= min_share and k >= 3 and lift > 1.1:
            scores[tag] = share * np.log(lift)
    return sorted(scores, key=scores.get, reverse=True)


def unique_label(ranked: list[str], used: set[tuple], size: int) -> str:
    """First `size`-tag combination (in rank order) not already used by another cluster."""
    for start in range(max(1, len(ranked) - size + 1)):
        combo = tuple(ranked[:1] + ranked[1 + start : size + start]) if size > 1 else (ranked[start],)
        if combo and frozenset(combo) not in used:
            used.add(frozenset(combo))
            return ", ".join(combo)
    return ", ".join(ranked[:size])


def examples(members: np.ndarray, core: np.ndarray, names: pd.Series, popularity: pd.Series, k: int = EXAMPLES) -> list[str]:
    """Most popular distinct names among the members HDBSCAN placed itself."""
    pool = members[core[members]] if core[members].any() else members
    ranked = names.iloc[pool[popularity.iloc[pool].fillna(0).to_numpy().argsort()[::-1]]]
    return list(dict.fromkeys(ranked))[:k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--layout", required=True, help="file stem in data/<domain>/layouts/")
    args = ap.parse_args()

    cfg = DOMAINS[args.domain]
    base = domain_dir(args.domain)
    layout = pd.read_parquet(base / "layouts" / f"{args.layout}.parquet")
    items = pd.read_parquet(base / "items.parquet")
    items = items.drop(columns=[c for c in LONG_TEXT if c in items]).set_index("id").loc[layout["id"]].reset_index()

    region_tags = tag_sets(items, cfg["region_tags"], cfg["stop"])
    fine_tags = tag_sets(items, cfg["fine_tags"], cfg["stop"])
    coarse, fine = layout["cluster_coarse"].to_numpy(), layout["cluster_fine"].to_numpy()
    core = layout["core"].to_numpy()
    everyone = np.arange(len(layout))
    names, popularity = items["name"], items[cfg["popularity"]]

    region_label, region_examples, used = {}, {}, set()
    for c in pd.Series(coarse).value_counts().index:  # largest first, so big regions get the best labels
        members = np.flatnonzero(coarse == c)
        region_label[c] = unique_label(ranked_tags(members, everyone, region_tags), used, 3) or f"region {c}"
        region_examples[c] = ", ".join(examples(members, core, names, popularity))

    # Fine labels: keywords against the parent region, then against everything,
    # and when no keyword stands out, the cluster's two best-known titles.
    fine_label, fine_examples, used = {}, {}, set()
    for c in pd.Series(fine).value_counts().index:
        members = np.flatnonzero(fine == c)
        parent = np.flatnonzero(coarse == coarse[members[0]])
        ranked = ranked_tags(members, parent, fine_tags, min_share=0.05)
        if len(ranked) < 2:
            ranked = ranked_tags(members, everyone, fine_tags, min_share=0.05)
        label = unique_label(ranked, used, 2) if ranked else ""
        fine_label[c] = label or " · ".join(examples(members, core, names, popularity, k=2))
        fine_examples[c] = ", ".join(examples(members, core, names, popularity))

    layout["label_coarse"] = [region_label[c] for c in coarse]
    layout["examples_coarse"] = [region_examples[c] for c in coarse]
    layout["label_fine"] = [fine_label[c] for c in fine]
    layout["examples_fine"] = [fine_examples[c] for c in fine]

    out_dir = base / "maps"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{args.layout}.parquet"
    layout.merge(items, on="id").to_parquet(out, index=False)

    # Titles include characters a Windows console's code page can't show; print those as "?".
    sys.stdout.reconfigure(errors="replace")
    for c in pd.Series(coarse).value_counts().index:
        print(f"{(coarse == c).sum():6,}  {region_label[c]}  [{region_examples[c]}]")
        children = pd.Series(fine[coarse == c]).value_counts().index[:3]
        for f in children:
            print(f"          · {fine_label[f]}  [{fine_examples[f]}]")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
