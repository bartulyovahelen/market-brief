# Daily Market Brief — cloud edition

Runs every morning in GitHub Actions (no computer or app needed). Gemini researches
the video-distribution niche across two streams, writes a dated HTML digest, and
rebuilds a clickable calendar. Results are committed back to this repo.

## Files
- `brief.py` — the engine (Gemini brain + renderer)
- `build_calendar.py` — rebuilds `index.html` (the clickable calendar)
- `day_template.html` — layout of one daily page
- `sources.md` — the watchlist (edit freely: competitors, platforms, geo, signals)
- `.github/workflows/brief.yml` — the daily schedule

## One-time setup
1. Create a **free Gemini API key** at aistudio.google.com (no card needed).
2. In this repo: **Settings → Secrets and variables → Actions → New repository secret**.
   Name it `GEMINI_API_KEY`, paste the key, save.
3. **Actions** tab → run the workflow once (`Run workflow`) to confirm it works.
   It will create `digests/<date>.html` and `index.html`.
4. To view the calendar anywhere: **Settings → Pages →** deploy from `main` / root.
   (Pages is public; keep the repo private and view locally if the content is sensitive.)

After that it runs automatically every day.

## Schedule / timezone note
GitHub cron runs in **UTC** and does not follow daylight saving. The workflow is set
to `06:00 UTC`, which is **09:00 Kyiv in summer** (EEST) and **08:00 in winter** (EET).
If you want exactly 09:00 year-round, change the cron in `brief.yml` to `0 7 * * *`
during winter.

## Swapping the brain
The brain is free Gemini. For sharper synthesis you can switch to the Anthropic API
(paid): change `brief.py` to call Claude and store `ANTHROPIC_API_KEY` instead.
