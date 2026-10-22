"""Stage 6: name each cluster.

For each cluster, the 20 games nearest its centroid (in full embedding space)
plus its most common mechanics and categories go to Claude, which returns a
2-5 word label. Tags are fine here: they name clusters, they don't place
games. Labels are cached by cluster membership, so reruns only pay for
clusters that changed.

Without ANTHROPIC_API_KEY (or with --offline) labels come from the cluster's
most over-represented tags instead.

    python src/label.py --model qwen3
"""

from __future__ import annotations

import argparse
import hashlib
import os
from collections import Counter

import numpy as np
import pandas as pd

from common import embedding_paths, labels_cache_path, load_dotenv, map_path, read_json, write_json

LLM_MODEL = os.environ.get("BGMAP_LABEL_MODEL", "claude-opus-5-5")
NOISE_LABEL = "Unclustered"

PROMPT = """These board games form one cluster on a map where games are placed by the meaning of their descriptions.

Most central games:
{games}

Most common mechanics: {mechanics}
Most common categories: {categories}

Give this cluster a 2-5 word label that says what its games have in common in theme or gameplay, specific enough to tell it apart from neighboring clusters (avoid generic words like "games" or "strategy"). Reply with the label only."""


def central_members(vecs: np.ndarray, idx: np.ndarray, n: int = 20) -> np.ndarray:
    centroid = vecs[idx].mean(axis=0)
    sims = vecs[idx] @ centroid
    return idx[np.argsort(-sims)[:n]]


def top_tags(series: pd.Series, n: int) -> list[str]:
    return [t for t, _ in Counter(t for tags in series for t in tags).most_common(n)]


def distinctive_tags(members: pd.DataFrame, everyone: pd.DataFrame, n: int = 2) -> list[str]:
    """Tags most over-represented in the cluster relative to the whole map."""
    scores = {}
    for col in ("mechanics", "categories"):
        inside = Counter(t for tags in members[col] for t in tags)
        overall = Counter(t for tags in everyone[col] for t in tags)
        for tag, k in inside.items():
            share_in = k / len(members)
            if share_in >= 0.25:
                scores[tag] = share_in / (overall[tag] / len(everyone))
    return [t for t, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:n]]


def tag_label(members: pd.DataFrame, everyone: pd.DataFrame) -> str:
    tags = distinctive_tags(members, everyone) or top_tags(members["mechanics"], 2)
    return " / ".join(tags) or "Misc"


def llm_label(client, prompt: str) -> str | None:
    # Fallbacks re-run a safety-declined request on another model server-side;
    # board game names occasionally trip classifiers (war games, horror).
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=4000,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text.splitlines()[0].strip(" \"'*.") if text else None


def label_level(df: pd.DataFrame, vecs: np.ndarray, col: str, cache: dict, client) -> dict[int, str]:
    labels = {-1: NOISE_LABEL}
    for cid in sorted(c for c in df[col].unique() if c >= 0):
        idx = np.flatnonzero(df[col].to_numpy() == cid)
        members = df.iloc[idx]
        central = df.iloc[central_members(vecs, idx)]
        key = hashlib.sha1(",".join(map(str, sorted(members["id"]))).encode()).hexdigest()[:16]
        source = "llm" if client else "tags"
        cached = cache.get(key)
        if cached and cached["source"] == source:
            labels[cid] = cached["label"]
            continue

        label = None
        if client:
            games = "\n".join(f"- {r.name} ({r.year})" if pd.notna(r.year) else f"- {r.name}"
                              for r in central.itertuples())
            prompt = PROMPT.format(games=games, mechanics=", ".join(top_tags(members["mechanics"], 8)),
                                   categories=", ".join(top_tags(members["categories"], 6)))
            label = llm_label(client, prompt)
        if not label:
            label, source = tag_label(members, df), "tags"
        cache[key] = {"label": label, "source": source, "size": len(idx),
                      "central": central["name"].tolist()[:5]}
        labels[cid] = label
        print(f"  {col} {cid:>3} ({len(idx):>5} games): {label}")
    return labels


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen3")
    ap.add_argument("--offline", action="store_true", help="tag-based labels only, no API calls")
    args = ap.parse_args()
    load_dotenv()

    df = pd.read_parquet(map_path(args.model))
    vecs = np.load(embedding_paths(args.model)[0])
    vecs = vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)

    client = None
    if not args.offline and os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        client = anthropic.Anthropic()
    print(f"labeling with {LLM_MODEL if client else 'tags (offline)'}")

    cache_path = labels_cache_path(args.model)
    cache = read_json(cache_path, {})
    try:
        for col in ("cluster", "cluster_coarse"):
            labels = label_level(df, vecs, col, cache, client)
            df[f"{col}_label"] = df[col].map(labels)
    finally:
        write_json(cache_path, cache)
    df.to_parquet(map_path(args.model), index=False)
    print(f"-> {map_path(args.model)}")


if __name__ == "__main__":
    main()
