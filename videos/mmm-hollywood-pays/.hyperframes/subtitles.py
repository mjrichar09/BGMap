"""Turn the karaoke captions into calm phrase subtitles.

Regroups the timed words in caption_groups.json into whole phrases (break at sentence ends and
colons, merge very short sentences into the next, cap at MAX_CHARS so a phrase fits two lines),
then patches compositions/captions.html: new GROUPS, no per-word highlighting, each phrase fades
in and out as one block, all words in cream. Run after every `captions.mjs build`.
"""
import json
import pathlib
import re

MAX_CHARS = 76        # about two lines at 40px in the caption card
MIN_SENTENCE = 12     # a sentence shorter than this joins the next one ("Same year. Same plot.")
FADE = 0.12

groups = json.load(open("caption_groups.json", encoding="utf-8"))["groups"]
words = [dict(w, frame=g["frame"]) for g in groups for w in g["words"]]

sentences, cur = [], []
def close():
    if cur: sentences.append(list(cur)); cur.clear()
for k, w in enumerate(words):
    nxt = words[k + 1] if k + 1 < len(words) else None
    if cur and w["frame"] != cur[-1]["frame"]:
        close()
    cur.append(w)
    text = " ".join(x["text"] for x in cur)
    end_sentence = re.search(r"[.?!]$", w["text"]) and len(text) >= MIN_SENTENCE
    colon = w["text"].endswith(":") and len(text) >= 30
    if end_sentence or colon or nxt is None or nxt["frame"] != w["frame"]:
        close()

def chars(ws): return len(" ".join(x["text"] for x in ws))
def split(ws):
    """Split a too-long sentence at the comma nearest its middle, else at the most balanced word break."""
    if chars(ws) <= MAX_CHARS or len(ws) < 2:
        return [ws]
    cuts = range(1, len(ws))
    commas = [i for i in cuts if ws[i - 1]["text"].endswith(",") and min(chars(ws[:i]), chars(ws[i:])) >= 25]
    best = min(commas or cuts, key=lambda i: abs(chars(ws[:i]) - chars(ws[i:])))
    return split(ws[:best]) + split(ws[best:])
phrases = [p for s in sentences for p in split(s)]

out = []
for k, ph in enumerate(phrases):
    start = max(0.0, ph[0]["start"] - 0.05)
    nxt = phrases[k + 1][0]["start"] - 0.05 if k + 1 < len(phrases) else ph[-1]["end"] + 1.0
    end = min(nxt, ph[-1]["end"] + 0.6)
    out.append({"id": f"caption-group-{k}", "frame": ph[0]["frame"], "start": round(start, 3), "end": round(end, 3),
                "text": " ".join(w["text"] for w in ph),
                "words": [{"id": f"caption-word-{k}-{i}", "text": w["text"], "start": w["start"], "end": w["end"]} for i, w in enumerate(ph)]})

p = pathlib.Path("compositions/captions.html")
s = p.read_text(encoding="utf-8")
s = re.sub(r"  var GROUPS = \[.*?\];\n", lambda m: "  var GROUPS = " + json.dumps(out, ensure_ascii=False) + ";\n", s, count=1, flags=re.S)

karaoke = re.search(r"      // group on/off — exactly one group visible at a time\n.*?\n    \}\);\n\n    // full-span anchor", s, flags=re.S)
calm = f"""      // whole phrase fades in and out as one block; no per-word states
      tl.fromTo(groupEl, {{ opacity: 0 }}, {{ opacity: 1, duration: {FADE}, ease: "power1.out" }}, start);
      tl.to(groupEl, {{ opacity: 0, duration: {FADE}, ease: "power1.in" }}, Math.max(start + {FADE}, end - {FADE}));
      tl.set(groupEl, {{ opacity: 0, visibility: "hidden" }}, end);
      tl.set(groupEl, {{ visibility: "visible" }}, start);
    }});

    // full-span anchor"""
if karaoke:
    s = s[: karaoke.start()] + calm + s[karaoke.end():]
    s = s.replace("      var end = isLast ? DURATION : Math.min(Number(next.start), Number(group.end) + 0.3);",
                  "      var end = Number(group.end);")

css = """
  /* Calm subtitles: every word cream, no highlight; up to two lines per phrase. */
  .caption-pill { max-width: 88%; padding: 16px 34px 18px; }
  .caption-line { font-size: 40px; line-height: 1.22; gap: 0 0.28em; }
  .caption-word, .caption-word.is-active, .caption-word.is-spoken { color: #F3E6D0; background: none; box-shadow: none; text-shadow: none; }
</style>
"""
# The captions use Work Sans; make sure its @font-face rules are present (from frame.md's font block).
if "font-family: 'Work Sans'" not in s:
    faces = pathlib.Path(".hyperframes/fontfaces.css").read_text(encoding="utf-8")
    ws = "".join(b + "}" + chr(10) for b in faces.split("}") if "'Work Sans'" in b)  # Work Sans @font-face rules
    s = s.replace("<style>", "<style>" + chr(10) + ws, 1)
if "Calm subtitles" not in s:
    s = s.replace("</style>\n\n<div\n  id=\"captions-root\"", css + "\n<div\n  id=\"captions-root\"", 1)
p.write_text(s, encoding="utf-8")
print(f"{len(out)} phrases")
for g in out:
    print(f"  {g['start']:6.2f}-{g['end']:6.2f}  {g['text']}")
