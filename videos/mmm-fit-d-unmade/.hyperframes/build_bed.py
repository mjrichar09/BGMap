"""Build the continuous music bed: take 11 part A's opening, then two sustained takes from the same
prompt family, joined by long equal-power crossfades centred on story turns, loudness-matched.
SECTIONS: (file, offset into the file where the section's audio starts, gain dB). SEAMS: centre times."""
import json, subprocess
import numpy as np, soundfile as sf
XF = 4.0
SECTIONS = [("assets/bgm/sections/A_11.wav", 0.0, 0.0), ("assets/bgm/sections/C_11.wav", 0.0, 0.0), ("assets/bgm/sections/C_47.wav", 1.0, -3.0)]
meta = json.load(open("audio_meta.json", encoding="utf-8"))
starts, t = [], 0.0
for v in meta["voices"]:
    starts.append(t); t += v["duration_s"]
total = t + 0.4
SEAMS = [12.5, starts[7]]                 # mid-GoodFellas (before part A fades) and "Want something original?"
edges = [0.0] + SEAMS + [total]
out = None
for k, (path, offset, gain) in enumerate(SECTIONS):
    y, sr = sf.read(path, always_2d=True)
    a = edges[k] - (XF / 2 if k else 0)            # timeline start, including the fade-in overlap
    b = edges[k + 1] + (XF / 2 if k < len(SECTIONS) - 1 else 0)
    seg = y[int(offset * sr): int((offset + b - a) * sr)] * 10 ** (gain / 20)
    n = len(seg); env = np.ones(n); x = int(XF * sr)
    if k: env[:x] = np.sin(np.linspace(0, np.pi / 2, x))                 # equal-power fade in
    if k < len(SECTIONS) - 1: env[-x:] = np.cos(np.linspace(0, np.pi / 2, x))
    else: f = int(3.0 * sr); env[-f:] *= np.linspace(1, 0, f)            # final fade out under the URL
    if out is None: out = np.zeros((int(total * sr) + sr, 2))
    i = int(a * sr); out[i:i + n] += seg[: len(out) - i] * env[:, None][: len(out) - i]
    print(f"section {k + 1}: {a:6.2f}s to {b:6.2f}s from {path.split('/')[-1]} @ {offset}s ({gain:+} dB)")
out = out[: int(total * sr)]
sf.write("assets/bgm/track.wav", out / max(1.0, np.abs(out).max() / 0.95), sr)
r = [20 * np.log10(np.sqrt(np.mean(out[i:i + sr // 2] ** 2)) + 1e-9) for i in range(0, len(out) - sr // 2, sr // 2)]
print(f"track.wav {total:.2f}s; quietest half-second {min(r[2:-6]):.0f} dB, median {np.median(r):.0f} dB")

# Leveler: a slow (2 s) gain curve that lifts quiet stretches toward the median, at most +6 dB,
# leaving the first second and the final 3.5 s fade untouched. It smooths the dips where a take
# starts its own fade inside a crossfade.
y, sr = sf.read("assets/bgm/track.wav", always_2d=True)
hop = sr // 10
rms = np.array([np.sqrt(np.mean(y[i:i + hop] ** 2)) + 1e-9 for i in range(0, len(y), hop)])
db = 20 * np.log10(rms); target = np.median(db)
gain = np.clip(target - db, 0, 6)
k = 20; gain = np.convolve(np.pad(gain, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]
t = np.arange(len(gain)) * hop / sr
gain[(t < 1.0) | (t > len(y) / sr - 3.5)] = 0
g = 10 ** (np.interp(np.arange(len(y)), np.arange(len(gain)) * hop, gain) / 20)
y = y * g[:, None]
sf.write("assets/bgm/track.wav", y / max(1.0, np.abs(y).max() / 0.95), sr)
r = [20 * np.log10(np.sqrt(np.mean(y[i:i + sr // 2] ** 2)) + 1e-9) for i in range(0, len(y) - sr // 2, sr // 2)]
print(f"levelled: quietest half-second (excluding ends) {min(r[2:-8]):.0f} dB, median {np.median(r):.0f} dB")
