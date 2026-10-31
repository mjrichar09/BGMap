"""Still map capture of one person's films (the people lens), for social images: the 2D layout at 2000 px with
the page's panels and region labels hidden, the person's films drawn large, and the screen position of
every one of their films. Serves data/movies/site with a hooked index.html (local only, the live site is
untouched); needs `python -m http.server 8765` in that folder.

    python person_image.py "Steven Spielberg" OUT_DIR
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

SITE = "http://localhost:8765/"
HTML = pathlib.Path("M:/Repositories/BGMap/data/movies/site/index.html").read_text(encoding="utf-8")
HOOK = """  window.__mm = { state, setView3d, fitView, pos, setHighlight, recolor, redraw,
    vp() { return deckgl.getViewports()[0]; },
    setView(v) { state.viewState = v; deckgl.setProps({ initialViewState: v }); redraw(); } };
  init();
})();"""
assert HTML.count("  init();\n})();") == 1
HTML = HTML.replace("  init();\n})();", HOOK)
LB = 'id: "labels", data: visibleLabels(),'
assert HTML.count(LB) == 1
HTML = HTML.replace(LB, 'id: "labels", data: state.noLabels ? [] : visibleLabels(),')
# Highlighted films draw larger (state.hlBoost) so they read at social-image size.
PS = "  const pointSize = (i) => { const a = colors[i * 4 + 3]; return a <= 60 && a > 2 ? Math.min(radii[i], 3) * 1.6 : radii[i] * 2; };"
assert HTML.count(PS) == 1
HTML = HTML.replace(PS, "  const pointSize = (i) => { if (state.hlBoost && state.highlight && state.highlight.has(i)) return Math.max(radii[i] * 2, 14) * state.hlBoost; const a = colors[i * 4 + 3]; return a <= 60 && a > 2 ? Math.min(radii[i], 3) * 1.6 : radii[i] * 2; };")
CSS = ".card, #stubs, #popcorn, #tooltip, #suggest, #status { display: none !important; }"
PERSON = """(name) => { const s = __mm.state; s.noLabels = true; s.hlBoost = 2.6; const d = s.manifest.people.indexOf(name), g = s.films, hits = [];
  for (let i = 0; i < s.n; i++) if (g.dir[i].includes(d) || g.cast[i].includes(d)) hits.push(i);
  __mm.setHighlight(new Set(hits)); return hits.map(i => ({ i, name: g.name[i], year: g.year[i], votes: g.votes[i], directed: g.dir[i].includes(d) })); }"""


def main():
    who, out = sys.argv[1], pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 1000, "height": 1000}, device_scale_factor=2, color_scheme="dark")
        pg.route(SITE, lambda r: r.fulfill(body=HTML, content_type="text/html; charset=utf-8"))
        pg.goto(SITE); pg.wait_for_selector("#status", state="hidden", timeout=120000); pg.wait_for_timeout(2000)
        pg.add_style_tag(content=CSS)
        pg.evaluate("() => { __mm.state.noLabels = true; __mm.setView3d(false); }"); pg.wait_for_timeout(1500)
        pg.evaluate("() => { const v = __mm.fitView(__mm.state.models[__mm.state.model]); if (v) __mm.setView({ ...v, transitionDuration: 0 }); }")
        films = pg.evaluate(PERSON, who); pg.wait_for_timeout(2500)
        pg.screenshot(path=str(out / "map.png"))
        xy = pg.evaluate("(ix) => ix.map(i => { const p = __mm.vp().project(__mm.pos(i)); return [p[0], p[1]]; })", [f["i"] for f in films])
        for f, (x, y) in zip(films, xy):
            f["xy"] = [round(x * 2), round(y * 2)]  # in the 2000 px screenshot
        (out / "films.json").write_text(json.dumps(films, indent=1, ensure_ascii=False), encoding="utf-8")
        for f in sorted(films, key=lambda f: -(f["votes"] or 0)):
            print(f"{f['name']} ({f['year']}) {'dir' if f['directed'] else 'cast'} votes {f['votes']} at {f['xy']}")
        b.close()


if __name__ == "__main__":
    main()
