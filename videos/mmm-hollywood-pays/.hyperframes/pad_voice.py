"""Pad each voice line with lead/tail silence (the breathing room between frames) and update audio_meta.json.
PAD maps frame -> (lead, tail) seconds; frame starts and boundaries follow from these."""
import json, subprocess, sys
PAD = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
DEFAULT = (0.15, 0.35)
meta = json.load(open("audio_meta.json", encoding="utf-8"))
t = 0.0
for v in meta["voices"]:
    n = v["frame"]; lead, tail = PAD.get(str(n), DEFAULT)
    src, dst = f"assets/voice/raw/{n:02d}.wav", f"assets/voice/{n:02d}.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-af", f"adelay={int(lead * 1000)}:all=1,apad=pad_dur={tail}", dst], check=True)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dst], capture_output=True, text=True).stdout)
    v["path"], v["duration_s"], v["lead_s"] = dst, round(d, 3), lead
    print(f"frame {n}: start {t:6.2f}  speech {t + lead:6.2f}  dur {d:5.2f}")
    t += d
print(f"total {t:.2f}s")
json.dump(meta, open("audio_meta.json", "w", encoding="utf-8"), indent=2)
