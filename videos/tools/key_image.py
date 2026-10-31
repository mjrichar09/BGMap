"""Still map capture for the Reddit key image: the 2D layout at 2000 px with the page's panels hidden,
plus the screen positions of the films the callouts point at. Serves data/movies/site with a hooked
index.html (local only, the live site is untouched); needs `python -m http.server 8765` in that folder.

    python key_image.py OUT_DIR
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

SITE = "http://localhost:8765/"
HTML = pathlib.Path("M:/Repositories/BGMap/data/movies/site/index.html").read_text(encoding="utf-8")
HOOK = """  window.__mm = { state, setView3d, fitView, pos, setHighlight, recolor, redraw, labelAnchors,
    vp() { return deckgl.getViewports()[0]; },
    setView(v) { state.viewState = v; deckgl.setProps({ initialViewState: v }); redraw(); } };
  init();
})();"""
assert HTML.count("  init();\n})();") == 1
HTML = HTML.replace("  init();\n})();", HOOK)
# The image draws its own, larger region labels (legible on phones), so the map's are hidden.
LB = 'id: "labels", data: visibleLabels(),'
assert HTML.count(LB) == 1
HTML = HTML.replace(LB, 'id: "labels", data: state.noLabels ? [] : visibleLabels(),')
CSS = ".card, #stubs, #popcorn, #tooltip, #suggest, #status { display: none !important; }"
FILMS = {  # callout -> films ("Name", year)
    "goodfellas": [("GoodFellas", 1990), ("American Gangster", 2007), ("Carlito's Way", 1993), ("The Irishman", 2019)],
    "dracula": [("Dracula", 1931), ("Dracula", 1958), ("Bram Stoker's Dracula", 1992)],
    "olympus": [("Olympus Has Fallen", 2013), ("White House Down", 2013)],
}
DESERT = ("Saving Private Ryan", 1998, 148)  # Island 9: WWII Marines x prehistoric beasts


def main():
    out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    deserts = json.loads(pathlib.Path("M:/Repositories/BGMap/data/movies/site/data/deserts.json").read_text(encoding="utf-8"))
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 1000, "height": 1000}, device_scale_factor=2, color_scheme="dark")
        pg.route(SITE, lambda r: r.fulfill(body=HTML, content_type="text/html; charset=utf-8"))
        pg.goto(SITE); pg.wait_for_selector("#status", state="hidden", timeout=120000); pg.wait_for_timeout(2000)
        pg.add_style_tag(content=CSS)
        pg.evaluate("() => { __mm.state.noLabels = true; __mm.setView3d(false); }"); pg.wait_for_timeout(1500)
        pg.evaluate("() => { const v = __mm.fitView(__mm.state.models[__mm.state.model]); if (v) __mm.setView({ ...v, transitionDuration: 0 }); }")
        pg.wait_for_timeout(2500)
        pg.screenshot(path=str(out / "map.png"))
        find = """(fs) => fs.map(([n, y]) => { const f = __mm.state.films;
            for (let i = 0; i < __mm.state.n; i++) if (f.name[i] === n && f.year[i] === y) return i; return -1; })"""
        proj = "(ix) => ix.map(i => { const p = __mm.vp().project(__mm.pos(i)); return [p[0], p[1]]; })"
        pts = {}
        for k, fs in FILMS.items():
            idx = pg.evaluate(find, fs)
            pts[k] = [{"name": n, "year": y, "xy": xy} for (n, y), i, xy in zip(fs, idx, pg.evaluate(proj, [i for i in idx if i >= 0]) + [None] * 9) if i >= 0]
        seed = pg.evaluate(find, [DESERT[:2]])[0]
        row = next(r for r in deserts["seeds"][str(seed)] if r[0] == DESERT[2])
        near = pg.evaluate(proj, row[3])
        pts["desert"] = [{"xy": [sum(x for x, _ in near) / len(near), sum(y for _, y in near) / len(near)], "near": near}]
        pts["regions"] = pg.evaluate("""() => __mm.labelAnchors(__mm.state.models[__mm.state.model], false).map(a => {
            const p = __mm.vp().project([a.x, a.y, a.z || 0]); return { label: a.label, size: a.size, xy: [p[0], p[1]] }; })""")
        (out / "points.json").write_text(json.dumps(pts, indent=1), encoding="utf-8")
        print(json.dumps(pts)[:900])
        b.close()


if __name__ == "__main__":
    main()
