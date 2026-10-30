"""Post-assembly patch: move the hoisted frame videos to the start of #root so they paint UNDER the
frame layers (assemble-index appends them after the frames, which would cover the frame overlays).
Idempotent: run after every assemble-index."""
import pathlib, re
p = pathlib.Path("index.html"); s = p.read_text(encoding="utf-8")
vids = re.findall(r"\n      <video [\s\S]*?</video>\n", s)
for v in vids: s = s.replace(v, "\n", 1)
anchor = re.search(r'<div\s+id="root"[^>]*>\n', s)
s = s[: anchor.end()] + "".join(v.lstrip("\n") for v in vids) + "\n" + s[anchor.end():]
p.write_text(s, encoding="utf-8")
print(f"moved {len(vids)} videos under the frames")
