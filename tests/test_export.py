import json
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def test_export_writes_page_and_consistent_data(tmp_path):
    import os

    env = {**os.environ, "BGMAP_DATA": str(tmp_path / "data")}
    run = lambda *a: subprocess.run([sys.executable, str(SRC / a[0]), *a[1:]], check=True, env=env, capture_output=True)
    run("make_stub.py", "--out", str(tmp_path / "data"), "--per-genre", "30")
    run("parse.py")
    run("embed.py", "--model", "tfidf")
    run("project.py", "--model", "tfidf", "--min-cluster-size", "10", "--coarse-cluster-size", "40")
    run("label.py", "--model", "tfidf", "--offline")
    run("export.py", "--out", str(tmp_path / "site"))

    site = tmp_path / "site"
    page = (site / "index.html").read_text()
    assert page.startswith("<!doctype html>") and "deck.gl@9.1.0" in page
    manifest = json.loads((site / "data" / "manifest.json").read_text())
    games = json.loads((site / "data" / "games.json").read_text())
    model = json.loads((site / "data" / "tfidf.json").read_text())
    n = len(games["id"])
    assert n == manifest["count"] == len(model["x"]) == len(model["cluster"])
    assert len(model["neighbors"]) == n * model["k"]
    assert all(0 <= j < n for j in model["neighbors"])
    assert all(0 <= t < len(manifest["mechanics"]) for tags in games["mech"] for t in tags)
    assert model["labels"] and all(isinstance(d["label"], str) for d in model["labels"])
