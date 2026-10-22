# Board Game Embedding Map — Plan

Oct 22, 2026 · @Mark

## Goal and scope

Build an interactive 2D map of every ranked BoardGameGeek (BGG) game, placed by the meaning of its description, so similar games cluster and surprising neighbors show up.

**v1 deliverable:** a local web page with every ranked base game (no expansions) as a point. Hover shows a card, search flies to a game, and points can be colored by weight, year, rating or player count.

**v1 is done when:**

- All ranked base games are fetched, cleaned and cached locally
- Embeddings run end to end on the RTX 3080 in under an hour
- The map has labeled clusters, and 20 games picked by hand have neighbors that make sense
- We have a written call on whether LLM profiles are worth adding (see Later)

**Out of scope for v1:** LLM-rewritten profiles, user reviews, other domains, public hosting.

## Data source

Use the official BGG XML API2 with a registered application. Register on day one, because approval can take a week or more.

- **Access.** As of BGG's 2025 policy, the XML API requires a registered application and a Bearer token ([Using the XML API](https://boardgamegeek.com/using_the_xml_api)). Register a free non-commercial app at boardgamegeek.com/applications. Send requests to `boardgamegeek.com` without `www`, or the token is ignored. Keep the token in an env var, never in the repo.
- **The game list.** BGG publishes a CSV of every game's id, name, rank and average rating ([BGG XML API wiki](https://boardgamegeek.com/wiki/page/BGG_XML_API)). It now also needs an approved application. Filter it to ranked base games to get our ID list.
- **Details.** `xmlapi2/thing?id=<ids>&stats=1` takes comma-separated IDs. Batch about 20 per request.
- **Pace.** BGG asks that requests be cached and made server-side. Run one request every few seconds and cache every raw XML response. At 20 IDs per request, about 1,500 requests covers 30k games in roughly 1–2 hours.
- **Terms.** A public-facing app must show the "Powered by BGG" logo linking back to BGG. Re-read the terms before hosting anything publicly.

**Fields to pull per game**

| Group | Fields | Used for |
| --- | --- | --- |
| Identity | id, name, year, thumbnail URL | Labels, hover card |
| Text | description | The embedding |
| Tags | categories, mechanics, families, designers, publishers | Overlays and evaluation, not embedded in v1 |
| Play | min/max players, playing time, min age | Overlays, filters |
| Stats | rank, bayes average, average, users rated, owned, average weight | Color and size, filters |

Keeping tags out of the embedded text matters: it lets us check whether description meaning alone recovers mechanics and categories.

## Pipeline architecture

A plain Python pipeline of six scripts, each reading the previous stage's file and writing its own. Nothing past stage 2 touches the network, so embedding and mapping can be rerun freely.

&#91;embedded content: pipeline · 6 stages, each cached to disk\]

Stage 2 is the slow, rate-limited one; it resumes from its cache if interrupted.

**Repo layout**

- `data/raw/` — cached XML responses, one file per batch (gitignored)
- `data/` — `ids.csv`, `games.parquet`, `embeddings.npy`, `map.parquet`
- `src/` — `fetch.py`, `parse.py`, `embed.py`, `project.py`, `label.py`
- `web/` — the interactive map page
- `notebooks/` — evaluation and parameter sweeps

**Stack:** Python 3.12, `requests`, `lxml`, `pandas`/`pyarrow`, `sentence-transformers`, `umap-learn`, `hdbscan`, `datamapplot`.

## Embedding

Embed the cleaned description text as-is (no LLM profiles yet), using a long-context model that runs locally on the RTX 3080.

**Text that gets embedded:** `"<name>. <cleaned description>"`. Cleaning strips HTML entities, BBCode, URLs and repeated whitespace. Tags stay out (see Data source). Games with an empty or very short description (under \~30 words) are flagged and drawn in a muted color rather than dropped.

**Why context length matters:** BGG descriptions run long, often including rules summaries and component lists. A 512-token model silently truncates them, so prefer a model with a long context window.

| Role | Model | Notes |
| --- | --- | --- |
| Primary | Qwen3-Embedding-0.6B | Long context, strong on benchmarks, about 1.2 GB in fp16 |
| Alternative | nomic-embed-text v1.5 | 8k context; needs the ` search_document:  ` prefix |
| Fast baseline | bge-base-en-v1.5 | 512 tokens; useful to see how much truncation costs |

Check the MTEB leaderboard before committing, since rankings move quickly.

**Settings:** fp16 on CUDA, `normalize_embeddings=True`, batch size tuned to fill VRAM (start at 32 for long texts). Save vectors as `embeddings.npy` with a row order that matches `games.parquet`, plus the model name and date in a small metadata file.

Running two models is cheap, so v1 embeds with both the primary and the fast baseline and compares them in Evaluation.

## Projection and clustering

Project to 2D with UMAP for the picture, but cluster in a higher-dimensional UMAP space so cluster shapes aren't distorted by squashing to two dimensions.

1. **UMAP to 2D** for display: cosine metric, `n_neighbors` 15–50, `min_dist` 0.05–0.2, fixed `random_state`. Sweep a small grid and save each layout.
2. **UMAP to \~10D** for clustering, same neighbors setting.
3. **HDBSCAN** on the 10D output. Start with `min_cluster_size` around 30 and sweep it; expect a share of points labeled noise, which is fine.
4. **Label clusters.** For each cluster, send the 20 most central game names plus their top mechanics and categories to an LLM and ask for a 2–5 word label. Tags are allowed here because they only name clusters, they don't place games. This is a few hundred cheap API calls.
5. **Hierarchy (optional).** `datamapplot` supports multi-level labels; run HDBSCAN at two cluster sizes to get broad regions and fine sub-clusters.

Output: `map.parquet` with id, x, y, cluster id, cluster label and every overlay field, ready for the web page.

## Visualization and interactions

Ship a static `datamapplot` image first to judge the layout, then build one self-contained interactive web page.

**Rendering:** start with `datamapplot`'s interactive HTML export, since it handles labels and zoom out of the box. Move to deck.gl or Apple's Embedding Atlas only if we outgrow it.

**Interactions, in priority order**

1. Hover card: thumbnail, name, year, weight, player count, playtime, rank, top mechanics
2. Search box that flies to a game and highlights it
3. Color-by switch: cluster, weight, year, bayes rating, best player count, a chosen mechanic
4. Point size by number of ratings, so popular games stand out
5. Click a game to list its 10 nearest neighbors (computed in full embedding space, not 2D)
6. Filters: year range, weight range, player count
7. Model toggle: primary vs baseline layout

Thumbnails load from BGG's image URLs. Keep the page private for v1; adding the "Powered by BGG" logo is a requirement before sharing it publicly.

## Evaluation

Judge the map with one quantitative check against BGG's own tags and one qualitative check against games we know. Because tags were kept out of the embedded text, they work as an independent answer key.

| Check | How | What good looks like |
| --- | --- | --- |
| Tag agreement | For each game, the share of its 10 nearest neighbors that share at least one mechanic, and separately one category | Well above a random-neighbor baseline; compare primary vs baseline model |
| Known-game spot check | Pick 20 games we know well across genres; review each one's 10 nearest neighbors | Most neighbors feel right; misses have a nameable cause |
| Cluster review | Read every cluster label plus five sample members | Clusters describe gameplay or theme, not writing style |
| Confound scan | Color the map by publisher, description length and year | No region is explained mainly by one of these |
| Layout stability | Compare 2D layouts across seeds and parameters | Same broad regions every run |

Keep a short log of failure cases with examples. That log is the evidence for the profiles decision below.

## Milestones

Five phases over about four to five weeks of spare time, with BGG app approval as the only external wait.

1. **Register and scaffold (week 1).** Register the BGG application on day one. Set up the repo, and build and test the parse, embed and projection stages on a handful of hand-saved game pages while approval is pending.
   - Exit: stages 3–6 run end to end on stub data.
2. **Fetch (week 2, once approved).** Download the ranks CSV and run the full fetch with caching and resume.
   - Exit: `games.parquet` holds every ranked base game; failures are logged and retried.
3. **Baseline map (week 2–3).** Embed with both models, sweep UMAP and HDBSCAN settings, label clusters, render the static map.
   - Exit: a static map we'd be happy to post a screenshot of.
4. **Evaluate (week 3).** Run the checks in Evaluation and write up the failure log.
   - Exit: chosen model and parameters, plus a yes/no on profiles.
5. **Interactive page (week 4–5).** Build the web page with interactions 1–5, then 6–7 if time allows.
   - Exit: the v1 done criteria in Goal and scope are met.

## Twists

Once the v1 map works, these turn it from a picture into a tool. They're post-v1 and ordered roughly from cheapest to most work; gap finding and the personal overlay reuse `map.parquet` almost as-is.

| Twist | What it shows | What it needs | Effort |
| --- | --- | --- | --- |
| Gap finding | Regions with few games but high ratings or ownership: underserved niches, or "games that should exist" | A density layer computed from `map.parquet`, crossed with bayes rating and owned counts | Small |
| Personal overlay | My owned and rated games highlighted; a taste centroid; nearest unowned games as picks, plus deliberately distant "stretch" picks | My BGG collection via the `collection` endpoint (owned, rated, my ratings) | Small |
| Time animation | Regions appearing and filling in by publication year, showing when design trends arrived | The year field already fetched; a year slider on the page | Small |
| "How it plays" layer | A second map from what players say rather than what publishers write | User comments via `thing?comments=1`, embedded per game; a much heavier fetch | Medium |
| Description vs. audience | Games that sound alike but are rated by different people, and the reverse | A ratings-based embedding (which users rate which games) to set against the description embedding; flag games whose two neighbor lists disagree most | Large |
| Cross-media space | Board games, video games and books in one space: the novel or Steam game nearest to a given board game | A second domain run through the same pipeline and the same embedding model | Large |

The description-vs-audience twist is the most novel. The disagreements are where the interesting stories are, and it doubles as a check on how much descriptions actually capture.

## Later

**Note: consider LLM profiles after seeing the v1 outcome.** Raw descriptions are skipped for now on purpose. Revisit after Evaluation, and add the profile step (between stages 3 and 4) if the failure log shows any of these:

- Neighbors grouped by writing style: publisher boilerplate, crowdfunding hype, translated text
- Long flavor text or story intros outweighing how the game actually plays
- Rules and component lists pulling games together that play nothing alike
- Games with short descriptions landing in odd places

If we add it, a cheap hosted model rewrites each game into a fixed schema: theme and setting, core mechanics, player interaction, complexity feel, length and player-count sweet spot, mood. Then rerun stages 4–6 and compare against the v1 map with the same Evaluation checks.

**Risks**

| Risk | Mitigation |
| --- | --- |
| App approval takes weeks | Build later stages on stub data first (Milestones phase 1) |
| Rate limiting or blocked token | Slow, cached, resumable fetch; one request every few seconds |
| Terms limit public sharing | Keep v1 private; review terms and add the BGG logo before sharing |
| Map is dominated by writing style | That is the trigger for the profiles step above |

## Sources

- [Using the XML API](https://boardgamegeek.com/using_the_xml_api) — registration, tokens, usage guidance, logo requirement
- [BGG XML API wiki](https://boardgamegeek.com/wiki/page/BGG_XML_API) — ranks CSV download
- [BGG XML API2 reference](https://videogamegeek.com/wiki/page/BGG_XML_API2) — endpoint parameters
