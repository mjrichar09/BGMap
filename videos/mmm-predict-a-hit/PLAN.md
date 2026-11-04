# Video 4 plan: "Can an AI predict a hit?" (draft, for review)

1:1, ~60s, X feed. Same look, narrator (Kokoro af_heart, 1.1x), music family and calm phrase subtitles as
videos/massive-movie-map, mmm-same-director and mmm-hollywood-pays. Doesn't repeat Hollywood Pays
(originality vs rating and money).

Numbers come from src/fit.py on the story-only map (data/movies/fit/fit.json). Pitch scores are calibrated:
each pitch is ranked against 1,000 real non-franchise films scored the same way, from their plot alone
(data/movies/fit/pitch_reference.parquet), because plot-only text scores lower than a film's full map vector
(median -5 / -10 / -23 percentile points on rating / box office / popularity). The name test used the
earlier, unmasked model (qwen3__text_plot__inst). Scores: data/movies/fit/optimal_scores.json (movies built to
maximize) and the novel-idea run below.

| # | Scene | Voiceover (draft) |
|---|---|---|
| 1 | Map colored by real box office, slowly turning | "Can an AI predict a hit movie from its plot alone?" |
| 2 | Bars: plot 33% vs genre 12% of box-office variation explained | "I trained it on thirty-six thousand plots. The story predicts a third of what a movie earns, three times more than its genre." |
| 3 | Same plot, two names: "the Vanguard" 65th -> "the Avengers" 97th percentile; "an orphan wizard" 17th -> "Harry Potter" 98th | "But it was cheating. Same plot, two names. Only the name changed, and the forecast jumped." |
| 4 | Names struck through, replaced with Person A, Person B... | "The most valuable ingredient isn't the story. It's the name. So I hid every name." |
| 5 | Ranked bars, brand-free: superheroes, true sports stories, martial-arts epics, alien invasions, disasters | "With the names gone, here's what stories really sell: superheroes, true sports stories, martial-arts epics, alien invasions, disasters." |
| 6 | Two columns. Rated highest: music and nature documentaries, true stories about racism and disability. Lowest: zombies, holiday slashers, killer dolls. Then a near-flat scatter of predicted rating vs predicted box office | "Audiences rate true stories highest, and zombies, slashers and killer dolls lowest. But being loved and making money are almost unrelated." |
| 7 | NEW: the movies nobody has made. Scatter of the 17 empty-space ideas, rating percentile (x) vs box-office percentile (y), dot size = popularity; The Last Province and Township Jazz labelled | "Then I scored the movies nobody has made yet. Most would be liked, but not watched. One would do it all: a Roman legionary and a Syrian refugee, crossing the same border nineteen hundred years apart." |
| 8 | Pitch cards: Grandfather's Orchard rating top 1%; best box-office pitch without a famous name, Wings of the Morning, 82nd percentile vs 97th for the named blockbusters | "And the perfect movie? A quiet story about a girl and her grandfather's orchard is rated in the top one percent. But no story without a famous name reached blockbuster territory." |
| 9 | End card: "What would you make?" + URL + TMDB credit | "What would you make? Massive Movie Map." |

## Scene 7 data: the 17 empty-space ideas (calibrated percentiles among real films)

Medians across all 17: rating 62nd, box office 27th, popularity 30th.

| Idea | Kind | Rating | Box office | Popularity |
|---|---|---|---|---|
| The Last Province | Unmade | 99 | 67 | 82 |
| The Equation | Desert | 88 | 70 | 42 |
| Gold Standard | Unmade | 65 | 57 | 49 |
| Field Guide | Desert | 91 | 21 | 35 |
| Season Finale | Unmade | 62 | 29 | 54 |
| The Valley Below | Horror | 54 | 25 | 57 |
| Township Jazz | Desert | 97 | 37 | 1 |
| The Heretic Princess | Unmade | 89 | 20 | 22 |
| Trinity in Color | Desert | 66 | 35 | 30 |
| Legion | Horror | 40 | 25 | 52 |
| Category Five | Desert | 44 | 61 | 11 |
| Launch Day | Desert | 5 | 38 | 70 |
| Thin Air | Unmade | 79 | 18 | 2 |
| Island 9 | Desert | 46 | 25 | 21 |
| Ingénue | Desert | 60 | 27 | 1 |
| The New Soviet Man | Horror | 62 | 8 | 10 |
| Color War | Desert | 49 | 7 | 20 |

Popularity = TMDB vote count relative to the median film of its year (plot explains 40% of it on
non-franchise films, genre 7%).

## Review notes

- Reframed (user feedback, 2026-10-31): predicted rating and box office correlate only +0.2, so the video
  says "almost unrelated", never "rise together".
- On screen: plot/genre figures are cross-validated R^2; brand-free numbers are on non-franchise films; pitch
  scores are percentiles among real films scored the same way; box office is not inflation-adjusted; the
  name test is the earlier model.
- These are predictions from plot text, not forecasts: say "the model predicts", not "would earn".
- Choose: full build (~60s), or a lean cut (scenes 3, 7, 8 + end card, ~30s).
