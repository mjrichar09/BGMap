"""End-to-end run of stages 3-6 on synthetic data with the TF-IDF embedder."""

import importlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent / "src"


def run(script, *args, env):
    subprocess.run([sys.executable, str(SRC / script), *args], check=True, env=env, capture_output=True)


def test_stub_pipeline(tmp_path, monkeypatch):
    import os

    env = {**os.environ, "BGMAP_DATA": str(tmp_path)}
    env.pop("ANTHROPIC_API_KEY", None)
    run("make_stub.py", "--out", str(tmp_path), "--per-genre", "40", env=env)
    run("parse.py", env=env)
    run("embed.py", "--model", "tfidf", env=env)
    run("project.py", "--model", "tfidf", "--min-cluster-size", "15", "--coarse-cluster-size", "60", env=env)
    run("label.py", "--model", "tfidf", "--offline", env=env)
    run("evaluate.py", env=env)

    games = pd.read_parquet(tmp_path / "games.parquet")
    assert len(games) == 320
    m = pd.read_parquet(tmp_path / "map_tfidf.parquet")
    assert m["id"].tolist() == games["id"].tolist()
    assert m["cluster_label"].notna().all()

    # The synthetic genres are encoded in names ("... Euro 3"); clusters should be nearly pure.
    genre = m["name"].str.split().str[-2]
    clustered = m[m["cluster"] >= 0]
    purity = genre[clustered.index].groupby(clustered["cluster"]).agg(lambda s: s.value_counts().iloc[0] / len(s))
    assert len(clustered) > 0.8 * len(m)
    # Genres overlap and publisher boilerplate pulls games together, so purity is high, not perfect.
    assert purity.mean() > 0.6

    import json
    metrics = json.loads((tmp_path / "eval" / "metrics.json").read_text())[0]
    assert metrics["mechanics_agreement"] > 2 * metrics["mechanics_random"]
    # The stub's publisher boilerplate is a confound the evaluation must catch.
    assert metrics["publisher_shared"] > 2 * metrics["publisher_shared_random"]
    assert "Spot check" in (tmp_path / "eval" / "report.md").read_text()

    nbrs = np.load(tmp_path / "neighbors_tfidf.npy")
    assert nbrs.shape == (320, 10)
    assert (nbrs != np.arange(320)[:, None]).all()


def test_label_uses_llm_and_caches(tmp_path, monkeypatch):
    monkeypatch.setenv("BGMAP_DATA", str(tmp_path))
    import common, label
    importlib.reload(common)
    importlib.reload(label)

    df = pd.DataFrame({
        "id": [1, 2, 3, 4], "name": list("abcd"), "year": [2000, 2001, None, 2003],
        "mechanics": [["Dice"], ["Dice"], ["Cards"], ["Cards"]],
        "categories": [["War"], ["War"], ["Party"], ["Party"]],
        "cluster": [0, 0, 1, -1],
    })
    vecs = np.eye(4, dtype=np.float32)
    calls = []

    class Block:
        type, text = "text", "Dice War Games\n"

    class Client:
        class beta:
            class messages:
                @staticmethod
                def create(**kwargs):
                    calls.append(kwargs)
                    return type("R", (), {"stop_reason": "end_turn", "content": [Block()]})

    cache = {}
    labels = label.label_level(df, vecs, "cluster", cache, Client())
    assert labels == {-1: label.NOISE_LABEL, 0: "Dice War Games", 1: "Dice War Games"}
    assert calls[0]["fallbacks"] == "default"
    label.label_level(df, vecs, "cluster", cache, Client())
    assert len(calls) == 2  # second pass served from cache
