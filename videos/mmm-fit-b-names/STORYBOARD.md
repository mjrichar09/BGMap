---
format: 1080x1920
duration: 28s
message: "Same plot, two names: the name moves the box-office forecast more than the story, so the model hides names."
arc: Hook (question) -> Name swap 1 -> Name swap 2 -> Hide the names -> What really sells -> CTA
audience: film fans and people curious about data or AI; no ML background
mode: collaborative
music: same bed family as video 1 (take 11 part A + sustained takes, G minor / D minor)
---

## Video direction

Same look as the first three videos (frame.md, Late Show): ground #0B0807 with grain and a soft top beam; ink #F3E6D0; amber #FFB547 is the one accent; marquee red #C8102E for misses and losses; Limelight titles, Oswald labels, Courier Prime numbers, Work Sans body. Vertical 1080x1920: content sits between y = 200 and y = 1450; calm phrase subtitles live in the band below. Map footage is frame-exact captures of the real page (fit plot, story map). Every number on screen is a percentile among real films, predicted from the plot alone; each frame with numbers carries a one-line source note.

## Frame 1 — Same plot

- type: hook
- blueprint: compose
- duration: 4.818s
- transition_in: cut
- status: animated
- src: compositions/frames/01-fit-hook.html
- scene: Fit plot turning; title CAN AN AI PREDICT A HIT? then a pitch card slides up.
- voiceover: "Can an AI predict a hit from the plot alone? Same plot, two names."
- asset_candidates: clips/fit_box.mp4

## Frame 2 — Vanguard

- type: benefit_highlight
- blueprint: compose
- duration: 5.194s
- transition_in: cut
- status: animated
- src: compositions/frames/02-swap.html
- scene: Pitch card (plot excerpt); name chip 'the Vanguard' with a box-office meter at 65; chip swaps to 'the Avengers' and the meter jumps to 97.
- voiceover: "The Vanguard: sixty-fifth percentile. Call them the Avengers: ninety-seventh."
- asset_candidates: none

## Frame 3 — Orphan wizard

- type: benefit_highlight
- blueprint: compose
- duration: 4.149s
- transition_in: cut
- status: animated
- src: compositions/frames/03-swap.html
- scene: Same card, second plot; 'an orphan wizard' 17 -> 'Harry Potter' 98.
- voiceover: "An orphan wizard: seventeenth. Harry Potter: ninety-eighth."
- asset_candidates: none

## Frame 4 — Hide the names

- type: pain_point
- blueprint: compose
- duration: 3.274s
- transition_in: cut
- status: animated
- src: compositions/frames/04-redact.html
- scene: The plot text with every name blacked out, then replaced by PERSON A / PERSON B; label NAMES MASKED.
- voiceover: "The name was doing the work. So I hid every name."
- asset_candidates: none

## Frame 5 — What sells

- type: benefit_highlight
- blueprint: compose
- duration: 5.513s
- transition_in: cut
- status: animated
- src: compositions/frames/05-bars.html
- scene: Ranked bars of predicted box office vs. the typical film of its year (non-franchise films): superheroes 1.9x, true sports stories 1.8x, martial-arts epics 1.7x.
- voiceover: "With the names gone, what sells? Superheroes, true sports stories, martial-arts epics."
- asset_candidates: none

## Frame 6 — End

- type: cta
- blueprint: compose
- duration: 5.268s
- transition_in: crossfade
- status: animated
- src: compositions/frames/06-end.html
- scene: End card: dimmed wide orbit of the map, the line, then the URL types on; TMDB credit line; fade to black.
- voiceover: "What would your story score? Massive Movie Map."
- asset_candidates: clips/end.mp4
