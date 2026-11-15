"""Write SCRIPT.md, STORYBOARD.md and BRIEF.md for the four "Can an AI predict a hit?" shorts
(videos/mmm-fit-a-misses, -b-names, -c-loved, -d-unmade) from one spec. Run from videos/:

    python mmm-fit-shorts.py            # (re)write the docs; durations come from audio_meta.json if present

Numbers: films.json `fit` (src/export.py fit_percentiles), manifest fit summary, fit/proposals.json,
and the earlier unmasked model's name test (see mmm-predict-a-hit/PLAN.md).
"""
import json
import pathlib

DIRECTION = (
    "Same look as the first three videos (frame.md, Late Show): ground #0B0807 with grain and a soft top beam; "
    "ink #F3E6D0; amber #FFB547 is the one accent; marquee red #C8102E for misses and losses; Limelight titles, "
    "Oswald labels, Courier Prime numbers, Work Sans body. Vertical 1080x1920: content sits between y = 200 and "
    "y = 1450; calm phrase subtitles live in the band below. Map footage is frame-exact captures of the real page "
    "(fit plot, story map). Every number on screen is a percentile among real films, predicted from the plot alone; "
    "each frame with numbers carries a one-line source note."
)
END = "End card: dimmed wide orbit of the map, the line, then the URL types on; TMDB credit line; fade to black."

SHORTS = {
    "mmm-fit-a-misses": {
        "message": "The AI's biggest box-office misses are Netflix films: great-looking plots that barely played in cinemas.",
        "arc": "Hook (the experiment) -> The misses, named -> Predicted vs actual -> Why (Netflix) -> CTA",
        "frames": [
            ("hook", "Plot alone", "fit-hook", "clips/fit_box.mp4",
             "I trained an AI to predict a movie's box office from its plot alone.",
             "The fit plot (films placed by predicted percentile) turning slowly, colored by box office vs. its plot; title PREDICTED FROM THE PLOT ALONE."),
            ("benefit_highlight", "Biggest misses", "misses", "posters",
             "Its biggest misses? The Irishman. Marriage Story. The Trial of the Chicago 7. The Two Popes.",
             "Four poster cards drop in one per spoken title, in a 2x2 grid."),
            ("benefit_highlight", "Top 5% vs bottom fifth", "dumbbell", "",
             "Their plots look like hits: top five percent. Their box office: the bottom fifth.",
             "Four rows on a 0-100 percentile scale: amber dot at the predicted box office (98, 96, 99, 96) on 'top five percent', then a red dot falls to the actual (16, 8, 8, 6) on 'bottom fifth'."),
            ("pain_point", "Netflix", "netflix", "",
             "The AI isn't wrong about the stories. It just can't see that Netflix barely put them in cinemas.",
             "Popularity row for the same four: predicted vs actual both high (The Irishman 100 -> 98). Then 'NETFLIX' stamp: released mostly to streaming; note: TMDB box office, Netflix doesn't report ticket sales."),
            ("cta", "End", "end", "clips/end.mp4",
             "See what your favorite movie's plot predicts. Massive Movie Map.", END),
        ],
    },
    "mmm-fit-b-names": {
        "message": "Same plot, two names: the name moves the box-office forecast more than the story, so the model hides names.",
        "arc": "Hook (question) -> Name swap 1 -> Name swap 2 -> Hide the names -> What really sells -> CTA",
        "frames": [
            ("hook", "Same plot", "fit-hook", "clips/fit_box.mp4",
             "Can an AI predict a hit from the plot alone? Same plot, two names.",
             "Fit plot turning; title CAN AN AI PREDICT A HIT? then a pitch card slides up."),
            ("benefit_highlight", "Vanguard", "swap", "",
             "The Vanguard: sixty-fifth percentile. Call them the Avengers: ninety-seventh.",
             "Pitch card (plot excerpt); name chip 'the Vanguard' with a box-office meter at 65; chip swaps to 'the Avengers' and the meter jumps to 97."),
            ("benefit_highlight", "Orphan wizard", "swap", "",
             "An orphan wizard: seventeenth. Harry Potter: ninety-eighth.",
             "Same card, second plot; 'an orphan wizard' 17 -> 'Harry Potter' 98."),
            ("pain_point", "Hide the names", "redact", "",
             "The name was doing the work. So I hid every name.",
             "The plot text with every name blacked out, then replaced by PERSON A / PERSON B; label NAMES MASKED."),
            ("benefit_highlight", "What sells", "bars", "",
             "With the names gone, what sells? Superheroes, true sports stories, martial-arts epics.",
             "Ranked bars of predicted box office vs. the typical film of its year (non-franchise films): superheroes 1.9x, true sports stories 1.8x, martial-arts epics 1.7x."),
            ("cta", "End", "end", "clips/end.mp4",
             "What would your story score? Massive Movie Map.", END),
        ],
    },
    "mmm-fit-c-loved": {
        "message": "The stories audiences love and the stories that make money are almost unrelated.",
        "arc": "Hook (loved) -> Money -> Almost unrelated (scatter) -> Lowest rated -> CTA",
        "frames": [
            ("hook", "Rated highest", "list", "clips/fit_2d.mp4",
             "What stories do audiences rate highest? Concert films, nature documentaries, music documentaries.",
             "Fit plot, 2D, dimmed; ranked list RATED HIGHEST with three entries landing on their words."),
            ("benefit_highlight", "Makes money", "list", "",
             "What makes money? Superheroes, martial-arts epics, ancient Rome.",
             "Same list frame, MAKES MONEY, three entries."),
            ("benefit_highlight", "Almost unrelated", "scatter", "clips/fit_2d.mp4",
             "I scored thirty-six thousand plots on both. Being loved and making money are almost unrelated.",
             "The fit plot in 2D undimmed: predicted rating across, predicted box office up; 36,841 counts up; correlation +0.2 lands on 'almost unrelated'."),
            ("pain_point", "Rated lowest", "list", "",
             "And the stories rated lowest? Gore, psycho killers and horror anthologies.",
             "List frame, RATED LOWEST, red accents."),
            ("cta", "End", "end", "clips/end.mp4",
             "Explore the plot fit yourself. Massive Movie Map.", END),
        ],
    },
    "mmm-fit-d-unmade": {
        "message": "The movies nobody has made would mostly be liked but not watched; one would do it all.",
        "arc": "Hook (gaps) -> Liked not watched -> Township Jazz -> The Last Province -> CTA",
        "frames": [
            ("hook", "The gaps", "fit-hook", "clips/gaps.mp4",
             "I found the gaps on the map, stories nobody has filmed, and had the AI score them.",
             "Story map turning with the unmade ideas starred; title MOVIES NOBODY HAS MADE."),
            ("benefit_highlight", "Liked, not watched", "scatter17", "",
             "Most would be liked, but not watched.",
             "17 ideas as dots: predicted rating (across) vs popularity (up); medians 62nd and 30th marked."),
            ("benefit_highlight", "Township Jazz", "scorecard", "",
             "Township Jazz: rated in the top three percent, watched by almost nobody.",
             "Scorecard: logline, three percentile bars: rating 97, box office 37, popularity 1."),
            ("benefit_highlight", "The Last Province", "scorecard", "",
             "But one does it all: a Roman legionary and a Syrian refugee, crossing the same border nineteen hundred years apart.",
             "Scorecard: logline, bars rating 99, box office 67, popularity 82, all amber."),
            ("cta", "End", "end", "clips/end.mp4",
             "What would you make? Massive Movie Map.", END),
        ],
    },
}

for proj, s in SHORTS.items():
    root = pathlib.Path(proj)
    meta = root / "audio_meta.json"
    durs = {}
    if meta.exists():
        durs = {v["frame"]: v["duration_s"] for v in json.loads(meta.read_text(encoding="utf-8"))["voices"]}
    total = sum(durs.values()) or 25
    script = [f"# SCRIPT — {proj}\n", "**Voice:** af_heart (Kokoro, local), speed 1.1",
              "**Voice settings:** speed 1.1",
              "**Voice direction:** Same narrator as the earlier videos: warm, curious, a little wry on the reveals.\n", "---\n"]
    board = ["---", "format: 1080x1920", f"duration: {round(total)}s", f'message: "{s["message"]}"', f"arc: {s['arc']}",
             "audience: film fans and people curious about data or AI; no ML background", "mode: collaborative",
             "music: same bed family as video 1 (take 11 part A + sustained takes, G minor / D minor)", "---", "",
             "## Video direction", "", DIRECTION, ""]
    for k, (typ, title, kind, asset, vo, scene) in enumerate(s["frames"], 1):
        slug = f"{k:02d}-{kind}"
        script += [f"## Line {k} — {title} (Frame {k})\n", f"    {vo}\n"]
        board += [f"## Frame {k} — {title}", "", f"- type: {typ}", "- blueprint: compose",
                  f"- duration: {durs.get(k, 5.0)}s", f"- transition_in: {'cut' if k == 1 else 'crossfade' if kind == 'end' else 'cut'}",
                  "- status: built", f"- src: compositions/frames/{slug}.html", f"- scene: {scene}", f'- voiceover: "{vo}"',
                  f"- asset_candidates: {asset or 'none'}", ""]
    (root / "SCRIPT.md").write_text("\n".join(script), encoding="utf-8")
    (root / "STORYBOARD.md").write_text("\n".join(board), encoding="utf-8")
    (root / "BRIEF.md").write_text(f"""---
workflow: product-launch-video
flow: automation
storyboard: yes
message: "{s['message']}"
destination: shorts-reels-tiktok
aspect: 1080x1920
language: en
audience: film fans and people curious about data or AI; no ML background
length: 25s
angle: "follow-up data story" (show and sell)
---

## Intent

One of four vertical shorts on the model fitting (videos/mmm-predict-a-hit/PLAN.md, revised 2026-11-13), in the
Massive Movie Map series (https://massive-movie-map.mjrfx.com). Same narrator (Kokoro af_heart, 1.1x), music
family, calm phrase subtitles and Late Show look as the earlier videos.

## Notes

- Percentiles among real films, predicted from the plot alone; not forecasts. TMDB box office (streaming films
  report little or none), not inflation-adjusted.
- End card credits: TMDB logo + notice; plots from Wikipedia, CC BY-SA.
- Ask before committing anything to git.
""", encoding="utf-8")
    print(proj, f"{len(s['frames'])} frames, {total:.1f}s")
