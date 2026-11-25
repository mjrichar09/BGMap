---
format: 1080x1920
duration: 28s
message: "The stories audiences love and the stories that make money are almost unrelated."
arc: Hook (loved) -> Money -> Almost unrelated (scatter) -> Lowest rated -> CTA
audience: film fans and people curious about data or AI; no ML background
mode: collaborative
music: same bed family as video 1 (take 11 part A + sustained takes, G minor / D minor)
---

## Video direction

Same look as the first three videos (frame.md, Late Show): ground #0B0807 with grain and a soft top beam; ink #F3E6D0; amber #FFB547 is the one accent; marquee red #C8102E for misses and losses; Limelight titles, Oswald labels, Courier Prime numbers, Work Sans body. Vertical 1080x1920: content sits between y = 200 and y = 1450; calm phrase subtitles live in the band below. Map footage is frame-exact captures of the real page (fit plot, story map). Every number on screen is a percentile among real films, predicted from the plot alone; each frame with numbers carries a one-line source note.

## Frame 1 — Rated highest

- type: hook
- blueprint: compose
- duration: 6.951s
- transition_in: cut
- status: animated
- src: compositions/frames/01-list.html
- scene: Fit plot, 2D, dimmed; ranked list RATED HIGHEST with three entries landing on their words.
- voiceover: "What stories do audiences rate highest? Concert films, nature documentaries, music documentaries."
- asset_candidates: clips/fit_2d.mp4

## Frame 2 — Makes money

- type: benefit_highlight
- blueprint: compose
- duration: 4.468s
- transition_in: cut
- status: animated
- src: compositions/frames/02-list.html
- scene: Same list frame, MAKES MONEY, three entries.
- voiceover: "What makes money? Superheroes, martial-arts epics, ancient Rome."
- asset_candidates: none

## Frame 3 — Almost unrelated

- type: benefit_highlight
- blueprint: compose
- duration: 6.133s
- transition_in: cut
- status: animated
- src: compositions/frames/03-scatter.html
- scene: The fit plot in 2D undimmed: predicted rating across, predicted box office up; 36,841 counts up; correlation +0.2 lands on 'almost unrelated'.
- voiceover: "I scored thirty-six thousand plots on both. Being loved and making money are almost unrelated."
- asset_candidates: clips/fit_2d.mp4

## Frame 4 — Rated lowest

- type: pain_point
- blueprint: compose
- duration: 4.873s
- transition_in: cut
- status: animated
- src: compositions/frames/04-list.html
- scene: List frame, RATED LOWEST, red accents.
- voiceover: "And the stories rated lowest? Gore, psycho killers and horror anthologies."
- asset_candidates: none

## Frame 5 — End

- type: cta
- blueprint: compose
- duration: 5.695s
- transition_in: crossfade
- status: animated
- src: compositions/frames/05-end.html
- scene: End card: dimmed wide orbit of the map, the line, then the URL types on; TMDB credit line; fade to black.
- voiceover: "Explore the plot fit yourself. Massive Movie Map."
- asset_candidates: clips/end.mp4
