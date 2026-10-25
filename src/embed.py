"""Stage 4 (shared): embed a domain's items.parquet text column.

Texts are sorted by token length and batched by a token budget rather than
a fixed count, so the longest texts don't run the GPU out of memory and the
short ones aren't padded out.

Writes data/<domain>/embeddings/<model>__<text column>.npy (float16, unit
length, rows in items.parquet order) and a .json beside it with the model,
date and the ids in row order.

    python -m src.embed --domain movies --model qwen3 --text text_plot
    python -m src.embed --domain movies --model bge --text text
"""

import argparse
import datetime as dt
import json
import time

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.common import domain_dir

MODELS = {
    "qwen3": {"name": "Qwen/Qwen3-Embedding-0.6B", "max_tokens": 4096},
    "bge": {"name": "BAAI/bge-base-en-v1.5", "max_tokens": 512},
}


def token_batches(lengths: np.ndarray, budget: int) -> list[np.ndarray]:
    """Group row indices, longest first, so each batch's padded size fits the budget."""
    order = np.argsort(-lengths, kind="stable")
    batches, start = [], 0
    while start < len(order):
        size = max(1, budget // max(1, lengths[order[start]]))  # first row is the batch's longest
        batches.append(order[start : start + size])
        start += size
    return batches


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--model", default="qwen3", choices=MODELS)
    ap.add_argument("--text", default="text", help="items.parquet column to embed")
    ap.add_argument("--token-budget", type=int, default=32768, help="padded tokens per batch")
    ap.add_argument("--limit", type=int, help="only embed the first N rows (for testing)")
    ap.add_argument(
        "--instruct",
        help="task instruction prepended to every text, for instruction-tuned models like Qwen3; "
        "adds __inst to the output name",
    )
    ap.add_argument(
        "--no-title",
        action="store_true",
        help="drop the leading '<name>. ' from each text, so same-named items aren't pulled together; "
        "adds __notitle to the output name",
    )
    args = ap.parse_args()

    spec = MODELS[args.model]
    base = domain_dir(args.domain)
    items = pd.read_parquet(base / "items.parquet", columns=["id", "name", args.text])
    if args.limit:
        items = items.head(args.limit)
    texts = items[args.text].fillna("").tolist()
    if args.no_title:
        # Items with no description are just their name; keep that rather than embed nothing.
        texts = [t[len(n) + 2 :] if t.startswith(f"{n}. ") else t for t, n in zip(texts, items["name"])]
    prompt = f"Instruct: {args.instruct}\nQuery: " if args.instruct else None

    model = SentenceTransformer(spec["name"], device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = spec["max_tokens"]

    lengths = np.array(
        [len(ids) for ids in model.tokenizer([(prompt or "") + t for t in texts], add_special_tokens=True)["input_ids"]]
    )
    truncated = int((lengths > spec["max_tokens"]).sum())
    lengths = np.minimum(lengths, spec["max_tokens"])
    print(f"{len(texts):,} texts, {lengths.sum():,} tokens, {truncated:,} truncated at {spec['max_tokens']}")

    out = np.zeros((len(texts), model.get_embedding_dimension()), dtype=np.float16)
    start = time.time()
    for batch in tqdm(token_batches(lengths, args.token_budget), unit="batch"):
        vecs = model.encode([texts[i] for i in batch], batch_size=len(batch), normalize_embeddings=True, prompt=prompt)
        out[batch] = vecs.astype(np.float16)
    elapsed = time.time() - start

    emb_dir = base / "embeddings"
    emb_dir.mkdir(exist_ok=True)
    name = f"{args.model}__{args.text}" + ("__inst" if args.instruct else "") + ("__notitle" if args.no_title else "")
    np.save(emb_dir / f"{name}.npy", out)
    meta = {
        "model": spec["name"],
        "text_column": args.text,
        "instruct": args.instruct,
        "no_title": args.no_title,
        "max_tokens": spec["max_tokens"],
        "truncated": truncated,
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "seconds": round(elapsed),
        "ids": items["id"].tolist(),
    }
    (emb_dir / f"{name}.json").write_text(json.dumps(meta), encoding="utf-8")
    print(f"Wrote {out.shape} to {emb_dir / name}.npy in {elapsed / 60:.1f} min")


if __name__ == "__main__":
    main()
