"""Add "this film is here" overlays to a map frame: when a film is named, a ring pulses on its marker
in the map footage and a thin line draws from its poster to the marker, both following the marker
frame by frame (positions tracked from the capture's camera path, assets/data/track_<clip>.json).

    python add_marker_tracks.py FRAME.html TRACK.json FRAME_ID 'JSON [[cue_s, anchor_x, anchor_y], ...]'

One entry per film, in the track file's film order; anchor = the poster's top-centre in the frame.
Idempotent: a previous overlay (marked by data-marker-tracks) is replaced.
"""
import json
import pathlib
import re
import sys

frame_path, track_path, frame_id, spec = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
track = json.loads(pathlib.Path(track_path).read_text(encoding="utf-8"))
fps = track["fps"]
assert len(spec) == len(track["films"])

films = [{"name": f["name"], "cue": cue, "ax": ax, "ay": ay, "pts": f["pts"]} for f, (cue, ax, ay) in zip(track["films"], spec)]
uid = re.sub(r"[^a-z0-9]", "", frame_id.lower())

svg = f'<svg data-marker-tracks="{uid}" ' \
      f'style="position:absolute;left:0;top:0;width:1080px;height:1080px;z-index:60;pointer-events:none;overflow:visible" viewBox="0 0 1080 1080">' + "".join(
    f'<line id="mt{uid}-l{k}" stroke="#FFB547" stroke-width="2.5" stroke-opacity="0.85" stroke-linecap="round" opacity="0"/>'
    f'<circle id="mt{uid}-p{k}" r="14" fill="none" stroke="#FFB547" stroke-width="3" opacity="0"/>'
    f'<circle id="mt{uid}-r{k}" r="17" fill="none" stroke="#FFB547" stroke-width="3" opacity="0"/>'
    for k in range(len(films))) + "</svg>"

script = f"""<script data-marker-tracks="{uid}">
(function () {{
  // Poster-to-marker lines and pulsing rings that follow each named film's marker in the footage.
  var tl = window.__timelines["{frame_id}"], FPS = {fps}, FILMS = {json.dumps([{k: f[k] for k in ("name", "cue", "ax", "ay", "pts")} for f in films])};
  var q = function (id) {{ return document.getElementById(id); }};
  var end = tl.duration();
  FILMS.forEach(function (f, k) {{
    var line = q("mt{uid}-l" + k), pulse = q("mt{uid}-p" + k), ring = q("mt{uid}-r" + k);
    var first = Math.round(f.cue * FPS), p0 = f.pts[first];
    tl.set([line, pulse, ring], {{ opacity: 0 }}, 0);
    // follow the marker every frame from the cue to the end of the frame
    for (var i = first; i < f.pts.length && i / FPS <= end; i++) {{
      var p = f.pts[i];
      tl.set(line, {{ attr: {{ x1: f.ax, y1: f.ay, x2: p[0], y2: p[1] }} }}, i / FPS);
      tl.set([pulse, ring], {{ attr: {{ cx: p[0], cy: p[1] }} }}, i / FPS);
    }}
    // line draws from the poster up to the marker
    var len = Math.hypot(p0[0] - f.ax, p0[1] - f.ay);
    tl.fromTo(line, {{ opacity: 1, attr: {{ "stroke-dasharray": len + 600, "stroke-dashoffset": len + 600 }} }},
              {{ attr: {{ "stroke-dashoffset": 0 }}, duration: 0.4, ease: "power3.out" }}, f.cue);
    // three pulses, then a steady ring
    for (var n = 0; n < 3; n++) {{
      tl.fromTo(pulse, {{ opacity: 0.95, attr: {{ r: 12 }} }}, {{ opacity: 0, attr: {{ r: 46 }}, duration: 0.55, ease: "power2.out" }}, f.cue + 0.15 + n * 0.45);
    }}
    tl.fromTo(ring, {{ opacity: 0, attr: {{ r: 30 }} }}, {{ opacity: 1, attr: {{ r: 17 }}, duration: 0.35, ease: "power3.out" }}, f.cue + 0.1);
  }});
}})();
</script>"""

s = pathlib.Path(frame_path).read_text(encoding="utf-8")
s = re.sub(r'<svg data-marker-tracks="[^"]*"[\s\S]*?</svg>', "", s)
s = re.sub(r'<script data-marker-tracks="[^"]*">[\s\S]*?</script>', "", s)
# The overlay goes inside the frame root (first child, drawn on top via z-index); the script after the frame's own.
last = s.rfind("</script>")
root = re.search(r'<div[^>]*data-composition-id="%s"[^>]*>' % re.escape(frame_id), s)
assert last > 0 and root
s = s[: last + len("</script>")] + "\n" + script + s[last + len("</script>"):]
s = s[: root.end()] + "\n" + svg + s[root.end():]
pathlib.Path(frame_path).write_text(s, encoding="utf-8")
print(f"{frame_id}: {len(films)} tracked films, overlay added")
