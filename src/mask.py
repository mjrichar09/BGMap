"""Masked plot texts: the story without its names, brands or genre labels, for embedding.

The plot embedding knows names. A famous one ("Avengers", "Hogwarts") predicts box office better than any
story does (src/fit.py), and sequels cluster by their shared names as much as by their stories. Masking
gives an embedding of the story alone:

  ner    Named entities in every plot (dslim/bert-base-NER on the GPU, ~10 min), widened to whole words,
         saved to data/<domain>/ner.parquet.
  build  data/<domain>/texts.parquet with masked text columns (src.embed --items texts.parquet):
         plot_masked       the plot (no title) with
           - people's names as Person A, Person B, ... (consistent within a film; a surname alone maps
             to the same person as the full name),
           - other named things (groups, places, things) as Group A, Place A, Thing A, unless they're
             common across kinds of story: in RARE+ films spread over SPREAD+ fine clusters (Paris, FBI,
             Nazi, Earth). Franchise vocabulary (Avengers, Jedi, Hogwarts) repeats a lot, but only inside
             its franchise's clusters, so it's masked. Nationalities and ethnicities are always kept,
           - genre labels removed ("a 2005 American horror film" -> "a 2005 American film"): unambiguous
             ones (horror, sci-fi, slasher, comedy, thriller, documentary, ...) always, ambiguous ones
             (action, western, drama, war, ...) only in genre phrases ("an action comedy").
           - the medium removed: animation is a format, not a kind of story (animated, anime, cartoon,
             stop-motion, CGI, ...), so it shouldn't decide where a film goes.
         plot_masked_meta  the same plus the film's TMDB keywords (minus genre, medium and studio words and masked names)
             and tagline (masked the same way); franchise keywords (sequel, ... universe) are dropped.

    python -m src.mask --domain movies ner
    python -m src.mask --domain movies build
"""

import argparse
import json
import re
from collections import Counter

import pandas as pd

from src.common import domain_dir

RARE = 20
SPREAD = 8
SPREAD_MAP = "qwen3__text_plot__inst__nn30_md0.05"
DEMONYM = re.compile(r"^[A-Z][a-z]+(?:[- ][A-Z][a-z]+)*(?:an|ian|ese|ish|ic|i|ch|ean|ite)s?$")  # Irish, Italian-American, Japanese
MEDIUM = re.compile(r"\b(?:computer[- ]animated|computer[- ]animation|stop[- ]motion|claymation|hand[- ]drawn|cel[- ]animated|"
                    r"animated|animations?|animators?|anime|manga|cartoons?|cartoonish|cgi)\b", re.I)
KW_MEDIUM = re.compile(r"anim|anime|manga|cartoon|stop motion|claymation|cgi|hand drawn|pixar|disney|dreamworks|ghibli|illumination", re.I)
KW_FRANCHISE = re.compile(r"universe|\(|sequel|prequel|spin[- ]?off|reboot|remake|franchise|collection|crossover", re.I)
NER_MODEL = "dslim/bert-base-NER"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TYPE_WORD = {"PER": "Person", "ORG": "Group", "LOC": "Place", "MISC": "Thing"}

GENRE_ALWAYS = (r"sci[- ]?fi|science[- ]fiction|rom[- ]?com|romantic comed(?:y|ies)|slasher|mockumentar(?:y|ies)|biopic|"
                r"docudrama|film[- ]noir|neo[- ]noir|comedy[- ]drama|black comedy|dark comedy|comed(?:y|ies)|comedic|"
                r"thrillers?|documentar(?:y|ies)|melodrama|horror")
GENRE_ADJ = (r"action|adventure|mystery|drama|dramatic|western|musical|fantasy|romance|romantic|war|crime|family|disaster|"
             r"spy|superhero|teen|sports?|heist|monster|martial[- ]arts|period|psychological|supernatural|erotic|historical|"
             r"epic|coming[- ]of[- ]age|animated|animation|zombie|vampire|creature|survival|buddy|road|independent|cult")
NOUNS = r"film|movie|picture|flick|feature|story|tale|series|genre|franchise|comed(?:y|ies)|thrillers?|drama|epic|romp|adventure"
GENRE_PHRASE = re.compile(rf"\b(?:(?:{GENRE_ALWAYS}|{GENRE_ADJ})[- ]+)+({NOUNS})\b", re.I)
GENRE_WORD = re.compile(rf"\b(?:{GENRE_ALWAYS})\b", re.I)
KW_GENRE = re.compile(rf"^(?:{GENRE_ALWAYS}|{GENRE_ADJ})(?: (?:{NOUNS}))?$", re.I)


def body(name, text):
    """The plot without its leading '<name>. ' (texts with no plot are just the name: keep nothing)."""
    text = text or ""
    return text[len(name) + 2:] if text.startswith(f"{name}. ") else ("" if text == name else text)


def widen(text, start, end):
    """Grow a span to whole words (the NER model sometimes tags part of a word: 'Than' in 'Thanos')."""
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "'-"):
        start -= 1
    while end < len(text) and (text[end].isalnum() or text[end] in "-"):
        end += 1
    return start, end


def ner(base):
    import torch
    from transformers import pipeline

    items = pd.read_parquet(base / "items.parquet", columns=["id", "name", "text_plot"])
    texts = [body(n, t) for n, t in zip(items["name"], items["text_plot"])]
    nlp = pipeline("token-classification", model=NER_MODEL, aggregation_strategy="first", device=0, dtype=torch.float16, stride=64)
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))   # similar lengths batch together
    spans = [None] * len(texts)
    for k in range(0, len(order), 512):
        idx = order[k:k + 512]
        for i, ents in zip(idx, nlp([texts[i] or "." for i in idx], batch_size=32)):
            out = []
            for e in ents:
                s, t = widen(texts[i], e["start"], e["end"])
                if out and out[-1][2] == e["entity_group"] and s <= out[-1][1] + 1:   # merge touching same-type pieces
                    out[-1][1] = max(out[-1][1], t)
                elif not out or s >= out[-1][1]:
                    out.append([s, t, e["entity_group"]])
            spans[i] = out
        print(f"  {min(k + 512, len(order)):,} / {len(order):,}")
    pd.DataFrame({"id": items["id"], "start": [[s[0] for s in x] for x in spans], "end": [[s[1] for s in x] for x in spans],
                  "type": [[s[2] for s in x] for x in spans]}).to_parquet(base / "ner.parquet")
    print(f"wrote {base / 'ner.parquet'}")


def strip_genre(text):
    text = MEDIUM.sub("", text)
    text = GENRE_PHRASE.sub(lambda m: m.group(1) if m.group(1).lower() in ("film", "movie", "picture", "flick", "feature", "story", "tale", "series", "franchise") else "film", text)
    text = re.sub(rf"\b(an?|the|this|that|his|her|their)\s+(?:{GENRE_ALWAYS})\b", lambda m: ("a" if m.group(1).lower() == "an" else m.group(1)) + " film", text, flags=re.I)
    text = GENRE_WORD.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", re.sub(r" +([,.;:])", r"\1", text)).strip()


def mask_text(text, spans, common):
    """Replace a film's entity spans: people always, other things unless common across kinds of story."""
    labels, counters, out, pos = {}, Counter(), [], 0
    rare_strings = {}
    for s, e, t in spans:
        word = text[s:e]
        key = word.lower()
        if t != "PER" and (key in common or DEMONYM.match(word)):
            continue
        # A surname alone is the same person as the full name seen earlier.
        lookup = key if t != "PER" else next((k for k in labels if k[0] == "PER" and (k[1] == key or k[1].endswith(" " + key) or key.endswith(" " + k[1]))), ("PER", key))[1]
        tag = (t, lookup)
        if tag not in labels:
            n = counters[t]; counters[t] += 1
            labels[tag] = f"{TYPE_WORD[t]} {LETTERS[n] if n < 26 else n + 1}"
        out.append(text[pos:s]); out.append(labels[tag]); pos = e
        rare_strings[key] = labels[tag]
    out.append(text[pos:])
    return "".join(out), rare_strings


def build(base):
    # Spread is measured on the first (unmasked) plot map, which the masked embedding was built from; pinned so
    # rebuilding gives the same texts whatever map src.gaps points at now.
    MAP = SPREAD_MAP

    items = pd.read_parquet(base / "items.parquet", columns=["id", "name", "text_plot", "keywords", "tagline"])
    spans = pd.read_parquet(base / "ner.parquet")
    cluster = pd.read_parquet(base / "maps" / f"{MAP}.parquet", columns=["id", "cluster_fine"]).set_index("id")["cluster_fine"].reindex(items["id"]).to_numpy()
    assert spans["id"].tolist() == items["id"].tolist()
    texts = [body(n, t) for n, t in zip(items["name"], items["text_plot"])]
    # Which entity strings are common across kinds of story: in RARE+ films over SPREAD+ fine clusters.
    df, where = Counter(), {}
    for text, st, en, cl in zip(texts, spans["start"], spans["end"], cluster):
        for k in {text[s:e].lower() for s, e in zip(st, en)}:
            df[k] += 1; where.setdefault(k, set()).add(cl)
    common = {k for k, n in df.items() if n >= RARE and len(where[k]) >= SPREAD}
    (base / "mask_common.json").write_text(json.dumps(sorted(common), ensure_ascii=False), encoding="utf-8")  # for src.pitch
    masked, meta = [], []
    for text, st, en, ty, kws, tag in zip(texts, spans["start"], spans["end"], spans["type"], items["keywords"], items["tagline"]):
        m, rare = mask_text(text, list(zip(st, en, ty)), common)
        m = strip_genre(m)
        masked.append(m)
        # Keywords and tagline: drop genre words, and mask the film's own masked names wherever they appear.
        def scrub(s):
            for k in sorted(rare, key=len, reverse=True):
                s = re.sub(rf"\b{re.escape(k)}\b", rare[k], s, flags=re.I)
            return s
        kw = [scrub(k) for k in (list(kws) if kws is not None else []) if not KW_GENRE.match(k) and not KW_FRANCHISE.search(k) and not KW_MEDIUM.search(k)]
        extra = []
        if kw:
            extra.append("Keywords: " + ", ".join(kw[:20]) + ".")
        if tag:
            extra.append("Tagline: " + strip_genre(scrub(tag)))
        meta.append(m + ("\n" + "\n".join(extra) if extra else ""))
    pd.DataFrame({"id": items["id"], "name": items["name"], "plot_masked": masked, "plot_masked_meta": meta}).to_parquet(base / "texts.parquet")
    changed = sum(a != b for a, b in zip(texts, masked))
    print(f"wrote {base / 'texts.parquet'}: {changed:,} of {len(texts):,} plots changed")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    ap.add_argument("stage", choices=["ner", "build"])
    args = ap.parse_args()
    base = domain_dir(args.domain)
    (ner if args.stage == "ner" else build)(base)


if __name__ == "__main__":
    main()
