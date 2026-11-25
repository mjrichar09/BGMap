---
format: 1080x1920
duration: 29s
message: "The AI's biggest box-office misses are Netflix films: great-looking plots that barely played in cinemas."
arc: Hook (the experiment) -> The misses, named -> Predicted vs actual -> Why (Netflix) -> CTA
audience: film fans and people curious about data or AI; no ML background
mode: collaborative
music: same bed family as video 1 (take 11 part A + sustained takes, G minor / D minor)
---

## Video direction

Same look as the first three videos (frame.md, Late Show): ground #0B0807 with grain and a soft top beam; ink #F3E6D0; amber #FFB547 is the one accent; marquee red #C8102E for misses and losses; Limelight titles, Oswald labels, Courier Prime numbers, Work Sans body. Vertical 1080x1920: content sits between y = 200 and y = 1450; calm phrase subtitles live in the band below. Map footage is frame-exact captures of the real page (fit plot, story map). Every number on screen is a percentile among real films, predicted from the plot alone; each frame with numbers carries a one-line source note.

## Frame 1 — Plot alone

- type: hook
- blueprint: compose
- duration: 4.882s
- transition_in: cut
- status: animated
- src: compositions/frames/01-fit-hook.html
- scene: The fit plot (films placed by predicted percentile) turning slowly, colored by box office vs. its plot; title PREDICTED FROM THE PLOT ALONE.
- voiceover: "I trained an AI to predict a movie's box office from its plot alone."
- asset_candidates: clips/fit_box.mp4

## Frame 2 — Biggest misses

- type: benefit_highlight
- blueprint: compose
- duration: 6.324s
- transition_in: cut
- status: animated
- src: compositions/frames/02-misses.html
- scene: Four poster cards drop in one per spoken title, in a 2x2 grid.
- voiceover: "Its biggest misses? The Irishman. Marriage Story. The Trial of the Chicago 7. The Two Popes."
- asset_candidates: posters

## Frame 3 — Top 5% vs bottom fifth

- type: benefit_highlight
- blueprint: compose
- duration: 5.365s
- transition_in: cut
- status: animated
- src: compositions/frames/03-dumbbell.html
- scene: Four rows on a 0-100 percentile scale: amber dot at the predicted box office (98, 96, 99, 96) on 'top five percent', then a red dot falls to the actual (16, 8, 8, 6) on 'bottom fifth'.
- voiceover: "Their plots look like hits: top five percent. Their box office: the bottom fifth."
- asset_candidates: none

## Frame 4 — Netflix

- type: pain_point
- blueprint: compose
- duration: 5.983s
- transition_in: cut
- status: animated
- src: compositions/frames/04-netflix.html
- scene: Popularity row for the same four: predicted vs actual both high (The Irishman 100 -> 98). Then 'NETFLIX' stamp: released mostly to streaming; note: TMDB box office, Netflix doesn't report ticket sales.
- voiceover: "The AI isn't wrong about the stories. It just can't see that Netflix barely put them in cinemas."
- asset_candidates: none

## Frame 5 — End

- type: cta
- blueprint: compose
- duration: 6.249s
- transition_in: crossfade
- status: animated
- src: compositions/frames/05-end.html
- scene: End card: dimmed wide orbit of the map, the line, then the URL types on; TMDB credit line; fade to black.
- voiceover: "See what your favorite movie's plot predicts. Massive Movie Map."
- asset_candidates: clips/end.mp4
