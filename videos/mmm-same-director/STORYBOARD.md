---
format: 1080x1080
duration: 45s
message: "The model can tell which filmmakers and stars keep making the same movie: Ridley Scott never repeats, Jason Statham always does."
arc: Hook → Mechanism (PCA) → Proof A (range) → Proof B (typecast) → Ranking chart → Franchise twist → CTA
audience: film fans and people curious about data or AI; no ML background
mode: collaborative
music: same bed family as video 1 (take 11 part A + sustained takes, G minor / D minor)
---

## Video direction

Same as the first video (frame.md, Late Show): ground #0B0807 with grain and a soft top beam; ink #F3E6D0; amber #FFB547 is the one accent; marquee red #C8102E for Matinee cards and the "typecast" side of charts; Limelight titles, Oswald labels, Courier Prime numbers, Work Sans body. Map footage is the hero on map frames; charts are drawn as clean SVG on the dark ground. Every element reveals on its spoken word; numbers count up; no bounce; holds are still. Calm phrase subtitles in the bottom band (keep content above y = 900).

## Frame 1 — Never the same

- type: hook
- blueprint: kinetic-type-beats
- duration: 5.807s
- transition_in: cut
- status: animated
- src: compositions/frames/01-hook.html
- scene: The whole cloud turning; "NEVER THE SAME MOVIE TWICE" lands, then "…AGAIN AND AGAIN" replaces it.
- voiceover: "Some filmmakers never make the same movie twice. Others make it again and again."
- asset_candidates: clips/spin.mp4

## Frame 2 — The two biggest differences

- type: product_intro
- blueprint: compose
- duration: 6.964s
- transition_in: crossfade
- status: animated
- src: compositions/frames/02-pca.html
- scene: Animated chart: 1,800 film dots settle onto two axes; the axis lines draw on and their ends label: ROMANCE · COMEDY ↔ ACTION · THRILLER, CRIME · THRILLER ↔ ANIMATION.
- voiceover: "Fold thirty-six thousand plots onto their two biggest differences: romance to action, and crime to animation."
- asset_candidates: data/stats.json (pca.points, x_axis, y_axis)

## Frame 3 — Ridley Scott

- type: feature_showcase
- blueprint: compose
- duration: 9.759s
- transition_in: cut
- status: animated
- src: compositions/frames/03-ridley.html
- scene: Map with only Ridley Scott's 31 films lit, scattered everywhere; a strip of posters (Alien, Gladiator, Black Hawk Down, The Martian) drops in name by name; the Courier stat "0.48" lands with "plot similarity".
- voiceover: "Ridley Scott's thirty-one films land all over the map. Alien. Gladiator. Black Hawk Down. The Martian. Plot similarity: zero point four eight."
- asset_candidates: clips/ridley.mp4, posters/alien-1979.jpg, posters/gladiator-2000.jpg, posters/black-hawk-down-2001.jpg, posters/the-martian-2015.jpg

## Frame 4 — Jason Statham

- type: feature_showcase
- blueprint: compose
- duration: 9.993s
- transition_in: cut
- status: animated
- src: compositions/frames/04-statham.html
- scene: Map with Jason Statham's 43 films lit; the camera pushes toward where most of them crowd; posters (Crank, The Transporter, The Expendables) drop in; "0.69" lands in marquee red.
- voiceover: "Jason Statham's forty-three films? Most of them crowd one corner. Crank. The Transporter. The Expendables. Plot similarity: zero point six nine."
- asset_candidates: clips/statham.mp4, posters/crank-2006.jpg, posters/the-transporter-2002.jpg, posters/the-expendables-2010.jpg

## Frame 5 — The ranking

- type: benefit_highlight
- blueprint: compose
- duration: 6.303s
- transition_in: film-strip wipe
- status: animated
- src: compositions/frames/05-ranking.html
- scene: Animated horizontal bar chart of plot similarity between each star's films: WIDEST RANGE at top (Cumberbatch 0.45, Blanchett 0.49, Johansson 0.49, Matt Damon 0.49, Adam Driver 0.49) and MOST TYPECAST below (Statham 0.69, Paul Walker 0.61, Jennifer Aniston 0.60, Paul Rudd 0.60, Michelle Rodriguez 0.59, Vin Diesel 0.59). Cumberbatch and Statham bars glow on their names.
- voiceover: "Among the biggest stars, Benedict Cumberbatch has the widest range. Jason Statham, the narrowest."
- asset_candidates: data/stats.json (widest_range, most_typecast)

## Frame 6 — One franchise

- type: benefit_highlight
- blueprint: compose
- duration: 6.964s
- transition_in: crossfade
- status: animated
- src: compositions/frames/06-franchise.html
- scene: The typecast bars stay; Walker, Rodriguez and Diesel bars light up red one by one; a small stack of Fast & Furious posters slides in beside them; "ONE FRANCHISE" lands.
- voiceover: "Also near the top: Paul Walker, Michelle Rodriguez and Vin Diesel. One franchise can typecast a whole cast."
- asset_candidates: data/stats.json (most_typecast), posters/ff-2001-the-fast-and-the-furious.jpg, posters/ff-2011-fast-five.jpg, posters/ff-2023-fast-x.jpg

## Frame 7 — Look it up

- type: cta
- blueprint: titlecard-reveal
- duration: 5.488s
- transition_in: crossfade
- status: animated
- src: compositions/frames/07-end.html
- scene: Wide spin, dimmed; "LOOK UP YOUR FAVORITE DIRECTOR" then the URL; TMDB credits line.
- voiceover: "Look up your favorite director. Massive Movie Map."
- asset_candidates: clips/end.mp4, tmdb-logo.svg
