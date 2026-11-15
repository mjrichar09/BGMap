"""Write the frame compositions (compositions/frames/*.html) for the four vertical fit shorts.
Run from videos/ after the voice is aligned (timings come from each project's audio_meta.json):

    python tools/build_fit_frames.py [a|b|c|d ...]

Every number here traces to the data: films.json `fit` (percentiles), data/movies/fit/fit.json (cluster
predictions), the site manifest's fit summary, fit/proposals.json, and the earlier name test
(mmm-predict-a-hit/PLAN.md). Layout: 1080x1920, content between y = 230 and y = 1440.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GSAP = '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'
INK, AMBER, RED, MUTED, BG = "#F3E6D0", "#FFB547", "#C8102E", "#B39C80", "#0B0807"
BLUE, ORANGE = "rgb(52,112,201)", "rgb(232,125,20)"     # the site's "vs. its plot" colors (below / above)
URL = "massive-movie-map.mjrfx.com"


class Words:
    def __init__(self, proj):
        meta = json.loads((ROOT / proj / "audio_meta.json").read_text(encoding="utf-8"))
        self.v = {v["frame"]: v for v in meta["voices"]}

    def dur(self, n): return self.v[n]["duration_s"]

    def __call__(self, n, word, k=0):
        norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
        hits = [w["start"] for w in self.v[n]["words"] if norm(w["text"]) == norm(word)]
        if len(hits) <= k: raise KeyError(f"frame {n}: no word {word!r} #{k}")
        return round(hits[k], 2)


def fonts(proj):
    return (ROOT / proj / ".hyperframes" / "fontfaces.css").read_text(encoding="utf-8")


def wrap(proj, cid, D, css, body, js):
    S = f'[data-composition-id="{cid}"]'
    base = f"""
{S} {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; color: {INK}; font-family: "Work Sans", sans-serif; }}
{S} * {{ box-sizing: border-box; }}
{S} .clip {{ position: absolute; }}
{S} .layer {{ left: 0; top: 0; width: 1080px; height: 1920px; pointer-events: none; }}
{S} .ground {{ background: {BG}; }}
{S} .beam {{ background: radial-gradient(ellipse 75% 50% at 50% -6%, rgba(255,196,120,.14), rgba(255,196,120,0) 70%); }}
{S} .topdim {{ background: linear-gradient(to bottom, rgba(11,8,7,.95) 0px, rgba(11,8,7,.75) 430px, rgba(11,8,7,0) 640px); }}
{S} .botdim {{ background: linear-gradient(to top, rgba(11,8,7,.92) 0px, rgba(11,8,7,.55) 520px, rgba(11,8,7,0) 720px); }}
{S} .abs {{ position: absolute; }}
{S} .eyebrow {{ font: 600 30px/1 "Oswald", sans-serif; letter-spacing: 4px; text-transform: uppercase; color: {AMBER}; white-space: nowrap; }}
{S} .title {{ font: 400 84px/1.06 "Limelight", serif; letter-spacing: .06em; text-transform: uppercase; color: {INK}; white-space: nowrap; }}
{S} .note {{ font: 400 25px/1.4 "Work Sans", sans-serif; color: {MUTED}; }}
{S} .lbl {{ font: 500 28px/1 "Oswald", sans-serif; letter-spacing: 2.5px; text-transform: uppercase; color: {MUTED}; white-space: nowrap; }}
{S} .num {{ font-family: "Courier Prime", monospace; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }}
"""
    return f"""<template id="{cid}-template">
{GSAP}
<style>
{fonts(proj)}
{base}
{css.replace("§", S)}
</style>
<div id="root" data-composition-id="{cid}" data-start="0" data-duration="{D}" data-width="1080" data-height="1920">
{body}
<script>
(function () {{
  window.__timelines = window.__timelines || {{}};
  var root = document.querySelector('[data-composition-id="{cid}"]');
  var q = function (s) {{ return root.querySelector(s); }};
  var qa = function (s) {{ return root.querySelectorAll(s); }};
  var tl = gsap.timeline({{ paused: true }});
  var D = {D};
  function inn(sel, t, o) {{ o = o || {{}};
    tl.fromTo(qa(sel), {{ opacity: 0, y: o.y == null ? 28 : o.y, x: o.x || 0, scale: o.sc || 1 }},
      {{ opacity: 1, y: 0, x: 0, scale: 1, duration: o.d || 0.55, ease: "power3.out", stagger: o.s || 0 }}, t); }}
  function count(sel, a, b, t, d, fmt) {{ var e = q(sel), st = {{ v: a }};
    function r() {{ e.textContent = fmt(st.v); }} r();
    tl.fromTo(st, {{ v: a }}, {{ v: b, duration: d, ease: "power3.out", onUpdate: r }}, t); }}
{js}
  tl.to({{}}, {{ duration: D }}, 0);
  window.__timelines["{cid}"] = tl;
}})();
</script>
</div>
</template>
"""


def video(p, D, src, start=0.0, dim=None, track=1):
    v = f"""<video id="{p}-video" data-frame-video="approved" src="assets/clips/{src}" muted playsinline
  data-start="0" data-duration="{D}"{f' data-media-start="{start}"' if start else ''} data-track-index="{track}"
  data-frame-video-x="0" data-frame-video-y="0" data-frame-video-width="1080" data-frame-video-height="1920"
  data-frame-video-fit="cover"></video>"""
    if dim is not None:
        v += f'\n<div id="{p}-dim" class="clip layer" style="background: rgba(11,8,7,{dim})" data-start="0" data-duration="{D}" data-track-index="2"></div>'
    return v


def layer(p, D, name, cls, track):
    return f'<div id="{p}-{name}" class="clip layer {cls}" data-start="0" data-duration="{D}" data-track-index="{track}"></div>'


def ground(p, D):
    return layer(p, D, "ground", "ground", 1) + "\n" + layer(p, D, "beam", "beam", 2)


def stage(p, D, inner, track=5):
    return f'<div id="{p}-stage" class="clip layer" data-start="0" data-duration="{D}" data-track-index="{track}">\n{inner}\n</div>'


def header(p, eyebrow, lines, top=250, size=84):
    ls = "".join(f'<div class="title {p}-tl" id="{p}-tl{k}" style="font-size:{size}px">{l}</div>' for k, l in enumerate(lines))
    return f'<div class="abs" style="left:90px;top:{top}px;width:900px"><div class="eyebrow" id="{p}-eb">{eyebrow}</div><div style="margin-top:18px">{ls}</div></div>'


def note(p, text, top=1360):
    return f'<div class="abs note" id="{p}-note" style="left:90px;top:{top}px;width:900px">{text}</div>'


# ---------------------------------------------------------------- shared frame kinds

def end_frame(proj, cid, p, D, lines, t_url):
    css = f"""
§ .e-dim {{ background: radial-gradient(ellipse 85% 40% at 50% 42%, rgba(11,8,7,.97) 0%, rgba(11,8,7,.92) 55%, rgba(11,8,7,.72) 100%),
  linear-gradient(to bottom, rgba(11,8,7,0) 60%, rgba(11,8,7,.92) 68%, rgba(11,8,7,.92) 100%); }}
§ .e-line {{ display: block; font: 400 80px/1.08 "Limelight", serif; letter-spacing: .06em; text-transform: uppercase; color: {AMBER};
  white-space: nowrap; text-shadow: 0 0 24px rgba(255,181,71,.35); }}
§ .e-url {{ position: relative; display: inline-block; margin-top: 70px; font: 700 50px/1 "Courier Prime", monospace; color: {INK}; white-space: nowrap; }}
§ .e-ch {{ opacity: 0; }}
§ .e-caret {{ position: absolute; top: -2px; left: 0; width: .08em; height: 1.08em; background: {AMBER}; opacity: 0; }}
§ .e-credits {{ left: 90px; width: 900px; top: 1290px; display: flex; align-items: center; gap: 28px;
  font: 400 23px/1.35 "Work Sans", sans-serif; color: {MUTED}; }}
§ .e-credits img {{ width: 150px; height: auto; flex: none; display: block; }}
§ .e-black {{ background: #000; opacity: 0; }}"""
    chars = "".join(f'<span class="e-ch">{c}</span>' for c in URL)
    body = "\n".join([
        video(p, D, "end.mp4"),
        layer(p, D, "dim", "e-dim", 2), layer(p, D, "beam", "beam", 3),
        stage(p, D, f"""<div class="abs" style="left:40px;width:1000px;top:560px;text-align:center">
  <div id="{p}-tw">{''.join(f'<span class="e-line {p}-ln">{l}</span>' for l in lines)}</div>
  <div class="e-url" id="{p}-url">{chars}<span class="e-caret" id="{p}-caret"></span></div>
</div>""", 4),
        f"""<div class="clip e-credits" id="{p}-credits" data-start="0" data-duration="{D}" data-track-index="5">
  <img src="assets/tmdb-logo.svg" alt="TMDB">
  <span>This video uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB. Plots: Wikipedia, <span style="white-space:nowrap">CC BY-SA</span>.</span>
</div>""",
        layer(p, D, "black", "e-black", 6)])
    js = f"""
  inn(".{p}-ln", 0.0, {{ y: 46, d: 0.7, s: 0.45 }});
  tl.fromTo(q("#{p}-tw"), {{ scale: 1 }}, {{ scale: 1.025, duration: D, ease: "none" }}, 0);
  var chars = qa(".e-ch"), caret = q("#{p}-caret"), t0 = {t_url}, step = 1.1 / chars.length;
  tl.set(caret, {{ opacity: 1, left: "0em" }}, t0 - 0.12);
  for (var i = 0; i < chars.length; i++) {{ tl.set(chars[i], {{ opacity: 1 }}, t0 + i * step); tl.set(caret, {{ left: ((i + 1) * 0.6) + "em" }}, t0 + i * step); }}
  var tb = t0 + chars.length * step + 0.25;
  for (var k = 0; k < 6; k++) tl.set(caret, {{ opacity: k % 2 === 0 ? 0 : 1 }}, tb + k * 0.3);
  inn("#{p}-credits", 1.4, {{ y: 12, d: 0.8 }});
  tl.fromTo(q("#{p}-black"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.6, ease: "power1.inOut" }}, D - 0.6);"""
    return wrap(proj, cid, D, css, body, js)


def hook_frame(proj, cid, p, D, src, eyebrow, lines, t_eb, t_lines, chip=None, t_chip=0, legend=None, t_legend=0, size=84, start=0.0):
    css = f"""
§ .chip {{ font: 600 40px/1 "Oswald", sans-serif; letter-spacing: 3px; text-transform: uppercase; color: {AMBER};
  background: rgba(11,8,7,.82); border-left: 5px solid {AMBER}; padding: 18px 26px; white-space: nowrap; }}
§ .leg {{ display: flex; gap: 40px; font: 500 28px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK};
  background: rgba(11,8,7,.8); padding: 16px 24px; }}
§ .leg i {{ display: inline-block; width: 22px; height: 22px; border-radius: 50%; margin-right: 12px; vertical-align: -3px; }}"""
    inner = header(p, eyebrow, lines, size=size)
    if chip: inner += f'\n<div class="abs chip" id="{p}-chip" style="left:90px;top:1330px">{chip}</div>'
    if legend:
        inner += f'\n<div class="abs leg" id="{p}-leg" style="left:90px;top:1330px">' + "".join(
            f'<span><i style="background:{c}"></i>{t}</span>' for c, t in legend) + "</div>"
    body = "\n".join([video(p, D, src, start), layer(p, D, "top", "topdim", 2), layer(p, D, "bot", "botdim", 3), stage(p, D, inner, 4)])
    js = f"""
  inn("#{p}-eb", {t_eb}, {{ y: 12, d: 0.45 }});
  {' '.join(f'inn("#{p}-tl{k}", {t}, {{ y: 36, d: 0.6 }});' for k, t in enumerate(t_lines))}
  {f'inn("#{p}-chip", {t_chip}, {{ x: -24, y: 0, d: 0.5 }});' if chip else ''}
  {f'inn("#{p}-leg", {t_legend}, {{ y: 16, d: 0.5 }});' if legend else ''}"""
    return wrap(proj, cid, D, css, body, js)


def list_frame(proj, cid, p, D, eyebrow, title, items, t_eb, t_title, src=None, start=0.0, accent=AMBER, notes=""):
    """items: [(name, keywords, t)]"""
    css = f"""
§ .it {{ left: 90px; width: 900px; height: 190px; border-left: 6px solid {accent}; padding-left: 34px; }}
§ .it .rk {{ font: 700 36px/1 "Courier Prime", monospace; color: {accent}; }}
§ .it .nm {{ margin-top: 14px; font: 600 72px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK}; white-space: nowrap; }}
§ .it .kw {{ margin-top: 16px; font: 400 28px/1 "Courier Prime", monospace; color: {MUTED}; white-space: nowrap; }}"""
    inner = header(p, eyebrow, [title])
    for k, (nm, kw, t) in enumerate(items):
        inner += f'\n<div class="abs it" id="{p}-it{k}" style="top:{560 + k * 250}px"><div class="rk">{k + 1:02d}</div><div class="nm">{nm}</div><div class="kw">{kw}</div></div>'
    inner += "\n" + note(p, notes)
    body = "\n".join(([video(p, D, src, start, dim=0.86)] if src else [ground(p, D)]) + [stage(p, D, inner)])
    js = f"""
  inn("#{p}-eb", {t_eb}, {{ y: 12, d: 0.45 }});
  inn(".{p}-tl", {t_title}, {{ y: 36, d: 0.6 }});
  {' '.join(f'inn("#{p}-it{k}", {t - 0.08}, {{ x: -40, y: 0, d: 0.55 }});' for k, (_, _, t) in enumerate(items))}
  inn("#{p}-note", {items[0][2] + 0.4}, {{ y: 0, d: 0.6 }});"""
    return wrap(proj, cid, D, css, body, js)


def scorecard_frame(proj, cid, p, D, tag, title, logline, bars, t_title, notes, stamp=None, t_stamp=0, marks=(), size=76):
    """bars: [(label, value, color, t)]; marks: [(phrase, t)] highlighted inside the logline."""
    css = f"""
§ .tag {{ font: 600 30px/1 "Oswald", sans-serif; letter-spacing: 4px; text-transform: uppercase; color: {BG}; background: {AMBER}; padding: 10px 16px; display: inline-block; }}
§ .log {{ font: 400 42px/1.42 "Work Sans", sans-serif; color: {INK}; }}
§ .log .mk {{ background: linear-gradient({AMBER}, {AMBER}) no-repeat 0 92% / 0% 6px; }}
§ .row {{ left: 90px; width: 900px; height: 130px; }}
§ .row .lbl {{ position: absolute; left: 0; top: 0; }}
§ .row .val {{ position: absolute; right: 0; top: -18px; font-size: 64px; }}
§ .row .trk {{ position: absolute; left: 0; top: 56px; width: 900px; height: 34px; background: rgba(243,230,208,.08); }}
§ .row .fill {{ position: absolute; left: 0; top: 56px; height: 34px; width: 900px; transform-origin: left center; transform: scaleX(0); }}
§ .row .pct {{ font-size: 30px; color: {MUTED}; }}
§ .stamp {{ font: 400 54px/1 "Limelight", serif; letter-spacing: .06em; text-transform: uppercase; color: {AMBER};
  border: 4px solid {AMBER}; padding: 16px 26px 12px; transform: rotate(-4deg); text-shadow: 0 0 24px rgba(255,181,71,.35); white-space: nowrap; }}"""
    log = logline
    for k, (ph, _) in enumerate(marks):
        log = log.replace(ph, f'<span class="mk" id="{p}-mk{k}">{ph}</span>', 1)
    inner = f"""<div class="abs" style="left:90px;top:250px;width:900px">
  <div class="tag" id="{p}-tag">{tag}</div>
  <div class="title" id="{p}-ttl" style="margin-top:30px;font-size:{size}px;color:{AMBER};text-shadow:0 0 24px rgba(255,181,71,.3)">{title}</div>
  <div class="log" id="{p}-log" style="margin-top:34px">{log}</div>
</div>"""
    for k, (lab, v, col, _) in enumerate(bars):
        inner += f"""
<div class="abs row" id="{p}-r{k}" style="top:{860 + k * 150}px"><div class="lbl" style="color:{INK}">{lab}</div>
  <div class="val num" id="{p}-v{k}" style="color:{col}">0</div><div class="trk"></div><div class="fill" id="{p}-f{k}" style="background:{col}"></div></div>"""
    if stamp: inner += f'\n<div class="abs stamp" id="{p}-stamp" style="right:90px;top:690px">{stamp}</div>'
    inner += "\n" + note(p, notes, 1330)
    body = "\n".join([ground(p, D), stage(p, D, inner)])
    js = f"""
  inn("#{p}-tag", 0.0, {{ y: 12, d: 0.4 }});
  inn("#{p}-ttl", {t_title}, {{ y: 30, d: 0.6 }});
  inn("#{p}-log", {t_title + 0.25}, {{ y: 20, d: 0.6 }});
  inn(".row", {bars[0][3] - 0.3}, {{ y: 16, d: 0.4, s: 0.06 }});
  {' '.join(f'tl.fromTo(q("#{p}-f{k}"), {{ scaleX: 0 }}, {{ scaleX: {v / 100:.3f}, duration: 0.8, ease: "power3.out" }}, {t}); count("#{p}-v{k}", 0, {v}, {t}, 0.8, function (x) {{ return Math.round(x) + "th"; }});' for k, (_, v, _, t) in enumerate(bars))}
  {' '.join(f'tl.fromTo(q("#{p}-mk{k}"), {{ backgroundSize: "0% 6px" }}, {{ backgroundSize: "100% 6px", duration: 0.5, ease: "power2.out" }}, {t});' for k, (_, t) in enumerate(marks))}
  {f'tl.fromTo(q("#{p}-stamp"), {{ opacity: 0, scale: 1.4 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "power3.out" }}, {t_stamp});' if stamp else ''}
  inn("#{p}-note", {bars[0][3] + 0.5}, {{ y: 0, d: 0.6 }});"""
    # ordinal suffix fix-up: 1st / 2nd / 3rd
    js = js.replace('return Math.round(x) + "th";', 'var n = Math.round(x), s = (n % 100 >= 11 && n % 100 <= 13) ? "th" : ["th", "st", "nd", "rd"][n % 10] || "th"; return n + s;')
    return wrap(proj, cid, D, css, body, js)


ORD = 'function (x) { var n = Math.round(x), s = (n % 100 >= 11 && n % 100 <= 13) ? "th" : ["th", "st", "nd", "rd"][n % 10] || "th"; return n + s; }'


# ---------------------------------------------------------------- A: the AI's biggest misses

FILMS_A = [  # name, poster, box predicted -> actual, popularity predicted -> actual (films.json fit)
    ("The Irishman", "the-irishman-2019.jpg", 98, 16, 100, 98),
    ("Marriage Story", "marriage-story-2019.jpg", 96, 8, 97, 98),
    ("The Trial of the Chicago 7", "the-trial-of-the-chicago-7-2020.jpg", 99, 8, 98, 95),
    ("The Two Popes", "the-two-popes-2019.jpg", 96, 6, 96, 95),
]


def short_a():
    proj = "mmm-fit-a-misses"; w = Words(proj); out = {}
    D = [w.dur(n) for n in range(1, 6)]; st = [sum(D[:k]) for k in range(5)]
    out["01-fit-hook"] = hook_frame(proj, "01-fit-hook", "a1", D[0], "fit_box.mp4", "I trained an AI to predict",
        ["Box office,", "from the plot"], w(1, "trained"), [w(1, "box"), w(1, "plot")],
        legend=[(BLUE, "Did worse than its plot"), (ORANGE, "Did better")], t_legend=w(1, "alone") + 0.1)

    # 2: the four misses, poster by poster
    p, d = "a2", D[1]
    css = f"""
§ .pc {{ width: 300px; }}
§ .pc img {{ width: 300px; height: 450px; object-fit: cover; display: block; border: 1px solid rgba(243,230,208,.3); }}
§ .pc div {{ margin-top: 14px; font: 600 28px/1.15 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK}; }}"""
    inner = header(p, "Box office, predicted from the plot", ["Biggest misses"])
    pos = [(165, 470), (615, 470), (165, 1000), (615, 1000)]
    for k, (nm, img, *_r) in enumerate(FILMS_A):
        inner += f'\n<div class="abs pc" id="{p}-c{k}" style="left:{pos[k][0]}px;top:{pos[k][1]}px"><img src="assets/posters/{img}" alt=""><div>{nm}</div></div>'
    ts = [w(2, "Irishman"), w(2, "Marriage"), w(2, "Trial"), w(2, "Two")]
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.45 }}); inn(".{p}-tl", {w(2, "biggest")}, {{ y: 36, d: 0.6 }});
  {' '.join(f'inn("#{p}-c{k}", {t - 0.15}, {{ y: 50, sc: 0.95, d: 0.55 }});' for k, t in enumerate(ts))}"""
    out["02-misses"] = wrap(proj, "02-misses", d, css, "\n".join([video(p, d, "fit_box.mp4", round(st[1], 3), dim=0.84), stage(p, d, inner)]), js)

    # 3: predicted vs actual box-office percentile, dumbbells
    p, d = "a3", D[2]
    X0, XW = 110, 860
    x = lambda v: X0 + v / 100 * XW
    css = f"""
§ .nm {{ font: 600 34px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK}; white-space: nowrap; }}
§ .trk {{ height: 4px; background: rgba(243,230,208,.18); }}
§ .zone {{ top: 600px; height: 690px; }}
§ .dot {{ width: 34px; height: 34px; margin: -17px 0 0 -17px; border-radius: 50%; }}
§ .lnk {{ height: 6px; margin-top: -3px; background: {RED}; transform-origin: right center; }}
§ .v {{ font-size: 32px; width: 80px; margin-left: -40px; text-align: center; }}
§ .tick {{ font: 400 24px/1 "Courier Prime", monospace; color: {MUTED}; width: 60px; margin-left: -30px; text-align: center; }}
§ .zl {{ font: 600 26px/1 "Oswald", sans-serif; letter-spacing: 3px; text-transform: uppercase; white-space: nowrap; }}
§ .key {{ display: flex; gap: 40px; font: 500 28px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK}; }}
§ .key i {{ display: inline-block; width: 22px; height: 22px; border-radius: 50%; margin-right: 12px; vertical-align: -3px; }}"""
    inner = header(p, "Box office percentile", ["Plot vs. reality"])
    inner += f'\n<div class="abs key" id="{p}-key" style="left:90px;top:500px"><span><i style="background:{AMBER}"></i>Plot predicts</span><span><i style="background:{RED}"></i>Actual</span></div>'
    inner += f'\n<div class="abs zone" id="{p}-ztop" style="left:{x(95)}px;width:{x(100) - x(95)}px;background:rgba(255,181,71,.2)"></div>'
    inner += f'\n<div class="abs zone" id="{p}-zbot" style="left:{x(0)}px;width:{x(20) - x(0)}px;background:rgba(200,16,46,.2)"></div>'
    for k, (nm, _i, bp, ba, *_r) in enumerate(FILMS_A):
        y = 640 + k * 170
        inner += f"""
<div class="abs nm" id="{p}-n{k}" style="left:{X0}px;top:{y}px">{nm}</div>
<div class="abs trk" style="left:{X0}px;top:{y + 78}px;width:{XW}px"></div>
<div class="abs lnk" id="{p}-l{k}" style="left:{x(ba)}px;top:{y + 80}px;width:{x(bp) - x(ba)}px"></div>
<div class="abs dot" id="{p}-a{k}" style="left:{x(bp)}px;top:{y + 80}px;background:{RED}"></div>
<div class="abs dot" id="{p}-p{k}" style="left:{x(bp)}px;top:{y + 80}px;background:{AMBER}"></div>
<div class="abs num v" id="{p}-pv{k}" style="left:{x(bp)}px;top:{y + 108}px;color:{AMBER}">{bp}</div>
<div class="abs num v" id="{p}-av{k}" style="left:{x(bp)}px;top:{y + 108}px;color:{INK}">{bp}</div>"""
    for v in (0, 25, 50, 75, 100):
        inner += f'\n<div class="abs tick" style="left:{x(v)}px;top:1300px">{v}</div>'
    inner += f'\n<div class="abs zl" id="{p}-zlt" style="right:{1080 - x(100)}px;top:560px;color:{AMBER}">Top 5%</div>'
    inner += f'\n<div class="abs zl" id="{p}-zlb" style="left:{x(0)}px;top:560px;color:{RED}">Bottom fifth</div>'
    inner += "\n" + note(p, "Percentiles among films with known box office (TMDB). Predicted from the plot alone, names masked.", 1350)
    tt, tb = w(3, "top"), w(3, "bottom")
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.45 }}); inn(".{p}-tl", 0.1, {{ y: 36, d: 0.6 }});
  inn("#{p}-key", 0.3, {{ y: 12, d: 0.45 }}); inn(".nm", 0.35, {{ x: -24, y: 0, d: 0.45, s: 0.07 }});
  tl.fromTo(qa(".trk"), {{ scaleX: 0, transformOrigin: "left center" }}, {{ scaleX: 1, duration: 0.6, ease: "power3.out", stagger: 0.07 }}, 0.4);
  tl.fromTo(qa(".tick"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4, stagger: 0.04 }}, 0.6);
  tl.fromTo(q("#{p}-ztop"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {tt}); inn("#{p}-zlt", {tt}, {{ y: 10, d: 0.4 }});
  tl.set(qa("[id^='{p}-a'], [id^='{p}-av'], [id^='{p}-l']"), {{ opacity: 0 }}, 0);
  {' '.join(f'tl.fromTo(q("#{p}-p{k}"), {{ x: {-(x(r[2]) - X0)}, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.6, ease: "power3.out" }}, {tt - 0.3 + k * 0.08}); count("#{p}-pv{k}", 0, {r[2]}, {tt - 0.3 + k * 0.08}, 0.6, function (v) {{ return Math.round(v); }}); tl.fromTo(q("#{p}-pv{k}"), {{ x: {-(x(r[2]) - X0)}, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.6, ease: "power3.out" }}, {tt - 0.3 + k * 0.08});' for k, r in enumerate(FILMS_A))}
  tl.fromTo(q("#{p}-zbot"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {tb}); inn("#{p}-zlb", {tb}, {{ y: 10, d: 0.4 }});
  {' '.join(f'tl.set(q("#{p}-a{k}"), {{ opacity: 1 }}, {tb - 0.2 + k * 0.08}); tl.set(q("#{p}-av{k}"), {{ opacity: 1 }}, {tb - 0.2 + k * 0.08}); tl.set(q("#{p}-l{k}"), {{ opacity: 1 }}, {tb - 0.2 + k * 0.08}); tl.fromTo(q("#{p}-a{k}"), {{ x: 0 }}, {{ x: {x(r[3]) - x(r[2])}, duration: 0.8, ease: "power3.inOut" }}, {tb - 0.2 + k * 0.08}); tl.fromTo(q("#{p}-av{k}"), {{ x: 0 }}, {{ x: {x(r[3]) - x(r[2])}, duration: 0.8, ease: "power3.inOut" }}, {tb - 0.2 + k * 0.08}); tl.fromTo(q("#{p}-l{k}"), {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.8, ease: "power3.inOut" }}, {tb - 0.2 + k * 0.08}); count("#{p}-av{k}", {r[2]}, {r[3]}, {tb - 0.2 + k * 0.08}, 0.8, function (v) {{ return Math.round(v); }}); tl.to(q("#{p}-pv{k}"), {{ opacity: 0.45, duration: 0.3 }}, {tb});' for k, r in enumerate(FILMS_A))}
  inn("#{p}-note", 1.0, {{ y: 0, d: 0.6 }});"""
    out["03-dumbbell"] = wrap(proj, "03-dumbbell", d, css, "\n".join([video(p, d, "fit_box.mp4", round(st[2], 3), dim=0.9), stage(p, d, inner)]), js)

    # 4: the stories were right (popularity), Netflix
    p, d = "a4", D[3]
    X0, XW = 470, 500
    x = lambda v: X0 + v / 100 * XW
    css = f"""
§ .nm {{ font: 600 30px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK}; white-space: nowrap; width: 360px; }}
§ .trk {{ height: 4px; background: rgba(243,230,208,.18); }}
§ .dot {{ width: 28px; height: 28px; margin: -14px 0 0 -14px; border-radius: 50%; }}
§ .v {{ font-size: 30px; }}
§ .big {{ font: 400 150px/1 "Limelight", serif; letter-spacing: .06em; color: {RED}; text-shadow: 0 0 30px rgba(200,16,46,.55); white-space: nowrap; }}
§ .sub {{ font: 600 40px/1.25 "Oswald", sans-serif; letter-spacing: 3px; text-transform: uppercase; color: {INK}; }}
§ .key {{ display: flex; gap: 40px; font: 500 28px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK}; }}
§ .key i {{ display: inline-block; width: 22px; height: 22px; border-radius: 50%; margin-right: 12px; vertical-align: -3px; }}"""
    inner = header(p, "But popularity: predicted right", ["People watched"])
    inner += f'\n<div class="abs key" id="{p}-key" style="left:90px;top:500px"><span><i style="background:{AMBER}"></i>Plot predicts</span><span><i style="background:{INK}"></i>Actual</span></div>'
    for k, (nm, _i, _bp, _ba, vp, va) in enumerate(FILMS_A):
        y = 600 + k * 95
        inner += f"""
<div class="abs nm {p}-row" style="left:90px;top:{y - 15}px">{nm.replace('The Trial of the ', '')}</div>
<div class="abs trk {p}-row" style="left:{X0}px;top:{y}px;width:{XW}px"></div>
<div class="abs dot {p}-dp" style="left:{x(vp)}px;top:{y + 2}px;background:{AMBER}"></div>
<div class="abs dot {p}-da" style="left:{x(va)}px;top:{y + 2}px;background:{INK};width:16px;height:16px;margin:-8px 0 0 -8px"></div>
<div class="abs num v {p}-dv" style="left:{X0 - 4}px;top:{y + 22}px;color:{MUTED};font-size:24px">{vp} → {va}</div>"""
    inner += f"""
<div class="abs" style="left:90px;top:1010px;width:900px">
  <div class="big" id="{p}-nf">Netflix</div>
  <div class="sub" id="{p}-sub" style="margin-top:22px">Streamed them. Barely put them in cinemas.</div>
</div>"""
    inner += "\n" + note(p, "Popularity: TMDB votes vs. films of the same year. Box office: TMDB; Netflix doesn't report ticket sales.", 1350)
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.45 }}); inn(".{p}-tl", {w(4, "wrong")}, {{ y: 36, d: 0.6 }});
  inn("#{p}-key", 0.3, {{ y: 12, d: 0.45 }}); inn(".{p}-row", 0.35, {{ x: -20, y: 0, d: 0.45, s: 0.04 }});
  inn(".{p}-dp", {w(4, "stories")} - 0.5, {{ y: 0, sc: 0.3, d: 0.4, s: 0.08 }}); inn(".{p}-da", {w(4, "stories")} - 0.2, {{ y: 0, sc: 0.3, d: 0.4, s: 0.08 }});
  inn(".{p}-dv", {w(4, "stories")}, {{ y: 8, d: 0.4, s: 0.06 }});
  tl.fromTo(q("#{p}-nf"), {{ opacity: 0, scale: 1.25, transformOrigin: "left center" }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "power3.out" }}, {w(4, "Netflix") - 0.05});
  inn("#{p}-sub", {w(4, "barely")}, {{ y: 16, d: 0.5 }});
  inn("#{p}-note", {w(4, "cinemas")}, {{ y: 0, d: 0.6 }});"""
    out["04-netflix"] = wrap(proj, "04-netflix", d, css, "\n".join([video(p, d, "fit_box.mp4", round(st[3], 3), dim=0.9), stage(p, d, inner)]), js)
    out["05-end"] = end_frame(proj, "05-end", "a5", D[4], ["What does your", "movie's plot", "predict?"], w(5, "Massive"))
    return proj, out


# ---------------------------------------------------------------- B: the name is worth more than the story

def swap_frame(proj, cid, p, D, eyebrow, pre, old, new, post, a, b, t_a, t_swap, t_b):
    css = f"""
§ .card {{ left: 90px; width: 900px; top: 400px; padding: 40px 44px; background: #EFE6D2; color: #2A1A14; border-top: 14px solid {RED}; }}
§ .card .lab {{ font: 600 26px/1 "Oswald", sans-serif; letter-spacing: 3px; text-transform: uppercase; color: {RED}; }}
§ .card .txt {{ margin-top: 24px; font: 400 40px/1.42 "Work Sans", sans-serif; }}
§ .nmw {{ position: relative; display: inline-block; font-weight: 700; padding: 0 8px; background: rgba(255,181,71,.55); }}
§ .strike {{ position: absolute; left: 0; top: 52%; height: 5px; width: 100%; background: {RED}; transform-origin: left center; transform: scaleX(0); }}
§ .big {{ font-size: 170px; color: {AMBER}; line-height: 1; }}
§ .trk {{ left: 90px; width: 900px; top: 1240px; height: 30px; background: rgba(243,230,208,.1); }}
§ .fill {{ left: 90px; width: 900px; top: 1240px; height: 30px; background: {AMBER}; transform-origin: left center; transform: scaleX(0); }}"""
    inner = f"""<div class="abs" style="left:90px;top:250px"><div class="eyebrow" id="{p}-eb">{eyebrow}</div></div>
<div class="abs card" id="{p}-card"><div class="lab">The plot</div>
  <div class="txt">{pre}<span class="nmw" id="{p}-old">{old}<span class="strike" id="{p}-st"></span></span><span class="nmw" id="{p}-new" style="display:none">{new}</span>{post}</div></div>
<div class="abs" style="left:90px;top:1000px"><div class="lbl">Predicted box office, percentile</div>
  <div class="num big" id="{p}-n" style="margin-top:14px">0th</div></div>
<div class="abs trk"></div><div class="abs fill" id="{p}-f"></div>
""" + note(p, "Scored by an earlier version of the model, which could still read names. Percentile among real films.", 1310)
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.45 }}); inn("#{p}-card", 0.05, {{ y: 40, d: 0.6 }});
  tl.fromTo(q("#{p}-f"), {{ scaleX: 0 }}, {{ scaleX: {a / 100}, duration: 0.8, ease: "power3.out" }}, {t_a});
  count("#{p}-n", 0, {a}, {t_a}, 0.8, {ORD});
  tl.fromTo(q("#{p}-st"), {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.3, ease: "power2.out" }}, {t_swap - 0.35});
  tl.set(q("#{p}-old"), {{ display: "none" }}, {t_swap}); tl.set(q("#{p}-new"), {{ display: "inline-block" }}, {t_swap});
  tl.fromTo(q("#{p}-new"), {{ backgroundColor: "rgba(255,181,71,1)" }}, {{ backgroundColor: "rgba(255,181,71,.55)", duration: 0.8 }}, {t_swap});
  tl.fromTo(q("#{p}-f"), {{ scaleX: {a / 100} }}, {{ scaleX: {b / 100}, duration: 0.6, ease: "power3.out" }}, {t_b});
  count("#{p}-n", {a}, {b}, {t_b}, 0.6, {ORD});
  inn("#{p}-note", {t_a + 0.4}, {{ y: 0, d: 0.6 }});"""
    return wrap(proj, cid, D, css, "\n".join([ground(p, D), stage(p, D, inner)]), js)


def short_b():
    proj = "mmm-fit-b-names"; w = Words(proj); out = {}
    D = [w.dur(n) for n in range(1, 7)]
    out["01-fit-hook"] = hook_frame(proj, "01-fit-hook", "b1", D[0], "fit_box.mp4", "From the plot alone",
        ["Can an AI", "predict a hit?"], w(1, "plot") , [0.05, w(1, "predict")], chip="Same plot. Two names.", t_chip=w(1, "Same"))
    out["02-swap"] = swap_frame(proj, "02-swap", "b2", D[1], "Pitch 1 · same plot, new name",
        "When an alien warlord armed with six cosmic stones invades Earth, the surviving members of ", "the Vanguard", "the Avengers",
        ", the planet's mightiest superheroes, must reunite for one final mission.", 65, 97, w(2, "65th"), w(2, "Avengers"), w(2, "97th"))
    out["03-swap"] = swap_frame(proj, "03-swap", "b3", D[2], "Pitch 2 · same plot, new name",
        "On his eleventh birthday, ", "an orphan boy", "Harry Potter",
        " living with his cruel aunt learns that he is the son of two legendary sorcerers, and is invited to a hidden academy of magic.",
        17, 98, w(3, "17th"), w(3, "Harry"), w(3, "98th"))

    p, d = "b4", D[3]
    css = f"""
§ .txt {{ left: 90px; width: 900px; font: 400 42px/1.5 "Work Sans", sans-serif; color: {INK}; }}
§ .red {{ position: relative; display: inline-block; padding: 0 6px; font-weight: 700; }}
§ .bar {{ position: absolute; inset: 2px -4px; background: {INK}; transform-origin: left center; transform: scaleX(0); }}
§ .ph {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font: 700 34px/1 "Courier Prime", monospace;
  color: {BG}; opacity: 0; white-space: nowrap; }}"""
    def red(k, name, ph): return f'<span class="red">{name}<span class="bar" id="{p}-b{k}"></span><span class="ph" id="{p}-p{k}">{ph}</span></span>'
    inner = header(p, "The name was doing the work", ["So I hid", "every name"])
    inner += f'\n<div class="abs txt" style="top:640px">"…the surviving members of {red(0, "the Avengers", "GROUP A")}, the planet\'s mightiest superheroes, must reunite…"</div>'
    inner += f'\n<div class="abs txt" style="top:930px">"{red(1, "Harry Potter", "PERSON A")}, living with his cruel aunt, learns that he is the son of two legendary sorcerers…"</div>'
    inner += f'\n<div class="abs lbl" id="{p}-lb" style="left:90px;top:1240px;color:{AMBER};font-size:34px">Every name masked before scoring</div>'
    th = w(4, "hid")
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.45 }});
  inn(".{p}-tl", {w(4, "So")}, {{ y: 36, d: 0.6, s: 0.25 }});
  inn(".txt", 0.1, {{ y: 20, d: 0.5, s: 0.15 }});
  tl.fromTo(qa(".bar"), {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.35, ease: "power2.out", stagger: 0.12 }}, {th});
  tl.fromTo(qa(".ph"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, stagger: 0.12 }}, {th + 0.4});
  inn("#{p}-lb", {th + 0.5}, {{ y: 12, d: 0.45 }});"""
    out["04-redact"] = wrap(proj, "04-redact", d, css, "\n".join([ground(p, d), stage(p, d, inner)]), js)

    # 5: what sells, names masked: predicted box office per story cluster vs the typical film (fit.json box_original)
    p, d = "b5", D[4]
    fit = json.loads((ROOT.parent / "data/movies/fit/fit.json").read_text(encoding="utf-8"))["box_original"]["top_clusters"]
    pick = {c["label"]: c["pred"] for c in fit}
    rows = [("Superheroes", "superhero, based on comic", w(5, "Superheroes")),
            ("True sports stories", "american football, based on true story", w(5, "true")),
            ("Martial-arts epics", "wuxia, martial arts", w(5, "martial-arts"))]
    X0, PX = 90, 900 / 2.5
    css = f"""
§ .nm {{ font: 600 52px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK}; white-space: nowrap; }}
§ .kw {{ font: 400 26px/1 "Courier Prime", monospace; color: {MUTED}; white-space: nowrap; }}
§ .trk {{ height: 64px; width: 900px; background: rgba(243,230,208,.07); }}
§ .fill {{ height: 64px; background: {AMBER}; transform-origin: left center; }}
§ .v {{ font-size: 44px; color: {BG}; line-height: 64px; }}
§ .one {{ width: 0; border-left: 3px dashed rgba(243,230,208,.75); }}"""
    inner = header(p, "With the names gone", ["What sells"])
    for k, (nm, key, _t) in enumerate(rows):
        y = 560 + k * 230; v = 10 ** pick[key]
        inner += f"""
<div class="abs nm {p}-nm" id="{p}-n{k}" style="left:{X0}px;top:{y}px">{nm}</div>
<div class="abs kw" style="left:{X0}px;top:{y + 62}px">{key}</div>
<div class="abs trk" style="left:{X0}px;top:{y + 104}px"></div>
<div class="abs fill" id="{p}-f{k}" style="left:{X0}px;top:{y + 104}px;width:{v * PX:.0f}px"></div>
<div class="abs num v" id="{p}-v{k}" style="left:{X0 + v * PX - 130:.0f}px;top:{y + 104}px">{v:.1f}×</div>"""
    inner += "".join(f'\n<div class="abs one {p}-one" style="left:{X0 + PX:.0f}px;top:{560 + k * 230 + 96}px;height:80px"></div>' for k in range(3))
    inner += f'\n<div class="abs lbl" id="{p}-onel" style="left:{X0 + PX + 14:.0f}px;top:1250px">1× = typical film of its year</div>'
    inner += "\n" + note(p, "Predicted box office for each story region, from the plot alone, names masked, non-franchise films.", 1330)
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.45 }}); inn(".{p}-tl", {w(5, "what")}, {{ y: 36, d: 0.6 }});
  tl.fromTo(qa(".trk"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4, stagger: 0.06 }}, 0.5);
  tl.fromTo(qa(".{p}-one"), {{ scaleY: 0, transformOrigin: "center top" }}, {{ scaleY: 1, duration: 0.6, ease: "power3.out" }}, 0.7); inn("#{p}-onel", 0.9, {{ y: 8, d: 0.4 }});
  {' '.join(f'inn("#{p}-n{k}", {t - 0.1}, {{ x: -24, y: 0, d: 0.45 }}); tl.fromTo(q("#{p}-f{k}"), {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.8, ease: "power3.out" }}, {t}); tl.fromTo(q("#{p}-v{k}"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {t + 0.5});' for k, (_n, _k, t) in enumerate(rows))}
  inn("#{p}-note", 1.5, {{ y: 0, d: 0.6 }});"""
    js += f"""
  {' '.join(f'tl.fromTo(qa(".kw")[{k}], {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {t});' for k, (_n, _k, t) in enumerate(rows))}"""
    out["05-bars"] = wrap(proj, "05-bars", d, css, "\n".join([ground(p, d), stage(p, d, inner)]), js)
    out["06-end"] = end_frame(proj, "06-end", "b6", D[5], ["What would", "your story", "score?"], w(6, "Massive"))
    return proj, out


# ---------------------------------------------------------------- C: loved vs. watched

LOVED_C, MONEY_C, LOW_C = AMBER, "#5FD3B5", "#F03448"     # the dot colours in capture_fit.py's C_GROUPS
PX = lambda v: round(241 + 7.51 * v)      # percentile -> x on the captured plot (axes measured from the stills)
PY = lambda v: round(1359 - 7.51 * v)     # percentile -> y


def stills(p, names, first=0):
    """Stacked full-frame stills of the plot (assets/clips/c, from capture_fit.py c_stills); all after `first` start hidden."""
    return "".join(f'<img class="abs st" id="{p}-s-{n}" src="assets/clips/c/{n}.png" style="left:0;top:0;width:1080px;height:1920px;{"" if k <= first else "opacity:0"}">'
                   for k, n in enumerate(names))


def filter_frame(proj, cid, p, D, title, rows, color, t_title, base, lit, key=None):
    """Short C: the fit plot with story regions lit one by one, each named in a filter row above the plot.
    rows: [(name, keywords, t)]; base: the still shown first; lit: the stills that add each row's region."""
    css = f"""
§ .row {{ left: 90px; height: 44px; display: flex; align-items: center; gap: 18px; white-space: nowrap; }}
§ .row i {{ width: 24px; height: 24px; border-radius: 50%; background: {color}; box-shadow: 0 0 14px {color}; }}
§ .row .nm {{ font: 600 40px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {INK}; }}
§ .row .kw {{ font: 400 24px/1 "Courier Prime", monospace; color: {MUTED}; }}
§ .key {{ font: 500 24px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {MUTED}; white-space: nowrap; }}
§ .key i {{ display: inline-block; width: 18px; height: 18px; border-radius: 50%; margin-right: 10px; vertical-align: -2px; }}"""
    inner = header(p, "Filter · story regions", [title], top=225, size=80)
    if key:
        inner += f'\n<div class="abs key" id="{p}-key" style="right:90px;top:229px"><i style="background:{key[1]}"></i>{key[0]}</div>'
    for k, (nm, kw, t) in enumerate(rows):
        inner += f'\n<div class="abs row" id="{p}-r{k}" style="top:{405 + k * 56}px"><i></i><span class="nm">{nm}</span><span class="kw">{kw}</span></div>'
    plot = f'<div id="{p}-plot" class="clip layer" data-start="0" data-duration="{D}" data-track-index="3">{stills(p, [base] + lit)}</div>'
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.45 }});
  inn(".{p}-tl", {t_title}, {{ y: 30, d: 0.55 }});
  {f'inn("#{p}-key", 0.15, {{ y: 0, d: 0.5 }});' if key else ''}"""
    for k, (_, _, t) in enumerate(rows):
        js += f"""
  inn("#{p}-r{k}", {t} - 0.08, {{ x: -30, y: 0, d: 0.45 }});
  tl.fromTo(q("#{p}-s-{lit[k]}"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4, ease: "power2.out" }}, {t} - 0.08);"""
    return wrap(proj, cid, D, css, "\n".join([ground(p, D), plot, stage(p, D, inner)]), js)


def short_c():
    proj = "mmm-fit-c-loved"; w = Words(proj); out = {}
    D = [w.dur(n) for n in range(1, 6)]
    out["01-list"] = filter_frame(proj, "01-list", "c1", D[0], "Rated highest",
        [("Concert films", "concert", w(1, "Concert")), ("Nature documentaries", "nature", w(1, "nature")),
         ("Music documentaries", "music, biography", w(1, "music"))], LOVED_C, w(1, "highest"), "base", ["loved1", "loved2", "loved3"])
    out["02-list"] = filter_frame(proj, "02-list", "c2", D[1], "Makes money",
        [("Superheroes", "superhero, comic", w(2, "Superheroes")), ("Martial-arts epics", "wuxia", w(2, "martial-arts")),
         ("Ancient Rome", "roman empire", w(2, "ancient"))], MONEY_C, w(2, "money"), "loved3", ["money1", "money2", "money3"],
        key=("Rated highest", LOVED_C))

    # 3: every film, faint; a dashed diagonal shows what "related" would look like, then the real trend lies almost flat.
    p, d = "c3", D[2]
    x0, x1 = PX(0), PX(100)
    r = 0.2                                   # predicted rating vs predicted box office (percentiles): y = 50 + r (x - 50)
    ya, yb = PY(50 - 50 * r), PY(50 + 50 * r)
    L1 = round(((x1 - x0) ** 2 + (PY(100) - PY(0)) ** 2) ** .5); L2 = round(((x1 - x0) ** 2 + (yb - ya) ** 2) ** .5)
    css = f"""
§ .cnt {{ font-size: 120px; color: {AMBER}; line-height: 1; }}
§ .plate {{ left: 255px; width: 400px; top: 622px; padding: 24px 30px 26px; background: rgba(11,8,7,.92); border: 3px solid {AMBER}; }}
§ .plate .k {{ font: 600 26px/1 "Oswald", sans-serif; letter-spacing: 4px; text-transform: uppercase; color: {MUTED}; }}
§ .plate .r {{ font-size: 104px; color: {AMBER}; line-height: 1; margin-top: 10px; }}
§ .plate .s {{ font: 400 46px/1.08 "Limelight", serif; letter-spacing: .05em; text-transform: uppercase; color: {INK}; margin-top: 12px; white-space: nowrap; }}
§ svg.guide {{ position: absolute; left: 0; top: 0; overflow: visible; }}
§ .gl {{ font: 500 26px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; white-space: nowrap;
  background: rgba(11,8,7,.85); padding: 8px 12px; }}"""
    plot = f'<div id="{p}-plot" class="clip layer" data-start="0" data-duration="{d}" data-track-index="3">{stills(p, ["money3", "all"])}</div>'
    inner = f"""<svg class="guide" width="1080" height="1920" viewBox="0 0 1080 1920">
  <line id="{p}-diag" x1="{x0}" y1="{PY(0)}" x2="{x1}" y2="{PY(100)}" stroke="{INK}" stroke-width="5" stroke-linecap="round" stroke-dasharray="0 {L1}" opacity="0"/>
  <line id="{p}-fit" x1="{x0}" y1="{ya}" x2="{x1}" y2="{yb}" stroke="{AMBER}" stroke-width="9" stroke-linecap="round" stroke-dasharray="0 {L2}"/>
</svg>
<div class="abs gl" id="{p}-gd" style="right:{1080 - PX(97)}px;top:{PY(91)}px;color:{INK}">If they went together</div>
<div class="abs gl" id="{p}-gf" style="right:{1080 - PX(97)}px;top:{yb + 26}px;color:{AMBER}">What the AI found</div>
<div class="abs" style="left:90px;top:230px"><div class="eyebrow" id="{p}-eb">Every plot, scored twice</div>
  <div class="num cnt" id="{p}-cnt" style="margin-top:16px">0</div><div class="lbl" id="{p}-pl" style="margin-top:10px;font-size:34px;color:{INK}">plots · rating across, box office up</div></div>
<div class="abs plate" id="{p}-plate"><div class="k">Correlation</div><div class="num r">+0.2</div><div class="s">Almost<br>unrelated</div></div>"""
    t_cnt, t_be, t_al = w(3, "thirty-six"), w(3, "Being"), w(3, "almost")
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.45 }});
  tl.fromTo(q("#{p}-s-all"), {{ opacity: 0 }}, {{ opacity: 1, duration: 1.2, ease: "power1.inOut" }}, {t_cnt} - 0.1);
  inn("#{p}-cnt", {t_cnt} - 0.1, {{ y: 16, d: 0.4 }});
  count("#{p}-cnt", 0, 36841, {t_cnt}, 1.3, function (v) {{ return Math.round(v).toLocaleString("en-US"); }});
  inn("#{p}-pl", {w(3, "both")}, {{ y: 10, d: 0.45 }});
  tl.set(q("#{p}-diag"), {{ opacity: 0.85 }}, {t_be} - 0.1);
  tl.fromTo(q("#{p}-diag"), {{ attr: {{ "stroke-dasharray": "0 {L1}" }} }}, {{ attr: {{ "stroke-dasharray": "{L1} 0" }}, duration: 0.8, ease: "power2.inOut" }}, {t_be} - 0.1);
  tl.set(q("#{p}-diag"), {{ attr: {{ "stroke-dasharray": "18 14" }} }}, {t_be} + 0.72);
  inn("#{p}-gd", {t_be} + 0.3, {{ y: 10, d: 0.4 }});
  tl.fromTo(q("#{p}-fit"), {{ attr: {{ "stroke-dasharray": "0 {L2}" }} }}, {{ attr: {{ "stroke-dasharray": "{L2} 0" }}, duration: 0.7, ease: "power2.inOut" }}, {t_al} - 0.35);
  inn("#{p}-gf", {t_al}, {{ y: 10, d: 0.4 }});
  tl.to([q("#{p}-diag"), q("#{p}-gd")], {{ opacity: 0.65, duration: 0.4 }}, {t_al} + 0.2);
  tl.fromTo(q("#{p}-plate"), {{ opacity: 0, scale: 1.1 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "power3.out", transformOrigin: "0% 0%" }}, {t_al});"""
    out["03-scatter"] = wrap(proj, "03-scatter", d, css, "\n".join([ground(p, d), plot, stage(p, d, inner)]), js)
    out["04-list"] = filter_frame(proj, "04-list", "c4", D[3], "Rated lowest",
        [("Gore", "gore, cannibal", w(4, "Gore")), ("Psycho killers", "psychopath, murder", w(4, "psycho")),
         ("Horror anthologies", "horror anthology", w(4, "horror"))], LOW_C, w(4, "lowest"), "base", ["low1", "low2", "low3"])
    out["05-end"] = end_frame(proj, "05-end", "c5", D[4], ["Explore the", "plot fit"], w(5, "Massive"))
    return proj, out


# ---------------------------------------------------------------- D: movies nobody has made

def short_d():
    proj = "mmm-fit-d-unmade"; w = Words(proj); out = {}
    D = [w.dur(n) for n in range(1, 6)]
    props = json.loads((ROOT.parent / "data/movies/fit/proposals.json").read_text(encoding="utf-8"))
    props = props if isinstance(props, list) else props["proposals"]
    out["01-fit-hook"] = hook_frame(proj, "01-fit-hook", "d1", D[0], "gaps.mp4", "Stories nobody has filmed",
        ["Movies nobody", "has made"], w(1, "stories"), [0.05, w(1, "gaps")], chip="Scored by the AI, from the plot alone", t_chip=w(1, "score"))

    p, d = "d2", D[1]
    X0, Y0, S = 170, 1260, 780      # chart: rating 0..100 -> x 170..950, popularity 0..100 -> y 1260..480
    X = lambda v: X0 + v / 100 * S
    Y = lambda v: Y0 - v / 100 * S
    rs = sorted(q["pct"]["rating"] for q in props); vs = sorted(q["pct"]["votes"] for q in props)
    mr, mv = rs[len(rs) // 2], vs[len(vs) // 2]
    css = f"""
§ .ax {{ background: rgba(243,230,208,.55); }}
§ .dot {{ width: 30px; height: 30px; margin: -15px 0 0 -15px; border-radius: 50%; background: {AMBER}; border: 3px solid {BG}; }}
§ .med {{ border-color: rgba(243,230,208,.6); border-style: dashed; border-width: 0; }}
§ .q {{ background: rgba(200,16,46,.18); }}
§ .ql {{ background: rgba(11,8,7,.85); padding: 6px 10px; font: 600 30px/1.1 "Oswald", sans-serif; letter-spacing: 3px; text-transform: uppercase; color: {INK}; text-align: right; white-space: nowrap; }}
§ .dl {{ background: rgba(11,8,7,.85); padding: 4px 8px; font: 600 24px/1 "Oswald", sans-serif; letter-spacing: 2px; text-transform: uppercase; color: {AMBER}; white-space: nowrap; }}"""
    inner = header(p, "The 17 unmade movies", ["Liked,", "not watched"], size=80)
    inner += f'\n<div class="abs q" id="{p}-q" style="left:{X(50)}px;top:{Y(50)}px;width:{X(100) - X(50)}px;height:{Y(0) - Y(50)}px"></div>'
    inner += f'\n<div class="abs ql" id="{p}-ql" style="left:{X(50)}px;width:{X(100) - X(50) - 12}px;top:{Y(50) + 12}px">Liked, not watched</div>'
    inner += f'\n<div class="abs ax" style="left:{X0}px;top:{Y0}px;width:{S}px;height:3px"></div><div class="abs ax" style="left:{X0}px;top:{Y(100)}px;width:3px;height:{S}px"></div>'
    inner += f'\n<div class="abs med" id="{p}-mx" style="left:{X(mr)}px;top:{Y(100)}px;height:{S}px;border-left-width:3px"></div>'
    inner += f'\n<div class="abs med" id="{p}-my" style="left:{X0}px;top:{Y(mv)}px;width:{S}px;border-top-width:3px"></div>'
    inner += f'\n<div class="abs lbl" style="left:{X0}px;top:{Y0 + 22}px">Predicted rating →</div>'
    inner += f'\n<div class="abs lbl" style="left:{X0 - 60}px;top:{Y0}px;transform:rotate(-90deg);transform-origin:left top">Predicted popularity →</div>'
    for k, pr in enumerate(props):
        inner += f'\n<div class="abs dot {p}-dot" style="left:{X(pr["pct"]["rating"])}px;top:{Y(pr["pct"]["votes"])}px"></div>'
    for t in ("Township Jazz", "The Last Province"):
        pr = next(q for q in props if q["title"] == t)
        inner += f'\n<div class="abs dl {p}-dl" style="right:{1080 - X(pr["pct"]["rating"]) + 26}px;top:{Y(pr["pct"]["votes"]) - (52 if pr["pct"]["votes"] < 10 else 14)}px">{t}</div>'
    inner += "\n" + note(p, f"Medians: rating {mr}th, popularity {mv}th percentile. Percentiles among real non-franchise films scored the same way.", 1330)
    js = f"""
  inn("#{p}-eb", 0.0, {{ y: 12, d: 0.4 }}); inn(".{p}-tl", 0.05, {{ y: 30, d: 0.5, s: 0.2 }});
  inn(".{p}-dot", 0.1, {{ y: 0, sc: 0.2, d: 0.35, s: 0.025 }});
  tl.fromTo(q("#{p}-q"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {w(2, "liked")}); inn("#{p}-ql", {w(2, "watched")}, {{ y: 10, d: 0.35 }});
  tl.fromTo(qa(".med"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.5);
  inn(".{p}-dl", {w(2, "watched")}, {{ y: 0, d: 0.35, s: 0.1 }});
  inn("#{p}-note", 0.6, {{ y: 0, d: 0.5 }});"""
    out["02-scatter17"] = wrap(proj, "02-scatter17", d, css, "\n".join([ground(p, d), stage(p, d, inner)]), js)

    note_d = "Percentiles among 1,000 real non-franchise films scored the same way, from their plot alone. Predictions, not forecasts."
    tj = next(q for q in props if q["title"] == "Township Jazz")["pct"]
    out["03-scorecard"] = scorecard_frame(proj, "03-scorecard", "d3", D[2], "An unmade movie", "Township Jazz",
        "In 1976, an American jazz legend touring South Africa must decide whether to play for whites-only crowds.",
        [("Rating", tj["rating"], AMBER, w(3, "rated")), ("Box office", tj["box"], MUTED, w(3, "percent")), ("Popularity", tj["votes"], RED, w(3, "watched"))],
        0.0, note_d)
    lp = next(q for q in props if q["title"] == "The Last Province")["pct"]
    out["04-scorecard"] = scorecard_frame(proj, "04-scorecard", "d4", D[3], "An unmade movie", "The Last Province",
        "A Syrian refugee and a Roman legionary's diary cross 1,900 years of the same border.",
        [("Rating", lp["rating"], AMBER, w(4, "all")), ("Box office", lp["box"], AMBER, w(4, "all") + 0.25), ("Popularity", lp["votes"], AMBER, w(4, "all") + 0.5)],
        0.0, note_d, stamp="Does it all", t_stamp=w(4, "does"),
        marks=[("a Roman legionary", w(4, "Roman")), ("Syrian refugee", w(4, "Syrian")), ("1,900 years", w(4, "nineteen"))], size=70)
    out["05-end"] = end_frame(proj, "05-end", "d5", D[4], ["What would", "you make?"], w(5, "Massive"))
    return proj, out


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b", "c", "d"]
    for k in which:
        proj, frames = {"a": short_a, "b": short_b, "c": short_c, "d": short_d}[k]()
        d = ROOT / proj / "compositions" / "frames"; d.mkdir(parents=True, exist_ok=True)
        src = ROOT / proj / ".hyperframes" / "frames_src"; src.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*.html"): f.unlink()
        for f in src.glob("*.html"): f.unlink()
        for name, html in frames.items():   # frames_src keeps the pristine copy finish.sh assembles from
            (d / f"{name}.html").write_text(html, encoding="utf-8"); (src / f"{name}.html").write_text(html, encoding="utf-8")
        print(proj, ", ".join(frames))
