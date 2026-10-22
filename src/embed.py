"""Stage 4: embed each game's text with a local model.

Writes data/embeddings/<model>.npy (row order matches games.parquet) and a
<model>.json with the model name, date, settings and the ID order.

    python src/embed.py --model qwen3     # primary, CUDA fp16 if available
    python src/embed.py --model bge       # fast 512-token baseline
    python src/embed.py --model tfidf     # no torch needed; stub runs/tests
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from common import GAMES_PARQUET, MODELS, embedding_paths, write_json


def embed_tfidf(texts: list[str], dim: int) -> np.ndarray:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    tfidf = TfidfVectorizer(stop_words="english", sublinear_tf=True, min_df=2, max_df=0.5)
    x = tfidf.fit_transform(texts)
    dim = min(dim, x.shape[1] - 1, x.shape[0] - 1)
    vecs = TruncatedSVD(n_components=dim, random_state=0).fit_transform(x)
    return vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)


def embed_st(texts: list[str], cfg: dict, batch_size: int | None, max_len: int | None) -> tuple[np.ndarray, dict]:
    import torch
    from sentence_transformers import SentenceTransformer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    kwargs = {"torch_dtype": torch.float16} if device == "cuda" else {}
    model = SentenceTransformer(
        cfg["name"], device=device, model_kwargs=kwargs, trust_remote_code=cfg.get("trust_remote_code", False)
    )
    model.max_seq_length = max_len or cfg["max_seq_length"]
    docs = [cfg["prefix"] + t for t in texts]

    lengths = [len(ids) for ids in model.tokenizer(docs, add_special_tokens=True)["input_ids"]]
    truncated = int(sum(n > model.max_seq_length for n in lengths))
    print(f"{device}, max_seq_length={model.max_seq_length}: {truncated:,}/{len(docs):,} texts "
          f"truncated (median {int(np.median(lengths))} tokens, p95 {int(np.percentile(lengths, 95))})")

    vecs = model.encode(
        docs, batch_size=batch_size or cfg["batch_size"], normalize_embeddings=True,
        show_progress_bar=True, convert_to_numpy=True,
    )
    info = {"device": device, "max_seq_length": model.max_seq_length, "truncated": truncated,
            "token_median": int(np.median(lengths)), "token_p95": int(np.percentile(lengths, 95))}
    return vecs.astype(np.float32), info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen3", choices=sorted(MODELS))
    ap.add_argument("--batch-size", type=int, help="override the model's default batch size")
    ap.add_argument("--max-seq-length", type=int, help="override the model's token cap")
    args = ap.parse_args()

    games = pd.read_parquet(GAMES_PARQUET, columns=["id", "embed_text"])
    texts = games["embed_text"].tolist()
    cfg = MODELS[args.model]
    start = time.time()
    if args.model == "tfidf":
        vecs, info = embed_tfidf(texts, cfg["dim"]), {}
    else:
        vecs, info = embed_st(texts, cfg, args.batch_size, args.max_seq_length)
    elapsed = time.time() - start

    npy, meta = embedding_paths(args.model)
    npy.parent.mkdir(parents=True, exist_ok=True)
    np.save(npy, vecs.astype(np.float32))
    write_json(meta, {
        "model_key": args.model, "model": cfg["name"], "prefix": cfg.get("prefix", ""),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "seconds": round(elapsed, 1),
        "n": int(vecs.shape[0]), "dim": int(vecs.shape[1]), **info,
        "ids": games["id"].astype(int).tolist(),
    })
    print(f"{vecs.shape[0]:,} x {vecs.shape[1]} in {elapsed:.0f}s -> {npy}")


if __name__ == "__main__":
    main()
