"""Frame-accurate map captures for videos 2 and 3 (layouts, color modes, people highlights, time-lapse).
Serves data/movies/site with a hooked index.html (local only, the live site is untouched).

    python cap2.py CLIP OUT_MP4
"""
import math
import pathlib
import subprocess
import sys

from playwright.sync_api import sync_playwright

SITE = "http://localhost:8765/"
HTML = pathlib.Path("M:/Repositories/BGMap/data/movies/site/index.html").read_text(encoding="utf-8")
HOOK = """  window.__mm = { state, select, setView3d, fitView, pos, setHighlight, recolor, redraw, loadModel, switchModel, setYear,
    vp() { return deckgl.getViewports()[0]; },
    setView(v) { state.viewState = v; deckgl.setProps({ initialViewState: v }); redraw(); } };
  init();
})();"""
assert HTML.count("  init();\n})();") == 1
HTML = HTML.replace("  init();\n})();", HOOK)
# Capture-only: highlighted films draw larger (state.hlBoost) so a person's films read at video size.
PS = "  const pointSize = (i) => { const a = colors[i * 4 + 3]; return a <= 60 && a > 2 ? Math.min(radii[i], 3) * 1.6 : radii[i] * 2; };"
assert HTML.count(PS) == 1
HTML = HTML.replace(PS, "  const pointSize = (i) => { if (state.hlBoost && state.highlight && state.highlight.has(i)) return Math.max(radii[i] * 2, 14) * state.hlBoost; const a = colors[i * 4 + 3]; return a <= 60 && a > 2 ? Math.min(radii[i], 3) * 1.6 : radii[i] * 2; };")
# Capture-only: state.noLabels hides the map's region labels (for clips where the color is the story).
LB = 'id: "labels", data: visibleLabels(),'
assert HTML.count(LB) == 1
HTML = HTML.replace(LB, 'id: "labels", data: state.noLabels ? [] : visibleLabels(),')
NO_LABELS = {"orig", "truth", "revenue", "roi", "timelapse", "ridley", "statham", "spin", "end"}
CSS = ".card, #stubs, #tooltip, #suggest, #status { display: none !important; } #map { inset: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; }"
FPS = 30
TRUTH_SHIFT, TRUTH_Z, TRUTH_DX = 270, (-0.95, -0.8), 233

PERSON = """(name) => { const s = __mm.state; s.hlBoost = 2.2; const d = s.manifest.people.indexOf(name), g = s.films, hits = [];
  for (let i = 0; i < s.n; i++) if (g.dir[i].includes(d) || g.cast[i].includes(d)) hits.push(i);
  __mm.setHighlight(new Set(hits)); return hits; }"""

def lerp(a, b, t): return a + (b - a) * t
def ease(t): return 0.5 - 0.5 * math.cos(math.pi * t)

def frame(pg, v):
    pg.evaluate("(v) => __mm.setView(v)", v)
    pg.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

def base(pg):
    return pg.evaluate("() => __mm.fitView(__mm.state.models[__mm.state.model])")

def fit(pg, idx, fill=0.75):
    """Target and zoom framing a set of films (3D: like fitView's own rule)."""
    ps = pg.evaluate("(ix) => ix.map(i => __mm.pos(i))", idx)
    lo = [min(p[k] for p in ps) for k in range(3)]; hi = [max(p[k] for p in ps) for k in range(3)]
    span = max(max(h - l for h, l in zip(hi, lo)), 1e-3)
    return [(h + l) / 2 for h, l in zip(hi, lo)], math.log2(540 / span * fill)

def orbit(b, n, target, zoom, rot, rx=20, view3d=True):
    out = []
    for k in range(n):
        t = k / max(1, n - 1)
        v = {**b, "target": [lerp(a, c, ease(t)) for a, c in zip(target[0], target[1])], "zoom": lerp(zoom[0], zoom[1], ease(t)), "transitionDuration": 0}
        if view3d: v.update(rotationOrbit=lerp(rot[0], rot[1], t), rotationX=rx)
        out.append(v)
    return out

def plan(pg, name):
    """Return (list of view states, per-frame JS or None)."""
    if name in NO_LABELS:
        pg.evaluate("() => { __mm.state.noLabels = true; __mm.redraw(); }")
    b = base(pg); z0 = b["zoom"]; T = b["target"]
    if name == "spin":                                  # opening: the whole cloud turning (as video 1's spin.mp4)
        return orbit(b, 9 * FPS, [T, T], [z0 - 0.15, z0 + 0.2], [-60, -10]), None
    if name == "end":                                   # end card: wide slow orbit (as video 1's end.mp4)
        return orbit(b, 8 * FPS, [T, T], [z0 + 0.15, z0 - 0.1], [-10, 30]), None
    if name == "pca":                                   # PCA layout, 2D, axes drawn by the page
        pg.evaluate("async () => { await __mm.loadModel('axes'); __mm.switchModel('axes'); __mm.setView3d(false); }"); pg.wait_for_timeout(2500)
        b = base(pg); T = b["target"]
        return orbit(b, 12 * FPS, [T, T], [b["zoom"] - 0.15, b["zoom"] + 0.15], None, view3d=False), None
    if name in ("ridley", "statham", "cumberbatch"):
        who = {"ridley": "Ridley Scott", "statham": "Jason Statham", "cumberbatch": "Benedict Cumberbatch"}[name]
        hits = pg.evaluate(PERSON, who); pg.wait_for_timeout(1200)
        if name == "statham":                           # wide, then push toward where most of his films sit
            ps = pg.evaluate("(ix) => ix.map(i => __mm.pos(i))", hits)
            tgt = [sorted(p[k] for p in ps)[len(ps) // 2] for k in range(3)]
            return orbit(b, 12 * FPS, [T, tgt], [z0 - 0.1, z0 + 1.3], [-30, 10]), None
        # framed high and a little wider, so every named film sits above the frame's poster strip (y < 600 of 1080)
        Tu = [T[0], T[1] - 215 / 2 ** z0, T[2]]
        return orbit(b, 12 * FPS, [Tu, Tu], [z0 - 0.4, z0 - 0.2], [-40, 5]), None
    if name in ("orig", "revenue", "roi"):
        pg.evaluate("(c) => { __mm.state.colorBy = c; __mm.recolor(); __mm.redraw(); }", name); pg.wait_for_timeout(1200)
        return orbit(b, 14 * FPS, [T, T], [z0 - 0.15, z0 + 0.2], [-50, 0]), None
    if name == "truth":                                 # the five most original popular films, highlighted
        idx = pg.evaluate("""(ns) => { const f = __mm.state.films, out = [];
            ns.forEach(([n, y]) => { for (let i = 0; i < f.name.length; i++) if (f.name[i] === n && f.year[i] === y) out.push(i); });
            __mm.state.colorBy = 'orig'; __mm.state.hlBoost = 2.2; __mm.setHighlight(new Set(out)); return out; }""",
            [["The King's Speech", 2010], ["The Social Network", 2010], ["The Big Short", 2015], ["Hidden Figures", 2016], ["The Founder", 2016]])
        pg.wait_for_timeout(1200)
        tgt, zf = fit(pg, idx, 0.55)
        # framed high and wide, so the starred films sit above the frame's poster row (y < 530 of 1080)
        Tu = [T[0] - TRUTH_DX / 2 ** z0, T[1] - TRUTH_SHIFT / 2 ** z0, T[2]]
        return orbit(b, 10 * FPS, [Tu, Tu], [z0 + TRUTH_Z[0], z0 + TRUTH_Z[1]], [-20, 10]), None
    if name == "timelapse":                             # films appear year by year, 1950 to 2025
        n = 7 * FPS; views = orbit(b, n, [T, T], [z0 - 0.1, z0 + 0.1], [-40, 0])   # 7.0s: frame 7 of video 3
        years = [round(lerp(1950, 2025, k / (n - 1))) for k in range(n)]
        return views, years
    raise SystemExit(f"unknown clip {name}")

def main(name, out):
    tmp = pathlib.Path(out).with_suffix("")
    tmp.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 540, "height": 540}, device_scale_factor=2, color_scheme="dark")
        pg.route(SITE, lambda r: r.fulfill(body=HTML, content_type="text/html; charset=utf-8"))
        pg.goto(SITE); pg.wait_for_selector("#status", state="hidden", timeout=90000)
        pg.add_style_tag(content=CSS); pg.evaluate("() => window.dispatchEvent(new Event('resize'))"); pg.wait_for_timeout(1500)
        views, years = plan(pg, name)
        if STILL:
            views = [views[0], views[len(views) // 2], views[-1]]; years = [years[0], years[len(years) // 2], years[-1]] if years else None
        last = None
        for k, v in enumerate(views):
            if years and years[k] != last:
                pg.evaluate("(y) => __mm.setYear(y)", years[k]); last = years[k]
            frame(pg, v); pg.screenshot(path=str(tmp / f"{k:04d}.png"))
        b.close()
    if STILL:
        print(name, "stills in", tmp); return
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "%04d.png"), "-c:v", "libx264", "-crf", "16",
                    "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
    for f in tmp.glob("*.png"): f.unlink()
    tmp.rmdir()
    print(name, len(views), "frames ->", out)

def track(name, out, films):
    """Screen position (1080px canvas) of each named film in every frame of a clip's camera path."""
    import json
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 540, "height": 540}, device_scale_factor=2, color_scheme="dark")
        pg.route(SITE, lambda r: r.fulfill(body=HTML, content_type="text/html; charset=utf-8"))
        pg.goto(SITE); pg.wait_for_selector("#status", state="hidden", timeout=90000)
        pg.add_style_tag(content=CSS); pg.evaluate("() => window.dispatchEvent(new Event('resize'))"); pg.wait_for_timeout(1500)
        views, _ = plan(pg, name)
        idx = pg.evaluate("""(fs) => fs.map(([n, y]) => { const f = __mm.state.films;
            for (let i = 0; i < f.name.length; i++) if (f.name[i] === n && f.year[i] === y) return i; return -1; })""", films)
        assert -1 not in idx, (films, idx)
        pts = []
        for v in views:
            frame(pg, v)
            pts.append(pg.evaluate("(ix) => ix.map(i => { const p = __mm.vp().project(__mm.pos(i)); return [Math.round(p[0] * 20) / 10, Math.round(p[1] * 20) / 10]; })", idx))
        b.close()
    data = {"fps": FPS, "films": [{"name": n, "year": y, "pts": [f[k] for f in pts]} for k, (n, y) in enumerate(films)]}
    pathlib.Path(out).write_text(json.dumps(data), encoding="utf-8")
    print(name, len(pts), "frames tracked ->", out)

STILL = len(sys.argv) > 3 and sys.argv[3] == "still"
TRACKS = {
    "ridley": [["Alien", 1979], ["Gladiator", 2000], ["Black Hawk Down", 2001], ["The Martian", 2015]],
    "statham": [["Crank", 2006], ["The Transporter", 2002], ["The Expendables", 2010]],
    "truth": [["The King's Speech", 2010], ["The Social Network", 2010], ["The Big Short", 2015], ["Hidden Figures", 2016]],
}
if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[3] == "track":
        track(sys.argv[1], sys.argv[2], TRACKS[sys.argv[1]])
    else:
        main(sys.argv[1], sys.argv[2])
