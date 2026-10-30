---
format: 1080x1080
duration: 60s
message: "An AI read 36,841 movie plots and drew a map of cinema, and it found things nobody told it. Go explore it."
arc: Hook → Product intro → Demo → Mechanism → Proof ×3 → CTA (Demo Loop with feature→benefit proof)
audience: film fans and people curious about data or AI; no ML background
mode: collaborative
music: quiet cinematic ambient, warm analog synth pad, slow, curious; low under voice
---

## Video direction

- **Palette (frame.md, Late Show):** ground `bg` #0B0807 with a faint film grain and a soft projector beam from the top on every map frame; ink `dark` #F3E6D0 for words; amber `red` #FFB547 is the one accent (numbers, lines, eyebrows, the search caret); marquee red `light` #C8102E only on Matinee cards (frame 5 clippings, frame 6 ticket header) and the "unmade" eyebrow. Matinee cards are cream #EFE6D2 with ink #2A1A14.
- **Type by role:** display = Limelight uppercase (titles); card titles = Abril Fatface; labels and eyebrows = Oswald uppercase tracked; every number and score = Courier Prime, typed or counted, never static; body = Work Sans.
- **The map footage is the hero.** Every map frame plays its captured clip full-bleed as the background layer, dimmed only where type sits. Type goes in the clip's empty quarter, never over the clip's own region labels.
- **Motion grammar:** long-tail power3 settles, no bounce, no overshoot. Each element reveals on its spoken word (cue times below are frame-local seconds from the word timings); nothing enters before the voice names it. Numbers count up; scores type on. Holds are still (subtle jitter at most).
- **Rhythm:** frame 1 is a slow cold open; 2 is a held title read; 3 and 5 are the busiest; 6 is a clean held comparison (the breather before the twist); 7 punches; 8 slows down for the idea; 9 holds still on the URL for 2.5s.
- **Caption band:** the bottom 17% belongs to captions on frames 1-8; frame 9 has no captions (the URL is the text) and puts the credits line there.
- **Never:** slideshow front-loading, floating or breathing cards, slow back-half pans over type, outlet logos on headlines, IMDb numbers, tilted display type (the frame 5 clippings are the one exception: paper at a slight angle).

## Frame 1 — 36,841 films

- type: hook
- duration: 4.38s
- transition_in: cut
- status: animated
- src: compositions/frames/01-count.html
- scene: Black. The movie cloud fades up, slowly turning; a Courier counter rolls up to 36,841.
- voiceover: "Thirty-six thousand, eight hundred forty-one films."
- asset_candidates: clips/spin.mp4

Cold open on scale. Every dot is a film. The number is the hook; nothing else on screen but the
cloud and the count. Count lands exactly as the VO says the number.

- blueprint: dataviz-countup (Adapt)
- focal: clips/spin.mp4
- roles: spin.mp4 = background (full-bleed, starts from black, dims to ~50% behind the counter)
- sfx: click, impact-bass-1
- handoff_out: spin.mp4 continues into frame 2. Full-bleed at x 0, y 0, scale 1, opacity 1, playing forward at 1x (frame 2 picks it up at media time 4.38s); dim overlay at 50%.

Adapt: keep the one-stat count-up as the signature; no push-through, the cloud itself is the instrument.
Scene 1 (0.0-1.0s): black; a projector click; the cloud fades up from black (spin.mp4 starts here) and turns. Nothing else on screen.
Scene 2 (1.0-3.3s): on "Thirty-six" a Courier counter in the upper middle (Centered, ~45% of frame width, over a soft radial dim) counts 0 to 36,841, landing exactly on "forty-one" (2.72s): value-scaled counter (counting-dynamic-scale).
Scene 3 (3.3-4.38s): on "films." the Oswald label FILMS rises in under the number; soft impact; hold still.

## Frame 2 — An AI read every plot

- type: product_intro
- duration: 4.276s
- transition_in: crossfade
- status: animated
- src: compositions/frames/02-title.html
- scene: The cloud keeps turning behind; "MASSIVE MOVIE MAP" in Limelight, then the line "placed by what their plots say".
- voiceover: "An AI read every plot, and put similar stories side by side."
- asset_candidates: clips/spin.mp4

The promise lands by beat 2: name the product and the idea in one breath. Title over the
continuing spin (same clip, later section) so the cloud never stops moving.

- blueprint: titlecard-reveal (Adapt)
- focal: clips/spin.mp4
- roles: spin.mp4 = background (continues from frame 1, dim ~55%)
- sfx: none
- handoff_in: spin.mp4 continues from frame 1. Full-bleed at x 0, y 0, scale 1, opacity 1, playing forward at 1x from media time 4.38s; dim overlay at 50% rising to 55%.

Adapt: one near-still card, not three; the moving cloud underneath carries the life.
Scene 1 (0.0-1.0s): eyebrow AN AI READ EVERY PLOT types on (Oswald, amber) in the upper third as the voice says it.
Scene 2 (1.0-2.4s): on "plot," the title MASSIVE MOVIE MAP rises in (Limelight, amber, two lines, Centered, ~70% width): per-word staggered reveal (dynamic-content-sequencing).
Scene 3 (2.4-4.28s): on "similar stories" the subline "placed by what their plots say" fades up under the title; hold still.

## Frame 3 — Search GoodFellas

- type: feature_showcase
- duration: 10.548s
- transition_in: cut
- status: animated
- src: compositions/frames/03-goodfellas.html
- scene: Search box types "GoodFellas"; the camera dives into the cloud to its clapperboard marker, amber lines fan out; neighbors stack in with Courier similarity scores.
- voiceover: "Search GoodFellas. Its closest neighbors: American Gangster. Carlito's Way. The Irishman. No genre information was given to group these as mafia movies."
- asset_candidates: clips/goodfellas.mp4, posters/goodfellas-1990.jpg

The demo: one search, one result, the neighbors. GoodFellas has no sequels, so every neighbor is a
different film. Each neighbor name appears as the VO names it: American Gangster 0.85 · Carlito's
Way 0.85 · The Irishman 0.84. The payoff line ("Nobody told it") lands
on the "GANGSTER, MAFIA" region label already visible in the clip.

- blueprint: device-surface-showcase (Adapt)
- focal: clips/goodfellas.mp4
- roles: goodfellas.mp4 = background (full-bleed, plays at 0.9x so its 8s covers the frame), goodfellas-1990.jpg = supporting (small poster under the search box)
- sfx: typing, whoosh-short

Adapt: the real surface is the map itself; the search box and neighbor card are overlays on the captured footage. Keep "the product does its core loop once": search, dive, neighbors.
Scene 1 (0.0-1.24s): search box (dark panel, amber caret) top-left (asymmetric 70/30); "GoodFellas" types on with the voice; the poster thumbnail drops in under it on "GoodFellas." The clip's dive is already running.
Scene 2 (1.24-2.78s): on "closest neighbors" a dark panel titled CLOSEST NEIGHBORS slides in from the right edge into the right third (clear of the clip's GANGSTER, MAFIA label).
Scene 3 (2.78-5.9s): each neighbor row slides in on its name with its Courier score typing on: American Gangster 0.85 (2.78), Carlito's Way 0.85 (4.04), The Irishman 0.84 (5.20).
Scene 4 (after "The Irishman"): on "No genre information" the panel holds; on "mafia movies" a thin amber underline draws under the clip's GANGSTER, MAFIA label area (svg-path-draw); hold.

## Frame 4 — Plot → numbers → map

- type: feature_showcase
- duration: 4.02s
- transition_in: wipe
- status: animated
- src: compositions/frames/04-how-it-works.html
- scene: Three stations left to right: a plot paragraph, a column of 1,024 flickering numbers, a dot landing in the cloud.
- voiceover: "Each plot becomes a thousand numbers. Those numbers become a map."
- asset_candidates: clips/spin.mp4

How it works in one sentence, no jargon. Station 1: a few lines of GoodFellas' plot
summary (paraphrased, not quoted). Station 2: the same as a strip of numbers. Station 3: one dot dropping into a
still of the cloud.

- blueprint: spatial-pan-stations (Adapt)
- focal: the plot-numbers-map triptych
- roles: spin.mp4 = supporting (a still frame in the third station)
- sfx: whoosh, click-soft

Adapt: three stations in a triptych instead of a long pan; keep the station-by-station read as the signature, each station lighting on its word.
Scene 1 (0.0-0.64s): eyebrow HOW IT WORKS; station 1 (cream plot card, a paraphrased GoodFellas plot, Work Sans) slides up on the left on "plot".
Scene 2 (0.64-2.12s): on "becomes" an amber arrow draws; station 2 fills with Courier numbers ticking in top to bottom (discrete-text-sequence) on "a thousand numbers"; label 1,024 NUMBERS.
Scene 3 (2.12-4.02s): on "Those numbers become a map" the second arrow draws and station 3 (a still of the cloud) reveals; on "map." one amber dot drops into the cloud and blooms (ambient-glow-bloom); hold.

## Frame 5 — Sequel after sequel

- type: pain_point
- duration: 8.567s
- transition_in: film-strip wipe
- status: animated
- src: compositions/frames/05-sequels.html
- scene: Real news headlines slam in one by one as typeset clippings (outlet + date in small caps); behind them Fast & Furious and Marvel posters drop and pile up; a Courier counter lands on 93%.
- voiceover: "What can we learn? Hollywood loves a sequel. In the 2010s, ninety-three percent of each year's ten biggest hits were franchise films."
- asset_candidates: posters/pile/ff-*.jpg, posters/pile/mcu-*.jpg

The recycling context before the model's own finding. Headlines are quoted verbatim, set as plain
typographic clippings (no outlet logos), each with outlet and date:
- Fortune, Sep 2016: "Will This Year Finally Cure Hollywood of its Sequel Obsession?"
- The Fiscal Times (from Business Insider), Apr 2017: "Here's Why Hollywood Is Addicted to Sequels"
- Fortune / AP, Nov 2023: "'The Marvels' struggles at box office amid superhero fatigue"
- The Week, Nov 2023: "The Marvels flop: end game for superhero box office streak?"
Posters: all 11 Fast & Furious films (2001–2023) and 25 Marvel films (2008–2025) from TMDB,
dropping and stacking like a pile of DVD cases. Stat from our data: of each year's 10 top-grossing
films (TMDB revenue), the share TMDB lists as part of a series. 1970s 51% → 2010s 93%. "Franchise
films" (not "sequels"): the share includes first entries like Iron Man (2008).

- blueprint: compose
- focal: the poster pile and the 93% counter
- roles: posters/pile/*.jpg = supporting (the pile, ~16 posters, Fast & Furious and Marvel interleaved by year), headline clippings = foreground
- sfx: pop, impact-bass-2

Compose: two layers. Clippings slam in above, posters drop and stack below; the counter lands last, on top.
Scene 0 (on "What can we learn?"): the pile is empty; a single Courier question mark blinks on under the voice, then the first headline slams in on "Hollywood".
Scene 1 (on "Hollywood loves a sequel"): the first two clippings slam in at the top (cream paper, Abril Fatface headline, red Oswald outlet and date, slight paper tilt), one per beat (kinetic-beat-slam): Fortune Sep 2016, then The Fiscal Times Apr 2017. Posters start dropping from above into the lower half, landing with a slight rotation and stacking (deterministic positions by index).
Scene 2 (1.62-3.08s): two more clippings slam over the first pair, offset: Fortune / AP Nov 2023, then The Week Nov 2023. The pile keeps growing in release order (The Fast and the Furious 2001 first; Fast X and Captain America: Brave New World last).
Scene 3 (3.08-5.06s): on "ninety-three percent" a dark panel lands center-right over the pile and the Courier counter counts 0 to 93% (counting-dynamic-scale); on "ten biggest hits" the line "of each year's top 10 hits in the 2010s" types under it.
Scene 4 (5.06-7.5s): on "franchise films" the label gets an amber underline; the pile settles; hold still.

## Frame 6 — The same movie, twice

- type: benefit_highlight
- duration: 7.284s
- transition_in: cut
- status: animated
- src: compositions/frames/06-same-movie.html
- scene: Matinee ticket card: Olympus Has Fallen and White House Down posters side by side, release dates (Mar 2013 / Jun 2013), a similarity bar fills to 0.92.
- voiceover: "And even when it's not a sequel, it's the same idea. Olympus Has Fallen. White House Down. Same year. Same plot."
- asset_candidates: posters/olympus-has-fallen-2013.jpg, posters/white-house-down-2013.jpg, clips/olympus.mp4

The punchline to frame 5: even the originals repeat. Two 2013 films, three months apart: terrorists seize the
White House, one Secret Service agent saves the President. Different titles, plot similarity 0.92.
Cream Matinee card on the dark ground, red header band "FOUND ON ITS OWN". Score counts up in Courier.

- blueprint: comparison-split (Adapt)
- focal: posters/olympus-has-fallen-2013.jpg, posters/white-house-down-2013.jpg
- roles: both posters = cutout (on the Matinee ticket), olympus.mp4 = background (dimmed ~70%, slow orbit)
- sfx: whoosh-short, impact-bass-1

Adapt: the two cards are the two posters on one Matinee ticket; keep the split-tilt entry from opposite wings as the signature.
Scene 1 (0.0-2.98s): the dimmed map clip (olympus.mp4) plays; on "same idea" the cream Matinee ticket (red header band FOUND ON ITS OWN) slides up from the bottom into the upper 70% (Centered).
Scene 2 (2.98-4.80s): on "Olympus Has Fallen" the left poster tilts in from the left wing with its title and "Mar 2013"; on "White House Down" the right poster tilts in from the right with "Jun 2013" (split-tilt-cards).
Scene 3 (4.80-7.28s): on "Same year. Same plot." the PLOT SIMILARITY bar under the ticket fills and the Courier score counts to 0.92 (stat-bars-and-fills); hold.

## Frame 7 — The least original story

- type: benefit_highlight
- duration: 5.769s
- transition_in: cut
- status: animated
- src: compositions/frames/07-dracula.html
- scene: Dracula (1931) poster; on the map, its marker sits in a dense knot; a counter rolls to 32 "films tell nearly the same story".
- voiceover: "The least original story on the map? Dracula. Thirty-two films tell almost the same plot."
- asset_candidates: clips/dracula.mp4, posters/dracula-1931.jpg

Originality = how unlike its 15 nearest plot neighbors a film is; Dracula (1931) scores lowest of
all 36,841. 32 films are ≥ 0.90 similar (Count Dracula, Bram Stoker's Dracula, Dracula: Dead and
Loving It…). Name three of them small under the counter.

- blueprint: dataviz-countup (Adapt)
- focal: posters/dracula-1931.jpg and the 32 counter
- roles: dracula.mp4 = background (full-bleed; its VAMPIRE, DRACULA knot sits right of center), dracula-1931.jpg = cutout (left column)
- sfx: impact-bass-2, click-soft

Adapt: one stat, no push-through; the map clip is the instrument.
Scene 1 (0.0-2.02s): the clip orbits Dracula's knot; the eyebrow LEAST ORIGINAL STORY ON THE MAP types on top-left with the question.
Scene 2 (2.02-2.46s): on "Dracula." the poster snaps in on the left (amber frame) and DRACULA (Limelight) lands under it; low hit.
Scene 3 (2.46-5.77s): on "Thirty-two" the Courier counter counts 0 to 32 beside "films tell almost the same plot"; on "same plot" three small titles type under it: Count Dracula, Bram Stoker's Dracula, Dracula: Dead and Loving It; hold.

## Frame 8 — Movies nobody has made

- type: benefit_highlight
- duration: 10.74s
- transition_in: crossfade
- status: animated
- src: compositions/frames/08-unmade.html
- scene: Map: a pulsing red "?" ring between two lit clusters (ancient Rome, refugee journeys), lines to each; the pitch title THE LAST PROVINCE types in.
- voiceover: "Want something original? Find the spaces where nobody has made a movie yet. A Roman legionary and a Syrian refugee, crossing the same border, nineteen hundred years apart."
- asset_candidates: clips/unmade.mp4

The site's Unmade movies tool: an empty spot in the model's space between "ancient Rome" and
refugee/migration stories (Persepolis, Dunki). Card: "THE LAST PROVINCE · ancient Rome × refugee
journeys · not made (yet)". Logline: "A Syrian refugee and a Roman legionary's diary cross 1,900
years of the same border."

- blueprint: kinetic-type-beats (Adapt)
- focal: clips/unmade.mp4 (the red "?" between the two clusters)
- roles: unmade.mp4 = background (full-bleed, plays at 0.65x to cover the frame)
- sfx: riser, ping

Adapt: one title and one pairing line, each landing on its words; the clip's "?" is the visual hook.
Scene 1 (0.0-2.44s): the clip: the "?" ring at center with red lines to the two lit clusters; the eyebrow WANT SOMETHING ORIGINAL? (red) types on top-left with the question, then UNMADE MOVIE replaces it on "nobody has made a movie yet".
Scene 2 (2.90-5.84s): the title THE LAST PROVINCE (Limelight, ink) lands top-left under the eyebrow on "A Roman legionary"; on "Syrian refugee" the pairing line "ancient Rome x refugee journeys" fades in under it (the x in amber).
Scene 3 (5.84-9.14s): on "nineteen hundred years apart" a small Courier tag "117 AD / 2017" types on beside the title; hold still while the clip finishes its slow orbit.

## Frame 9 — Go get lost

- type: cta
- duration: 4.848s
- transition_in: crossfade
- status: animated
- src: compositions/frames/09-end.html
- scene: The cloud spins wide; "GO GET LOST." then the URL massive-movie-map.mjrfx.com; credits line with the TMDB logo.
- voiceover: "Go get lost. Massive Movie Map."
- asset_candidates: clips/end.mp4, tmdb-logo.svg

End card holds ≥ 2s on the URL. Credits (small but legible): "Film data: TMDB. This product uses
the TMDB API but is not endorsed or certified by TMDB. Plots: Wikipedia, CC BY-SA."

- blueprint: titlecard-reveal (Reproduce)
- focal: clips/end.mp4
- roles: end.mp4 = background (dim ~55%), tmdb-logo.svg = supporting (credits line)
- sfx: impact-bass-1

Scene 1 (0.0-1.08s): the wide spin returns, dimmed; on "Go get lost." GO GET LOST. rises in (Limelight, amber, two lines, Centered).
Scene 2 (1.08-2.3s): on "Massive Movie Map" the URL massive-movie-map.mjrfx.com types on under it (Courier, ink); the credits line (TMDB logo, the TMDB notice, "Plots: Wikipedia, CC BY-SA") fades up in the bottom band.
Scene 3 (2.3-4.85s): hold still on the URL; at the very end the whole frame fades to black (the video's only exit).

