"""Put each SFX cue on its word: offsets come from the word timings (frame-local seconds).
CUES: frame -> list of (file stem, word to land on or a fixed second, lead-in seconds, volume)."""
import json
CUES = {1: [("click", 0.0, 0, 0.45), ("impact-bass-1", "films.", 0, 0.35)],
        3: [("typing", 0.0, 0, 0.25), ("whoosh-short", "neighbors:", 0.15, 0.3)],
        4: [("whoosh", 0.0, 0, 0.35), ("click-soft", "map.", 0, 0.35)],
        5: [("pop", "Hollywood", 0, 0.3), ("impact-bass-2", "ninety-three", 0, 0.35)],
        6: [("whoosh-short", "idea.", 0.1, 0.3), ("impact-bass-1", "Same", 0, 0.3)],
        7: [("impact-bass-2", "Dracula.", 0, 0.4), ("click-soft", "Thirty-two", 0, 0.3)],
        8: [("riser", "Roman", 1.6, 0.3), ("ping", "nineteen", 0, 0.3)],
        9: [("impact-bass-1", "Go", 0, 0.35)]}
meta = json.load(open("audio_meta.json", encoding="utf-8"))
words = {v["frame"]: v["words"] for v in meta["voices"]}
out = []
for s in meta["sfx"]:
    stem = s["file"].split("/")[-1].rsplit(".", 1)[0]
    for name, at, lead, vol in CUES.get(s["frame"], []):
        if name == stem:
            t = at if isinstance(at, float) else next(w["start"] for w in words[s["frame"]] if w["text"] == at)
            s["offset_s"], s["volume"] = round(max(0.0, t - lead), 3), vol
            CUES[s["frame"]].remove((name, at, lead, vol)); break
    out.append(s); print(s["frame"], stem, s["offset_s"], s["volume"])
meta["sfx"] = out
json.dump(meta, open("audio_meta.json", "w", encoding="utf-8"), indent=2)
