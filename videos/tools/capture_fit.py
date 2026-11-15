"""Frame-accurate vertical (1080x1920) map captures for the four fit shorts (videos/mmm-fit-*).
Serves data/movies/site on http://localhost:8766 (start `python -m http.server 8766` there first) with a hooked
index.html (local only; the live site is untouched).

    python tools/capture_fit.py CLIP OUT_MP4 [SECONDS] [still]

CLIP: c_stills (OUT is a folder: short C's filter states as PNGs), fit_box (3D fit plot, colored by box office vs. its plot), fit_2d (2D fit plot: predicted rating across,
predicted box office up), gaps (3D fit plot with the unmade ideas as rings), end (story map, wide slow orbit).
"""
import math
import pathlib
import subprocess
import sys

from playwright.sync_api import sync_playwright

SITE = "http://localhost:8766/"
HTML = pathlib.Path("M:/Repositories/BGMap/data/movies/site/index.html").read_text(encoding="utf-8")
HOOK = """  window.__mm = { state, fitView, setView3d, switchModel, loadModel, recolor, redraw, setHighlight, pos,
    vp() { return deckgl.getViewports()[0]; },
    setView(v) { state.viewState = v; deckgl.setProps({ initialViewState: v }); redraw(); },
    // Paint every film one colour, then light whole story regions (by label) in their own colours, as a filter would.
    paint(base, groups) { const m = state.models[state.model], ids = groups.map((g) => new Set(m.labels.filter((d) => g.labels.includes(d.label)).map((d) => d.id)));
      const c = new Uint8ClampedArray(state.n * 4);
      for (let i = 0; i < state.n; i++) { let col = base; ids.forEach((s, k) => { if (s.has(m.cluster[i])) col = groups[k].c; }); c.set(col, i * 4); }
      colors = c; redraw(); return ids.map((s) => s.size); } };
  init();
})();"""
assert HTML.count("  init();\n})();") == 1
HTML = HTML.replace("  init();\n})();", HOOK)
# Only the map: every panel, bar and pill is hidden, the map fills the window.
CSS = "body > *:not(#map) { display: none !important; } #map { inset: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; }"
FPS = 30
W, H = 540, 960     # x2 device scale = 1080x1920


def lerp(a, b, t): return a + (b - a) * t
def ease(t): return 0.5 - 0.5 * math.cos(math.pi * t)


def frame(pg, v):
    pg.evaluate("(v) => __mm.setView(v)", v)
    pg.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")


def orbit(b, n, zoom, rot=None, rx=None, target=None):
    out = []
    for k in range(n):
        t = k / max(1, n - 1)
        v = {**b, "zoom": lerp(zoom[0], zoom[1], ease(t)), "transitionDuration": 0}
        if target: v["target"] = [lerp(a, c, ease(t)) for a, c in zip(target[0], target[1])]
        if rot: v["rotationOrbit"] = lerp(rot[0], rot[1], t)
        if rx: v["rotationX"] = lerp(rx[0], rx[1], ease(t))
        out.append(v)
    return out


def setup_fit(pg, view3d, color, rings):
    pg.evaluate("""async ([v3, color, rings]) => {
        const s = __mm.state; await __mm.loadModel('fit');
        if (!rings) s.models.fit.proposals = null;      // the unmade ideas only where the short is about them
        __mm.switchModel('fit'); __mm.setView3d(v3);
        if (color) { s.colorBy = color; __mm.recolor(); }
        __mm.redraw(); }""", [view3d, color, rings])
    pg.wait_for_timeout(2500)
    return pg.evaluate("() => __mm.fitView(__mm.state.models.fit)")


def plan(pg, name, secs):
    n = round(secs * FPS)
    if name == "fit_box":
        b = setup_fit(pg, True, "missB", False); z = b["zoom"]
        return orbit(b, n, [z + 0.15, z + 0.35], rot=[-45, -20], rx=[22, 16])
    if name == "fit_2d":
        b = setup_fit(pg, False, "rating", False); z = b["zoom"]
        b["target"][1] -= 200 / 2 ** z      # the page frames the plot at the bottom; lift it to the middle of the tall frame
        return orbit(b, n, [z - 0.02, z + 0.06])
    if name == "gaps":
        b = setup_fit(pg, True, None, True); z = b["zoom"]
        return orbit(b, n, [z + 0.25, z + 0.4], rot=[-20, 5], rx=[20, 16])
    if name == "end":
        pg.evaluate("() => { __mm.setView3d(true); }"); pg.wait_for_timeout(1500)
        b = pg.evaluate("() => __mm.fitView(__mm.state.models[__mm.state.model])"); z = b["zoom"]
        return orbit(b, n, [z + 0.2, z - 0.05], rot=[-10, 30])
    raise SystemExit(f"unknown clip {name}")


# Short C: the 2D fit plot held still while story regions light up, one still per filter state.
DIM, CREAM = [125, 112, 98, 46], [243, 230, 208, 58]
LOVED, MONEY, LOW = [255, 181, 71, 255], [95, 211, 181, 255], [240, 52, 72, 255]
C_GROUPS = {"loved": [("concert, concert film", LOVED), ("nature documentary, nature", LOVED), ("music documentary, biography", LOVED)],
            "money": [("superhero, based on comic", MONEY), ("wuxia, martial arts", MONEY), ("ancient rome, roman empire", MONEY)],
            "low": [("gore, cannibal", LOW), ("psychopath, murder", LOW), ("anthology, horror anthology", LOW)]}
C_STATES = {"base": []}
for k in range(1, 4):
    C_STATES[f"loved{k}"] = C_GROUPS["loved"][:k]
    C_STATES[f"money{k}"] = C_GROUPS["loved"] + C_GROUPS["money"][:k]
    C_STATES[f"low{k}"] = C_GROUPS["low"][:k]


def c_stills(pg, outdir):
    b = setup_fit(pg, False, "rating", False); z = b["zoom"]
    b["target"][1] -= 200 / 2 ** z
    frame(pg, {**b, "zoom": z + 0.02, "transitionDuration": 0})
    states = {**C_STATES, "all": None}
    for name, groups in states.items():
        base = CREAM if groups is None else DIM
        sizes = pg.evaluate("([b, g]) => __mm.paint(b, g)", [base, [{"labels": [l], "c": c} for l, c in (groups or [])]])
        pg.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(pathlib.Path(outdir) / f"{name}.png")); print(name, sizes)


def main(name, out, secs, still):
    tmp = pathlib.Path(out).with_suffix("")
    if name != "c_stills": tmp.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2, color_scheme="dark")
        pg.route(SITE, lambda r: r.fulfill(body=HTML, content_type="text/html; charset=utf-8"))
        pg.goto(SITE); pg.wait_for_selector("#loader", state="hidden", timeout=120000)
        pg.add_style_tag(content=CSS); pg.evaluate("() => window.dispatchEvent(new Event('resize'))"); pg.wait_for_timeout(1500)
        if name == "c_stills":
            pathlib.Path(out).mkdir(parents=True, exist_ok=True); c_stills(pg, out); b.close(); return
        views = plan(pg, name, secs)
        if still:
            views = [views[0], views[len(views) // 2], views[-1]]
        for k, v in enumerate(views):
            frame(pg, v); pg.screenshot(path=str(tmp / f"{k:04d}.png"))
        b.close()
    if still:
        print(name, "stills in", tmp); return
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "%04d.png"), "-c:v", "libx264", "-crf", "16",
                    "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
    for f in tmp.glob("*.png"): f.unlink()
    tmp.rmdir()
    print(name, len(views), "frames ->", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 8.0, len(sys.argv) > 4 and sys.argv[4] == "still")
