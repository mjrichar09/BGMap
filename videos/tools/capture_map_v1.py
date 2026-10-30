"""Frame-accurate map captures for the video. Serves data/movies/site with a hooked index.html (local only).

    python cap.py stills OUTDIR            -> test stills for framing
    python cap.py clip NAME OUTDIR         -> PNG frame sequence for one clip
"""
import json, math, pathlib, sys
from playwright.sync_api import sync_playwright

SITE = "http://localhost:8765/"
HTML = pathlib.Path("M:/Repositories/BGMap/data/movies/site/index.html").read_text(encoding="utf-8")
HOOK = """  window.__mm = { state, select, setView3d, setSpin, fitView, pos, showUnmade, redraw, recolor,
    setView(v) { state.viewState = v; deckgl.setProps({ initialViewState: v }); redraw(); } };
  init();
})();"""
assert HTML.count("  init();\n})();") == 1
HTML = HTML.replace("  init();\n})();", HOOK)
CSS = ".card, #stubs, #tooltip, #suggest { display: none !important; } #map { inset: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; }"

def open_page(p, theme="dark"):
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 540, "height": 540}, device_scale_factor=2, color_scheme=theme)
    pg.route(SITE, lambda r: r.fulfill(body=HTML, content_type="text/html; charset=utf-8"))
    pg.goto(SITE); pg.wait_for_selector("#status", state="hidden", timeout=90000)
    pg.add_style_tag(content=CSS); pg.evaluate("() => window.dispatchEvent(new Event('resize'))"); pg.wait_for_timeout(1500)
    return b, pg

JS_FIND = "([n, y]) => { const f = __mm.state.films; for (let i = 0; i < f.name.length; i++) if (f.name[i] === n && (y == null || f.year[i] === y)) return i; return -1; }"

def frame(pg, v):
    pg.evaluate("(v) => __mm.setView(v)", v)
    pg.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

def base(pg):
    return pg.evaluate("() => __mm.fitView(__mm.state.models[__mm.state.model])")

def lerp(a, b, t): return a + (b - a) * t
def ease(t): return 0.5 - 0.5 * math.cos(math.pi * t)

def shots(pg):
    """Each clip: (setup js, list of view states over time)."""
    b = base(pg); z0 = b["zoom"]; fps = 30
    gf = pg.evaluate(JS_FIND, ["GoodFellas", 1990]); ol = pg.evaluate(JS_FIND, ["Olympus Has Fallen", 2013]); pk = pg.evaluate(JS_FIND, ["Pokémon the Movie 2000", 1999])
    lk = pg.evaluate(JS_FIND, ["The Lion King", 1994]); dr = pg.evaluate(JS_FIND, ["Dracula", 1931])
    P = lambda i: pg.evaluate("(i) => __mm.pos(i)", i)
    su = pg.evaluate("() => __mm.state.manifest.unmade.findIndex(u => u.title === 'The Last Province')")
    def orbit(n, target, zoom, rot, rx=20):
        out = []
        for k in range(n):
            t = k / (n - 1)
            out.append({**b, "target": [lerp(a, c, ease(t)) for a, c in zip(target[0], target[1])],
                        "zoom": lerp(zoom[0], zoom[1], ease(t)), "rotationOrbit": lerp(rot[0], rot[1], t), "rotationX": rx,
                        "transitionDuration": 0})
        return out
    T = b["target"]
    return {
        "spin": (None, orbit(9 * fps, [T, T], [z0 - 0.15, z0 + 0.2], [-60, -10])),
        "olympus": (f"__mm.select({ol}, false)", orbit(int(7.3 * fps), [P(ol), P(ol)], [z0 + 2.2, z0 + 2.8], [0, 15])),
        "goodfellas": (f"__mm.select({gf}, false)", orbit(int(10.6 * fps), [T, P(gf)], [z0 + 0.2, z0 + 2.3], [-10, 15])),
        "pokemon": (f"__mm.select({pk}, false)", orbit(6 * fps, [P(pk), P(pk)], [z0 + 1.6, z0 + 2.4], [40, 60])),
        "lionking": (f"__mm.select({lk}, false)", orbit(5 * fps, [P(lk), P(lk)], [z0 + 2.2, z0 + 2.8], [0, 15])),
        "dracula": (f"__mm.select({dr}, false)", orbit(6 * fps, [P(dr), P(dr)], [z0 + 1.8, z0 + 2.6], [-20, 0])),
        "unmade": (f"__mm.showUnmade({su})", "unmade"),
        "end": ("__mm.state.selected = null; __mm.recolor(); __mm.redraw()", orbit(8 * fps, [T, T], [z0 + 0.15, z0 - 0.1], [-10, 30])),
    }

def unmade_views(pg, n=324):
    b = base(pg); u = pg.evaluate("() => { const m = __mm.state.models[__mm.state.model]; const k = __mm.state.manifest.unmade.findIndex(u => u.title === 'The Last Province'); const p = m.unmade[k]; return [p[2], p[3], p[4]]; }")
    t = u or b["target"]
    return [{**b, "target": list(t), "zoom": b["zoom"] + lerp(0.0, 0.35, ease(k / (n - 1))),
             "rotationOrbit": lerp(-20, 5, k / (n - 1)), "rotationX": 20, "transitionDuration": 0} for k in range(n)]


def run_clip(pg, name, out, every=1):
    setup, views = shots(pg)[name]
    if setup: pg.evaluate(f"() => {{ {setup} }}"); pg.wait_for_timeout(2500)
    if views == "unmade":  # centred on the unmade movie, wide enough to see both parent clusters
        views = unmade_views(pg)
    d = pathlib.Path(out) / name; d.mkdir(parents=True, exist_ok=True)
    for k, v in enumerate(views):
        if k % every: continue
        frame(pg, v); pg.screenshot(path=str(d / f"{k:04d}.png"))
    print(name, len(views), "frames")

with sync_playwright() as p:
    b, pg = open_page(p)
    if sys.argv[1] == "stills":
        out = pathlib.Path(sys.argv[2])
        for name in ["spin", "godfather", "pokemon", "lionking", "unmade", "end"]:
            setup, views = shots(pg)[name]
            if setup: pg.evaluate(f"() => {{ {setup} }}"); pg.wait_for_timeout(2500)
            if views == "unmade": views = unmade_views(pg)
            if views: frame(pg, views[-1])
            pg.screenshot(path=str(out / f"still_{name}.png"))
    else:
        run_clip(pg, sys.argv[2], sys.argv[3])
    b.close()
