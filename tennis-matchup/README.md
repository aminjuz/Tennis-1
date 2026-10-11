# Matchup

Pick two ATP players and a court on your phone. The page shows win probability, why one player is favoured,
serve/return and style comparison, head-to-head, court speed, and form/workload.

Data: each player's Tennis Abstract classic page (rendered in a headless browser) and the courtspeed.com tables.
Personal, non-commercial use; Tennis Abstract data is Jeff Sackmann's (CC BY-NC-SA), so credit him and keep it non-commercial.

## Set up (once)
1. Create a **public** GitHub repo and upload this whole folder (keep the `.github` folder).
2. Settings > Pages > Deploy from branch > `main` / root. Your page will be at `https://<you>.github.io/<repo>/`.
3. Actions tab > "Update tennis data" > Run workflow. The first run takes ~10-20 minutes for 100 players.
4. Open the page on your phone and use Share > Add to Home Screen.

It then refreshes daily. Start a refresh any time from the Actions tab (or the GitHub mobile app).

## First run: check it
The scraper was written from the page structure seen on a Tiafoe page, but it has not run end to end yet.
After the first run, open `data/errors.json`. If players failed, run locally with
`python scraper/scrape.py --debug --only FrancesTiafoe` and send me `data/raw_FrancesTiafoe.json`.

## Notes
- `scraper/players_seed.json` is the top-200 list as of 5 Oct 2026. Add players by appending `{rank, name, slug}`
  (slug = Tennis Abstract name without spaces, e.g. `FrancesTiafoe`).
- The scraper waits 2.5 s between players to be gentle on the site. Keep `--top` modest.
- Injury status is not in the data; each comparison links to a news search.
- Win probability is a heuristic (serve/return point model, blended 60/40 with Elo when available), not a betting tip.
