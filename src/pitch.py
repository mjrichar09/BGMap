"""Embed new text (pitches, candidate plots) into the same space as the map's films.

The films' vectors may come from masked text (src.mask: names, genre and medium words out) and have
directions erased (src.erase). New text has to go through the same steps, or it lands somewhere films
never could. This reads the embedding's metadata and repeats them:
    masked text column -> names masked with the same NER model and common-entity list, genre and medium
                          words stripped (no keywords or tagline: a pitch has neither)
    erased            -> the same directions projected out
then normalizes.

    from src.pitch import embed_texts
    vecs = embed_texts(base, meta, ["Title. Plot ...", ...])
"""

import json

import numpy as np


def mask_texts(base, texts):
    import torch
    from transformers import pipeline

    from src.mask import NER_MODEL, mask_text, strip_genre, widen

    common = set(json.loads((base / "mask_common.json").read_text(encoding="utf-8")))
    nlp = pipeline("token-classification", model=NER_MODEL, aggregation_strategy="first", device=0, dtype=torch.float16, stride=64)
    out = []
    for text, ents in zip(texts, nlp(list(texts), batch_size=16)):
        spans = []
        for e in ents:
            s, t = widen(text, e["start"], e["end"])
            if spans and spans[-1][2] == e["entity_group"] and s <= spans[-1][1] + 1:
                spans[-1][1] = max(spans[-1][1], t)
            elif not spans or s >= spans[-1][1]:
                spans.append([s, t, e["entity_group"]])
        masked, _ = mask_text(text, [tuple(x) for x in spans], common)
        out.append(strip_genre(masked))
    return out


def embed_texts(base, meta, texts):
    """texts: 'Title. Plot' strings. Returns unit vectors in the embedding described by `meta`."""
    import torch
    from sentence_transformers import SentenceTransformer

    if str(meta.get("text_column", "")).startswith("plot_masked"):
        texts = mask_texts(base, [t.split(". ", 1)[1] if ". " in t else t for t in texts])  # films are embedded without titles
    model = SentenceTransformer(meta["model"], device="cuda", model_kwargs={"torch_dtype": torch.float16})
    prompt = f"Instruct: {meta['instruct']}\nQuery: " if meta.get("instruct") else None
    v = model.encode(list(texts), normalize_embeddings=True, prompt=prompt).astype(np.float64)
    if meta.get("erased"):
        name = meta["erased"]["file"]
        for w in np.load(base / "embeddings" / name).astype(np.float64):
            v = v - np.outer(v @ w, w)
    return (v / np.linalg.norm(v, axis=1, keepdims=True)).astype(np.float32)
