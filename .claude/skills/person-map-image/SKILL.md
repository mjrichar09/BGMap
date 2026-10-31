---
name: person-map-image
description: Make a social image (X / Reddit) of one director's or actor's films on the Massive Movie Map, with their stats card overlaid (avg rating, box office, range), and draft the post to go with it. Use when asked for "<name>'s map", a director/actor image, or a people-lens post.
---

# Person map image

One command turns a name into a 1080×1350 image (saved at 2x): the map with the person's films lit up and
labelled, their stats tiles, and the site URL. Their films come from the site's people lens (directed, or
top-4 billed cast), and the stats come from their card in `data/movies/site/data/people.json`.

## Steps

1. **Check the site build is current.** The image reads `data/movies/site` (index.html and data/). If
   `web/movies_map.html` or the data changed since the last export, re-export first:
   `.venv/Scripts/python -m src.export --domain movies --map qwen3__text_plot__inst__nn30_md0.05`, then
   `cp web/movies_map.html data/movies/site/index.html`. Use the TMDB build. The `--private` IMDb build must
   never be used for anything published.
2. **Run it** from the repo root (it starts and stops a local server on port 8765 if none is running):
   ```bash
   PYTHONIOENCODING=utf-8 .venv/Scripts/python videos/tools/person_card.py "Steven Spielberg"
   ```
   - It prints the tiles and the labels it placed, and writes
     `videos/posters/people/<slug>/<slug>.png`. That folder is gitignored, like the other media.
   - Names must match the site's spelling. When nothing matches, it prints close matches.
   - People with fewer than 5 films on the map have no stats card, so there's no image for them.
   - `--labels N` sets how many label groups it tries (default 8).
3. **Look at the image before sending it.** Read the PNG and check:
   - Labels sit beside their own films and don't cover each other or the tiles. Labels that can't fit are
     dropped (the printed list shows what made it).
   - Each tile's number matches its caption, and nothing wraps badly.
   - The line under the name matches the picture ("land everywhere" for wide range, "stay in one corner"
     for narrow).
   If a label is wrong or missing, adjust `GROUP_PX`, `NAMED` or `NAMES_PER_LABEL` in `person_card.py`,
   or the placement rings in `videos/posters/person.html`, and rerun.
4. **Send it** with SendUserFile (display: render), and draft the post (below).

## The post

X without Premium allows 280 characters (a link counts as 23). Lead with what the picture shows, give one
striking stat, and end with a question that invites replies:

> {Name}'s films, placed by an AI that read every plot.
>
> {One line on where they land: the range of subjects, or the one corner they never leave.}
>
> Whose map should I make next? 👇
> massive-movie-map.mjrfx.com

## Facts to keep straight

- Each person's card has one role, from their credits on the map: someone with more acting than directing
  credits (Greta Gerwig) is compared with actors, and all their films count. Mention it in the post if it
  matters.
- Percentiles compare directors with directors and actors with actors (the footer gives the peer count).
  "Range" is how unalike the person's plots are: top % means wider-ranging.
- Box office is TMDB's, where known, not adjusted for inflation. The total covers only films with a known
  box office.
- The film count includes acting credits. For example, Spielberg's 45 = 38 directed + 7 documentaries he
  appears in. Say "films on the map", not "films directed".
- Don't assume anyone's pronouns in captions or posts. Use their name (the image already does).
- The TMDB notice in the footer is required. Leave it in.

## Files

- `videos/tools/person_card.py`: capture, stats, label grouping, render
- `videos/posters/person.html`: the template (text fitting, collision-free label placement)
- `videos/tools/person_image.py`, `videos/posters/spielberg.html`: the earlier hand-tuned Spielberg version
