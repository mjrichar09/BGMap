"""Stretch chosen words of a voice line (pitch kept) to give them emphasis, with optional pauses after.
    python emphasize.py IN.wav OUT.wav 'JSON list of {start, end, tempo, gain, pause}'
Cut points snap to the quietest 10 ms within 60 ms of each requested time so cuts land between sounds."""
import json, subprocess, sys
import numpy as np, soundfile as sf
src, dst, edits = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
y, sr = sf.read(src)
mono = y if y.ndim == 1 else y.mean(1)
def snap(t):
    w = int(0.01 * sr); lo, hi = int((t - 0.06) * sr), int((t + 0.06) * sr)
    best = min(range(max(0, lo), min(len(mono) - w, hi), w // 2), key=lambda i: np.sum(mono[i:i + w] ** 2))
    return (best + w / 2) / sr
cuts, parts, t = [], [], 0.0
for e in edits:
    a, b = snap(e["start"]), snap(e["end"])
    parts.append((t, a, 1.0, 1.0, 0)); parts.append((a, b, e.get("tempo", 1.0), e.get("gain", 1.0), e.get("pause", 0))); t = b
parts.append((t, len(mono) / sr, 1.0, 1.0, 0))
inputs, chains = [], []
for k, (a, b, tempo, gain, pause) in enumerate(parts):
    inputs += ["-i", src]
    f = f"[{k}:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS"
    if tempo != 1.0: f += f",atempo={tempo}"
    if gain != 1.0: f += f",volume={gain}"
    if pause: f += f",apad=pad_dur={pause}"
    chains.append(f + f"[s{k}]")
graph = ";".join(chains) + ";" + "".join(f"[s{k}]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[out]"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", dst], check=True)
print("wrote", dst)
