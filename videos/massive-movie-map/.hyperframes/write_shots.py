"""One-off: write the Video direction block and per-frame shot sequences into STORYBOARD.md."""
import pathlib
import re

p = pathlib.Path("STORYBOARD.md")
s = p.read_text(encoding="utf-8")
s = s.replace("duration: 45s", "duration: 56s", 1)

DIRECTION = """
## Video direction

- **Palette (frame.md, Late Show):** ground `bg` #0B0807 with a faint film grain and a soft projector beam from the top on every map frame; ink `dark` #F3E6D0 for words; amber `red` #FFB547 is the one accent (numbers, lines, eyebrows, the search caret); marquee red `light` #C8102E only on Matinee cards (frame 5 clippings, frame 6 ticket header) and the "unmade" eyebrow. Matinee cards are cream #EFE6D2 with ink #2A1A14.
- **Type by role:** display = Limelight uppercase (titles); card titles = Abril Fatface; labels and eyebrows = Oswald uppercase tracked; every number and score = Courier Prime, typed or counted, never static; body = Work Sans.
- **The map footage is the hero.** Every map frame plays its captured clip full-bleed as the background layer, dimmed only where type sits. Type goes in the clip's empty quarter, never over the clip's own region labels.
- **Motion grammar:** long-tail power3 settles, no bounce, no overshoot. Each element reveals on its spoken word (cue times below are frame-local seconds from the word timings); nothing enters before the voice names it. Numbers count up; scores type on. Holds are still (subtle jitter at most).
- **Rhythm:** frame 1 is a slow cold open; 2 is a held title read; 3 and 5 are the busiest; 6 is a clean held comparison (the breather before the twist); 7 punches; 8 slows down for the idea; 9 holds still on the URL for 2.5s.
- **Caption band:** the bottom 17% belongs to captions on frames 1-8; frame 9 has no captions (the URL is the text) and puts the credits line there.
- **Never:** slideshow front-loading, floating or breathing cards, slow back-half pans over type, outlet logos on headlines, IMDb numbers, tilted display type (the frame 5 clippings are the one exception: paper at a slight angle).
"""
s = s.replace("\n## Frame 1 —", DIRECTION + "\n## Frame 1 —", 1)

ADD = {
1: """- blueprint: dataviz-countup (Adapt)
- focal: clips/spin.mp4
- roles: spin.mp4 = background (full-bleed, starts from black, dims to ~50% behind the counter)
- sfx: projector-click, soft-impact
- handoff_out: spin.mp4 continues into frame 2. Full-bleed at x 0, y 0, scale 1, opacity 1, playing forward at 1x (frame 2 picks it up at media time 4.38s); dim overlay at 50%.

Adapt: keep the one-stat count-up as the signature; no push-through, the cloud itself is the instrument.
Scene 1 (0.0-1.0s): black; a projector click; the cloud fades up from black (spin.mp4 starts here) and turns. Nothing else on screen.
Scene 2 (1.0-3.3s): on "Thirty-six" a Courier counter in the upper middle (Centered, ~45% of frame width, over a soft radial dim) counts 0 to 36,841, landing exactly on "forty-one" (2.72s): value-scaled counter (counting-dynamic-scale).
Scene 3 (3.3-4.38s): on "films." the Oswald label FILMS rises in under the number; soft impact; hold still.
""",
2: """- blueprint: titlecard-reveal (Adapt)
- focal: clips/spin.mp4
- roles: spin.mp4 = background (continues from frame 1, dim ~55%)
- sfx: none
- handoff_in: spin.mp4 continues from frame 1. Full-bleed at x 0, y 0, scale 1, opacity 1, playing forward at 1x from media time 4.38s; dim overlay at 50% rising to 55%.

Adapt: one near-still card, not three; the moving cloud underneath carries the life.
Scene 1 (0.0-1.0s): eyebrow AN AI READ EVERY PLOT types on (Oswald, amber) in the upper third as the voice says it.
Scene 2 (1.0-2.4s): on "plot," the title MASSIVE MOVIE MAP rises in (Limelight, amber, two lines, Centered, ~70% width): per-word staggered reveal (dynamic-content-sequencing).
Scene 3 (2.4-4.28s): on "similar stories" the subline "placed by what their plots say" fades up under the title; hold still.
""",
3: """- blueprint: device-surface-showcase (Adapt)
- focal: clips/goodfellas.mp4
- roles: goodfellas.mp4 = background (full-bleed, plays at 0.9x so its 8s covers the frame), goodfellas-1990.jpg = supporting (small poster under the search box)
- sfx: key-typing, whoosh-soft

Adapt: the real surface is the map itself; the search box and neighbor card are overlays on the captured footage. Keep "the product does its core loop once": search, dive, neighbors.
Scene 1 (0.0-1.24s): search box (dark panel, amber caret) top-left (asymmetric 70/30); "GoodFellas" types on with the voice; the poster thumbnail drops in under it on "GoodFellas." The clip's dive is already running.
Scene 2 (1.24-2.78s): on "closest neighbors" a dark panel titled CLOSEST NEIGHBORS slides in from the right edge into the right third (clear of the clip's GANGSTER, MAFIA label).
Scene 3 (2.78-5.9s): each neighbor row slides in on its name with its Courier score typing on: American Gangster 0.85 (2.78), Carlito's Way 0.85 (4.04), The Irishman 0.84 (5.20).
Scene 4 (6.16-8.9s): on "Nobody told it" the panel holds; on "gangster films" (7.62) a thin amber underline draws under the clip's GANGSTER, MAFIA label area (svg-path-draw); hold.
""",
4: """- blueprint: spatial-pan-stations (Adapt)
- focal: the plot-numbers-map triptych
- roles: spin.mp4 = supporting (a still frame in the third station)
- sfx: whoosh-soft, tick

Adapt: three stations in a triptych instead of a long pan; keep the station-by-station read as the signature, each station lighting on its word.
Scene 1 (0.0-0.64s): eyebrow HOW IT WORKS; station 1 (cream plot card, a paraphrased GoodFellas plot, Work Sans) slides up on the left on "plot".
Scene 2 (0.64-2.12s): on "becomes" an amber arrow draws; station 2 fills with Courier numbers ticking in top to bottom (discrete-text-sequence) on "a thousand numbers"; label 1,024 NUMBERS.
Scene 3 (2.12-4.02s): on "Those numbers become a map" the second arrow draws and station 3 (a still of the cloud) reveals; on "map." one amber dot drops into the cloud and blooms (ambient-glow-bloom); hold.
""",
5: """- blueprint: compose
- focal: the poster pile and the 93% counter
- roles: posters/pile/*.jpg = supporting (the pile, ~16 posters, Fast & Furious and Marvel interleaved by year), headline clippings = foreground
- sfx: paper-slap x4, soft-impact

Compose: two layers. Clippings slam in above, posters drop and stack below; the counter lands last, on top.
Scene 1 (0.0-1.62s): on "Hollywood loves a sequel" the first two clippings slam in at the top (cream paper, Abril Fatface headline, red Oswald outlet and date, slight paper tilt), one per beat (kinetic-beat-slam): Fortune Sep 2016, then The Fiscal Times Apr 2017. Posters start dropping from above into the lower half, landing with a slight rotation and stacking (deterministic positions by index).
Scene 2 (1.62-3.08s): two more clippings slam over the first pair, offset: Fortune / AP Nov 2023, then The Week Nov 2023. The pile keeps growing in release order (The Fast and the Furious 2001 first; Fast X and Captain America: Brave New World last).
Scene 3 (3.08-5.06s): on "ninety-three percent" a dark panel lands center-right over the pile and the Courier counter counts 0 to 93% (counting-dynamic-scale); on "ten biggest hits" the line "of each year's top 10 hits in the 2010s" types under it.
Scene 4 (5.06-7.5s): on "franchise films" the label gets an amber underline; the pile settles; hold still.
""",
6: """- blueprint: comparison-split (Adapt)
- focal: posters/olympus-has-fallen-2013.jpg, posters/white-house-down-2013.jpg
- roles: both posters = cutout (on the Matinee ticket), olympus.mp4 = background (dimmed ~70%, slow orbit)
- sfx: ticket-tear, soft-impact

Adapt: the two cards are the two posters on one Matinee ticket; keep the split-tilt entry from opposite wings as the signature.
Scene 1 (0.0-2.98s): the dimmed map clip (olympus.mp4) plays; on "same idea" the cream Matinee ticket (red header band FOUND ON ITS OWN) slides up from the bottom into the upper 70% (Centered).
Scene 2 (2.98-4.80s): on "Olympus Has Fallen" the left poster tilts in from the left wing with its title and "Mar 2013"; on "White House Down" the right poster tilts in from the right with "Jun 2013" (split-tilt-cards).
Scene 3 (4.80-7.28s): on "Same year. Same plot." the PLOT SIMILARITY bar under the ticket fills and the Courier score counts to 0.92 (stat-bars-and-fills); hold.
""",
7: """- blueprint: dataviz-countup (Adapt)
- focal: posters/dracula-1931.jpg and the 32 counter
- roles: dracula.mp4 = background (full-bleed; its VAMPIRE, DRACULA knot sits right of center), dracula-1931.jpg = cutout (left column)
- sfx: low-hit, tick

Adapt: one stat, no push-through; the map clip is the instrument.
Scene 1 (0.0-2.02s): the clip orbits Dracula's knot; the eyebrow LEAST ORIGINAL STORY ON THE MAP types on top-left with the question.
Scene 2 (2.02-2.46s): on "Dracula." the poster snaps in on the left (amber frame) and DRACULA (Limelight) lands under it; low hit.
Scene 3 (2.46-5.77s): on "Thirty-two" the Courier counter counts 0 to 32 beside "films tell almost the same plot"; on "same plot" three small titles type under it: Count Dracula, Bram Stoker's Dracula, Dracula: Dead and Loving It; hold.
""",
8: """- blueprint: kinetic-type-beats (Adapt)
- focal: clips/unmade.mp4 (the red "?" between the two clusters)
- roles: unmade.mp4 = background (full-bleed, plays at 0.65x to cover the frame)
- sfx: riser-soft, ping

Adapt: one title and one pairing line, each landing on its words; the clip's "?" is the visual hook.
Scene 1 (0.0-2.44s): the clip: the "?" ring at center with red lines to the two lit clusters; the eyebrow UNMADE MOVIE (red) types on top-left on "nobody has made yet".
Scene 2 (2.90-5.84s): the title THE LAST PROVINCE (Limelight, ink) lands top-left under the eyebrow on "A Roman legionary"; on "Syrian refugee" the pairing line "ancient Rome x refugee journeys" fades in under it (the x in amber).
Scene 3 (5.84-9.14s): on "nineteen hundred years apart" a small Courier tag "117 AD / 2017" types on beside the title; hold still while the clip finishes its slow orbit.
""",
9: """- blueprint: titlecard-reveal (Reproduce)
- focal: clips/end.mp4
- roles: end.mp4 = background (dim ~55%), tmdb-logo.svg = supporting (credits line)
- sfx: soft-impact

Scene 1 (0.0-1.08s): the wide spin returns, dimmed; on "Go get lost." GO GET LOST. rises in (Limelight, amber, two lines, Centered).
Scene 2 (1.08-2.3s): on "Massive Movie Map" the URL massive-movie-map.vercel.app types on under it (Courier, ink); the credits line (TMDB logo, the TMDB notice, "Plots: Wikipedia, CC BY-SA") fades up in the bottom band.
Scene 3 (2.3-4.85s): hold still on the URL; at the very end the whole frame fades to black (the video's only exit).
""",
}

parts = re.split(r"(?=^## Frame \d+ — )", s, flags=re.M)
out = []
for part in parts:
    m = re.match(r"## Frame (\d+) — ", part)
    if m:
        part = re.sub(r"^- blueprint: .*\n", "", part, flags=re.M)
        part = part.rstrip("\n") + "\n\n" + ADD[int(m.group(1))] + "\n"
    out.append(part)
s = "".join(out)
p.write_text(s, encoding="utf-8")
print(len(re.findall(r"^Scene \d", s, flags=re.M)), "scene lines")
