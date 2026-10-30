"""Copy the padded voice timings, word timings and the music bed into the engine's neutral sidecar
(audio_engine_meta.json), since audio.mjs fetch-sfx rebuilds audio_meta.json from it."""
import json
pl = json.load(open("audio_meta.json", encoding="utf-8"))
ne = json.load(open("audio_engine_meta.json", encoding="utf-8"))
BGM = {"path": "assets/bgm/track.wav", "volume": 0.27, "duration_s": 60.83,
       "query": "take 11 part A + sustained takes C_11, C_47 (Stable Audio Open, local)"}
by = {int(v["frame"]): v for v in pl["voices"]}
for v in ne["voices"]:
    p = by[int(v["id"])]
    v["path"], v["duration_s"], v["words"] = p["path"], p["duration_s"], p["words"]
ne["bgm"], ne["bgm_pending"] = dict(BGM), False
pl["bgm"], pl["bgm_pending"] = dict(BGM), False
json.dump(ne, open("audio_engine_meta.json", "w", encoding="utf-8"), indent=2)
json.dump(pl, open("audio_meta.json", "w", encoding="utf-8"), indent=2)
