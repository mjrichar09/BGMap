"""Social image of one director's or actor's films on the map, with their stats card (people lens data).

Captures the 2D map twice from a hooked local copy of the site (the dimmed base, and the person's films drawn
large), reads their card from data/people.json, groups their best-known films into labels, and fills
videos/posters/person.html, which fits the text and places the labels without overlaps. Starts
`python -m http.server 8765` in data/movies/site if nothing is serving there (and stops it after).

    .venv/Scripts/python videos/tools/person_card.py "Steven Spielberg" [--labels 8]
Writes videos/posters/people/<slug>/<slug>.png (1080x1350 at 2x, X's tallest feed size) plus the captures
and data.json. Needs Playwright in .venv (uses the installed Edge; no browser download).
"""
import argparse
import json
import math
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE_DIR = ROOT / "data" / "movies" / "site"
POSTERS = ROOT / "videos" / "posters"
SITE = "http://localhost:8765/"
S, MX, MY = 0.52, 17, 307   # 2000 px capture -> template px: (MX + x*S, MY + y*S)
GROUP_PX = 46               # films closer than this (template px) share a label
PER_LINE, NAMES_PER_LABEL = 2, 3
NAMED = 18                  # only this many most-voted films are named in labels (all are drawn)

HTML = (SITE_DIR / "index.html").read_text(encoding="utf-8")
for a, b in [
    ("  init();\n})();", """  window.__mm = { state, setView3d, fitView, pos, setHighlight, recolor, redraw,
    vp() { return deckgl.getViewports()[0]; },
    setView(v) { state.viewState = v; deckgl.setProps({ initialViewState: v }); redraw(); } };
  init();
})();"""),
    ('id: "labels", data: visibleLabels(),', 'id: "labels", data: state.noLabels ? [] : visibleLabels(),'),
    ("  const pointSize = (i) => { const a = colors[i * 4 + 3]; return a <= 60 && a > 2 ? Math.min(radii[i], 3) * 1.6 : radii[i] * 2; };",
     "  const pointSize = (i) => { if (state.hlBoost && state.highlight && state.highlight.has(i)) return Math.max(radii[i] * 2, 14) * state.hlBoost; const a = colors[i * 4 + 3]; return a <= 60 && a > 2 ? Math.min(radii[i], 3) * 1.6 : radii[i] * 2; };"),
]:
    assert HTML.count(a) == 1, f"site page changed; can't hook: {a[:50]}"
    HTML = HTML.replace(a, b)
CSS = ".card, #stubs, #popcorn, #tooltip, #suggest, #status { display: none !important; }"
PERSON = """(d) => { const s = __mm.state; s.hlBoost = 2.6; const g = s.films, hits = [];
  for (let i = 0; i < s.n; i++) if (g.dir[i].includes(d) || g.cast[i].includes(d)) hits.push(i);
  __mm.setHighlight(new Set(hits)); return hits.map(i => ({ i, name: g.name[i], year: g.year[i], votes: g.votes[i] || 0 })); }"""


def serving():
    try:
        urllib.request.urlopen(SITE, timeout=2); return True
    except OSError:
        return False


def capture(person_index, out):
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 1000, "height": 1000}, device_scale_factor=2, color_scheme="dark")
        pg.route(SITE, lambda r: r.fulfill(body=HTML, content_type="text/html; charset=utf-8"))
        pg.goto(SITE); pg.wait_for_selector("#status", state="hidden", timeout=120000); pg.wait_for_timeout(2000)
        pg.add_style_tag(content=CSS)
        pg.evaluate("() => { __mm.state.noLabels = true; __mm.setView3d(false); }"); pg.wait_for_timeout(1500)
        pg.evaluate("() => { const v = __mm.fitView(__mm.state.models[__mm.state.model]); if (v) __mm.setView({ ...v, transitionDuration: 0 }); }")
        pg.wait_for_timeout(2500)
        pg.screenshot(path=str(out / "base.png"))
        films = pg.evaluate(PERSON, person_index); pg.wait_for_timeout(2500)
        pg.screenshot(path=str(out / "hl.png"))
        xy = pg.evaluate("(ix) => ix.map(i => { const p = __mm.vp().project(__mm.pos(i)); return [p[0], p[1]]; })", [f["i"] for f in films])
        b.close()
    for f, (x, y) in zip(films, xy):
        f["at"] = [round(MX + 2 * x * S, 1), round(MY + 2 * y * S, 1)]   # capture is 2x the 1000 px viewport
    return films


def short(name):
    """Label form of a title: franchise prefix only ("Indiana Jones and the Temple of Doom" -> "Indiana Jones")."""
    if re.match(r"[^:]+ Presents: ", name):  # "Fast & Furious Presents: Hobbs & Shaw" -> "Hobbs & Shaw"
        return name.split(": ", 1)[1].strip()
    return re.split(r": | and the | - | – ", name)[0].strip()


def groups(films, limit):
    """The best-known films (the NAMED most-voted), merged into labels where they sit close together, most-voted
    groups first; each title is named once, at most NAMES_PER_LABEL to a label."""
    out = []
    for f in sorted(films, key=lambda f: -f["votes"])[:NAMED]:
        g = next((g for g in out if math.dist(g["seed"], f["at"]) < GROUP_PX), None)
        if g is None:
            if len(out) >= limit:
                continue
            g = {"films": [], "seed": f["at"], "at": f["at"], "votes": 0}; out.append(g)
        g["films"].append(f); g["votes"] += f["votes"]
        g["at"] = [sum(h["at"][k] for h in g["films"]) / len(g["films"]) for k in (0, 1)]
    used = set()
    for g in out:
        names = [n for n in dict.fromkeys(short(f["name"]) for f in g["films"]) if n not in used][:NAMES_PER_LABEL]
        used.update(names)
        g["lines"] = [" · ".join(names[k:k + PER_LINE]) for k in range(0, len(names), PER_LINE)]
    return [g for g in out if g["lines"]]


def money(m):
    return f"${m / 1000:.1f}B".replace(".0B", "B") if m >= 1000 else f"${m:.0f}M"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def ranked(pct, what, role=None):
    of = f" of {role}s" if role else ""
    return f"{what}: top {max(1, 100 - pct)}%{of}" if pct >= 50 else f"{what}: {ordinal(pct)} percentile{of}"


def card_text(name, c):
    role, pct = c["role"], c.get("pct", {})
    last = name.split()[-1]
    tiles = [[f"{c['rating']:.1f}", ranked(pct.get("rating", 50), "Avg rating", role)]]
    if c.get("boxOffice") is not None:
        tiles.append([money(c["boxOffice"]), ranked(pct.get("boxOffice", 50), "Median box office")])
    if c.get("boxOfficeTotal"):
        tiles.append([money(c["boxOfficeTotal"]), "Total box office, where known"])
    if c.get("roi") is not None and len(tiles) < 3:
        tiles.append([f"{c['roi']:.1f}×", ranked(pct.get("roi", 50), "Return on budget")])
    p = pct.get("range", 50)
    tiles.append([f"Top {max(1, 100 - p)}%" if p >= 50 else f"Bottom {max(1, p)}%", "For range of stories"])
    while len(tiles) < 4:
        tiles.insert(-1, [f"{round(c['orig'] * 100)}", ranked(pct.get("orig", 50), "Originality")])
    spread = "land everywhere" if p >= 75 else "stay in one corner" if p <= 25 else "cover a lot of ground" if p >= 50 else "stick close together"
    return {
        "name": name, "tiles": tiles[:4],
        "eyebrow": f"{role.title()} · {c['films']} films on the map · {c['years'][0]}–{c['years'][1]}",
        "sub": f"An AI placed every film by its plot. {last}'s {spread}.",
        "src": f"Vs. {c['peers']:,} {role}s · TMDB data, not inflation-adjusted · Uses the TMDB API; not endorsed or certified by TMDB.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--labels", type=int, default=8, help="most label groups to try (some may not fit)")
    args = ap.parse_args()
    man = json.loads((SITE_DIR / "data" / "manifest.json").read_text(encoding="utf-8"))
    people = json.loads((SITE_DIR / "data" / "people.json").read_text(encoding="utf-8"))
    matches = [k for k, n in enumerate(man["people"]) if n.lower() == args.name.lower()]
    if not matches:
        near = [n for n in man["people"] if args.name.lower() in n.lower()][:8]
        sys.exit(f"No one called {args.name!r} on the map. Close: {near}")
    d = max(matches, key=lambda k: people.get(str(k), {}).get("films", 0))
    name, card = man["people"][d], people.get(str(d))
    if not card:
        sys.exit(f"{name} has too few films on the map for a stats card.")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    out = POSTERS / "people" / slug; out.mkdir(parents=True, exist_ok=True)

    server = None
    if not serving():
        server = subprocess.Popen([sys.executable, "-m", "http.server", "8765"], cwd=SITE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if serving(): break
            time.sleep(0.25)
    try:
        films = capture(d, out)
    finally:
        if server:
            server.terminate()
    data = {**card_text(name, card), "s": S, "mx": MX, "my": MY,
            "base": f"people/{slug}/base.png", "hl": f"people/{slug}/hl.png",
            "points": [f["at"] for f in films], "groups": [{"lines": g["lines"], "at": g["at"]} for g in groups(films, args.labels)]}
    (out / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        pg.add_init_script(f"window.DATA = {json.dumps(data)};")
        pg.goto((POSTERS / "person.html").as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(800)
        placed = pg.evaluate("() => layout()"); pg.wait_for_timeout(200)
        png = out / f"{slug}.png"
        pg.screenshot(path=str(png)); b.close()
    print(f"{name}: {card['films']} films, tiles {[t[0] for t in data['tiles']]}")
    print(f"labels placed: {placed}")
    print(f"wrote {png}")


if __name__ == "__main__":
    main()
