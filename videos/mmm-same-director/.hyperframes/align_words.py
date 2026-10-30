"""Word timings for each voice line: Whisper word timestamps, with the words themselves taken from
SCRIPT.md (so captions show the script's exact spelling), matched in order by difflib."""
import json, re, difflib, whisper
script = open("SCRIPT.md", encoding="utf-8").read()
lines = {int(m.group(1)): " ".join(m.group(2).split()) for m in re.finditer(r"## Line \d+ — .*?\(Frame (\d+)\)\n(?:.*\n)*?\n((?:    .+\n?)+)", script)}
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
model = whisper.load_model("turbo", device="cuda")
meta = json.load(open("audio_meta.json", encoding="utf-8"))
for v in meta["voices"]:
    text = lines[v["frame"]]
    res = model.transcribe(v["path"], word_timestamps=True, language="en", initial_prompt=text)
    heard = [w for s in res["segments"] for w in s["words"]]
    # Voice-only respellings (fixes for the TTS) show as the real words in captions.
    DISPLAY = {"red": "read", "moovees.": "movies.", "twenty-tens,": "2010s,", "Staythum's": "Statham's", "Staythum,": "Statham,"}
    ours = [DISPLAY.get(w, w) for w in text.split()]
    sm = difflib.SequenceMatcher(a=[norm(w) for w in ours], b=[norm(w["word"]) for w in heard], autojunk=False)
    times = [None] * len(ours)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n): times[a + k] = (heard[b + k]["start"], heard[b + k]["end"])
    # fill unmatched words (e.g. "2010s" vs "twenty tens") by interpolating between neighbours
    for k, t in enumerate(times):
        if t is None:
            prev = next((times[j][1] for j in range(k - 1, -1, -1) if times[j]), v.get("lead_s", 0))
            nxt = next((times[j][0] for j in range(k + 1, len(times)) if times[j]), prev + 0.4)
            gap = [j for j in range(k, len(times)) if times[j] is None and (j == k or times[j - 1] is None)]
            span = (nxt - prev) / max(1, len(gap)); times[k] = (prev, prev + span)
    v["words"] = [{"id": f"{v['frame']:02d}-{k}", "text": w, "start": round(s, 3), "end": round(e, 3)} for k, (w, (s, e)) in enumerate(zip(ours, times))]
    print(v["frame"], f"{sum(1 for w in heard)} heard / {len(ours)} script;", " ".join(f"{w['text']}@{w['start']}" for w in v["words"][:6]))
json.dump(meta, open("audio_meta.json", "w", encoding="utf-8"), indent=2)
