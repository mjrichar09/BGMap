# BGMap

An interactive 2D map of every ranked BoardGameGeek base game, placed by the meaning of its description. See [plan.md](plan.md) for goals, design and milestones.

## Status

Phase 1 (register and scaffold) is done. All pipeline stages are built and run end to end on stub data. The next step is phase 2, the real fetch, which waits on BGG approving the API application.

## Pipeline

Each stage reads the previous stage's file and writes its own. Only stage 2 touches the network.

| Stage | Script | Reads | Writes |
| --- | --- | --- | --- |
| 1 | `src/ids.py` | BGG ranks CSV | `data/ids.csv` |
| 2 | `src/fetch.py` | `ids.csv` | `data/raw/batch_*.xml`, `manifest.jsonl` |
| 3 | `src/parse.py` | raw XML | `data/games.parquet` |
| 4 | `src/embed.py` | `games.parquet` | `data/embeddings/<model>.npy` + `.json` |
| 5 | `src/project.py` | embeddings | `data/map_<model>.parquet`, `data/neighbors_<model>.npy` |
| 6 | `src/label.py` | map + embeddings | cluster labels in the map file, `data/labels_<model>.json` cache |
| — | `src/render.py` | labeled map | `data/map_<model>.png`, `web/map_<model>.html` |

Embedding models (`--model`): `qwen3` (primary, Qwen3-Embedding-0.6B), `nomic`, `bge` (512-token baseline), and `tfidf` (no torch; used for stub runs and as a bag-of-words floor).

## Setup

Python 3.12+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # CUDA build for the RTX 3080
pip install -e ".[embed,dev]"
cp .env.example .env   # then fill in BGG_TOKEN (and ANTHROPIC_API_KEY for LLM cluster labels)
```

## Try it on stub data (no BGG token needed)

```bash
python src/make_stub.py                     # synthetic BGG-format XML in data/stub/raw
export BGMAP_DATA=data/stub                 # Windows PowerShell: $env:BGMAP_DATA="data/stub"
python src/parse.py
python src/embed.py --model tfidf           # or bge / qwen3
python src/project.py --model tfidf --min-cluster-size 20
python src/label.py --model tfidf --offline
python src/render.py --model tfidf          # open web/map_tfidf.html
```

The stub has 8 invented genres; a working pipeline recovers them as 8 clusters.

## Real run (once BGG approves the app)

1. Put the token in `.env` as `BGG_TOKEN`.
2. Download the ranks CSV while logged in: https://boardgamegeek.com/data_dumps/bg_ranks
3. Run:

```bash
python src/ids.py ~/Downloads/boardgames_ranks.zip
python src/fetch.py --limit 40      # two requests, to check the token works
python src/fetch.py                 # full run, about 1-2 hours; safe to stop and restart
python src/fetch.py --retry-missing # re-request any IDs BGG skipped
python src/parse.py
python src/embed.py --model qwen3
python src/embed.py --model bge
python src/project.py --model qwen3 --sweep
python src/label.py --model qwen3
python src/render.py --model qwen3
```

`fetch.py` waits 5 seconds between requests (`--delay`), retries BGG's queue/throttle responses with backoff, and stops on a 401/403 so a bad token doesn't burn through the ID list.

`label.py` uses Claude (`claude-opus-5-5` at low effort; override with `BGMAP_LABEL_MODEL`) when `ANTHROPIC_API_KEY` is set, and tag-based labels otherwise. Labels are cached by cluster membership, so reruns only pay for clusters that changed.

## Tests

```bash
pytest
```

## Terms

Raw BGG responses stay local (`data/` is gitignored). The map is private for v1; before sharing it publicly, re-read BGG's API terms and add the "Powered by BGG" logo linking back to BGG.
