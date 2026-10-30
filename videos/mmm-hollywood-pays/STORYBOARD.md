---
format: 1080x1080
duration: 50s
message: "Audiences rate original movies higher, but Hollywood's money follows the crowded, familiar ones."
arc: Hook → Finding (rating) → Twist (money) → Surprise (true stories) → Money map → Per-dollar ranking → Trend over time → CTA
audience: film fans and people curious about data or AI; no ML background
mode: collaborative
music: same bed family as video 1 (take 11 part A + sustained takes, G minor / D minor)
---

## Video direction

Same as the first video (frame.md, Late Show): ground #0B0807 with grain and a soft top beam; ink #F3E6D0; amber #FFB547 is the one accent; marquee red #C8102E for Matinee cards and "loss" values; Limelight titles, Oswald labels, Courier Prime numbers, Work Sans body. Map footage is the hero on map frames; charts are clean SVG on the dark ground, every bar and line grows on its spoken word, values count up. Each chart carries a one-line source note in small muted type (what was measured). Calm phrase subtitles in the bottom band (keep content above y = 900).

## Frame 1 — Color by originality

- type: hook
- blueprint: compose
- duration: 6.085s
- transition_in: cut
- status: animated
- src: compositions/frames/01-orig.html
- scene: The cloud colored by originality (viridis: deep blue = crowded, yellow = original) turning; a legend bar CROWDED → ORIGINAL draws on.
- voiceover: "Color the movie map by originality: how unlike its closest neighbors each plot is."
- asset_candidates: clips/orig.mp4

## Frame 2 — Rated higher

- type: benefit_highlight
- blueprint: dataviz-countup
- duration: 7.583s
- transition_in: cut
- status: animated
- src: compositions/frames/02-rating.html
- scene: Vertical bar chart, five bars from MOST CROWDED to MOST ORIGINAL, average TMDB rating 6.47 → 6.52 → 6.56 → 6.64 → 6.72, growing left to right as "climb at every step" is spoken (axis from 6.3, labelled); orig.mp4 dimmed behind.
- voiceover: "Audiences rate original movies higher. From the most crowded fifth to the most original, ratings climb at every step."
- asset_candidates: data/stats.json (fifths.rating), clips/orig.mp4

## Frame 3 — But earn less

- type: pain_point
- blueprint: dataviz-countup
- duration: 6.921s
- transition_in: cut
- status: animated
- src: compositions/frames/03-boxoffice.html
- scene: Same five bars morph to median box office: $33.5M → $21.3M → $18.6M → $17.9M → $16.0M (falling); the first and last values count up; note "median TMDB box office, not adjusted for inflation".
- voiceover: "But the crowded ones earn twice as much: a median box office of thirty-three million dollars, against sixteen."
- asset_candidates: data/stats.json (fifths.median_box_office_m)

## Frame 4 — True stories

- type: benefit_highlight
- blueprint: compose
- duration: 7.476s
- transition_in: crossfade
- status: animated
- src: compositions/frames/04-true.html
- scene: Map (still colored by originality) with the five most original popular films starred; a row of four posters (The King's Speech, The Social Network, The Big Short, Hidden Figures) slides in name by name; "TRUE STORIES" lands.
- voiceover: "And the most original hits are based on true stories: The King's Speech. The Social Network. The Big Short. Hidden Figures."
- asset_candidates: clips/truth.mp4, posters/the-king-s-speech-2010.jpg, posters/the-social-network-2010.jpg, posters/the-big-short-2015.jpg, posters/hidden-figures-2016.jpg

## Frame 5 — Superheroes

- type: benefit_highlight
- blueprint: dataviz-countup
- duration: 6.153s
- transition_in: cut
- status: animated
- src: compositions/frames/05-revenue.html
- scene: The map recolored by box office; "$268M" counts up with "median box office per superhero film" and the Avengers: Endgame poster.
- voiceover: "Follow the money, and superheroes lead: a median of two hundred sixty-eight million dollars a film."
- asset_candidates: clips/revenue.mp4, posters/avengers-endgame-2019.jpg

## Frame 6 — Per dollar

- type: benefit_highlight
- blueprint: compose
- duration: 9.14s
- transition_in: cut
- status: animated
- src: compositions/frames/06-roi.html
- scene: Horizontal bar chart of box office ÷ budget (median per cluster) over dimmed roi.mp4: James Bond 5.7×, Slashers 4.1×, Korean thrillers 4.0× grow in amber; a dashed BREAK EVEN line at 1×; Political dramas 1.1× and Apartheid dramas 0.7× in red near it. Skyfall and Halloween posters small beside the top bars.
- voiceover: "But per dollar spent, James Bond returns five point seven times his budget. Slashers, four times. Political dramas barely break even."
- asset_candidates: data/stats.json (roi_top, roi_bottom), clips/roi.mp4, posters/skyfall-2012.jpg, posters/halloween-1978.jpg

## Frame 7 — Seventy years

- type: benefit_highlight
- blueprint: compose
- duration: 6.815s
- transition_in: crossfade
- status: animated
- src: compositions/frames/07-trends.html
- scene: The map time-lapse 1950 → 2025 (films appearing year by year) with a big Courier year counter; an inset line chart draws Westerns 10% → 1% (falling, red) and Thrillers 12% → 26% (rising, amber) decade by decade in sync.
- voiceover: "And over seventy years, westerns fell from one film in ten... to one in a hundred, while thrillers more than doubled."
- asset_candidates: clips/timelapse.mp4, data/stats.json (trends)

## Frame 8 — Your way

- type: cta
- blueprint: titlecard-reveal
- duration: 5.147s
- transition_in: crossfade
- status: animated
- src: compositions/frames/08-end.html
- scene: Wide spin, dimmed; "COLOR THE MAP YOUR WAY" then the URL; TMDB credits line.
- voiceover: "Color the map your way. Massive Movie Map."
- asset_candidates: clips/end.mp4, tmdb-logo.svg
