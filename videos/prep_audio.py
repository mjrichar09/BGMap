"""After the voiceover is generated: pad lines, time every word, build the music bed, place SFX.
Run from a project folder:   python ../prep_audio.py CONFIG.json

CONFIG: {"pad": {"1": [lead, tail], ...}, "seam_frames": [frame numbers where the bed crossfades],
         "sfx": [[frame, "file stem", "word" | seconds, lead_in, volume], ...]}
Reuses the first video's helpers in .hyperframes/ (pad_voice, align_words, build_bed's bed method).
"""
import json
import pathlib
import subprocess
import sys

import numpy as np
import soundfile as sf

PY = sys.executable
cfg = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))

voice = pathlib.Path("assets/voice"); raw = voice / "raw"; raw.mkdir(exist_ok=True)
for f in voice.glob("0*.wav"):
    f.replace(raw / f.name)
subprocess.run([PY, ".hyperframes/pad_voice.py", json.dumps(cfg["pad"])], check=True)
subprocess.run([PY, ".hyperframes/align_words.py"], check=True)

meta = json.load(open("audio_meta.json", encoding="utf-8"))
starts, t = {}, 0.0
for v in meta["voices"]:
    starts[v["frame"]] = t; t += v["duration_s"]
total = t + 0.4

# Music bed: take 11 part A opening, then sustained takes C_11 and C_47, equal-power crossfades
# centred on story turns, a slow leveler, final fade under the end card (same method as video 1).
XF = 4.0
SECTIONS = [("assets/bgm/sections/A_11.wav", 0.0, 0.0), ("assets/bgm/sections/C_11.wav", 0.0, 0.0), ("assets/bgm/sections/C_47.wav", 1.0, -3.0)]
edges = [0.0, 12.5, starts[cfg["seam_frames"][0]], total]
out = np.zeros((int((total + 1) * 44100), 2))
for k, (path, offset, gain) in enumerate(SECTIONS):
    y, sr = sf.read(path, always_2d=True)
    a = edges[k] - (XF / 2 if k else 0); b = edges[k + 1] + (XF / 2 if k < 2 else 0)
    seg = y[int(offset * sr): int((offset + b - a) * sr)] * 10 ** (gain / 20)
    n = len(seg); env = np.ones(n); x = int(XF * sr)
    if k: env[:x] = np.sin(np.linspace(0, np.pi / 2, x))
    if k < 2: env[-x:] = np.cos(np.linspace(0, np.pi / 2, x))
    else: f = int(3.0 * sr); env[-f:] *= np.linspace(1, 0, f)
    i = int(a * sr); out[i:i + n] += seg[: len(out) - i] * env[: len(out) - i, None]
out = out[: int(total * 44100)]
hop = 4410
rms = np.array([np.sqrt(np.mean(out[i:i + hop] ** 2)) + 1e-9 for i in range(0, len(out), hop)])
db = 20 * np.log10(rms); gain = np.clip(np.median(db) - db, 0, 6)
gain = np.convolve(np.pad(gain, 20, mode="edge"), np.ones(41) / 41, mode="same")[20:-20]
tt = np.arange(len(gain)) * 0.1; gain[(tt < 1.0) | (tt > total - 3.5)] = 0
out = out * (10 ** (np.interp(np.arange(len(out)), np.arange(len(gain)) * hop, gain) / 20))[:, None]
sf.write("assets/bgm/track.wav", out / max(1.0, np.abs(out).max() / 0.95), 44100)

meta["bgm"] = {"path": "assets/bgm/track.wav", "volume": 0.27, "duration_s": round(total, 2),
               "query": "take 11 part A + sustained takes C_11, C_47 (Stable Audio Open, local)"}
meta["bgm_pending"] = False
words = {v["frame"]: v["words"] for v in meta["voices"]}
sfx = []
for frame, stem, at, lead, vol in cfg["sfx"]:
    t0 = at if isinstance(at, (int, float)) else next(w["start"] for w in words[frame] if w["text"].rstrip(".,?:") == at)
    sfx.append({"frame": frame, "file": f"assets/sfx/{stem}.mp3", "offset_s": round(max(0.0, t0 - lead), 3), "duration_s": 2.0, "volume": vol})
meta["sfx"] = sfx
json.dump(meta, open("audio_meta.json", "w", encoding="utf-8"), indent=2)
print(f"total {total:.2f}s; seams at 12.5 and {edges[2]:.2f}; {len(sfx)} sfx")
for v in meta["voices"]:
    print(f"F{v['frame']} start {starts[v['frame']]:.2f} ({v['duration_s']}s):", " ".join(f"{w['text']}@{w['start']:.2f}" for w in v["words"]))
