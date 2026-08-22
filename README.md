# League of Legends — live FPL page

Static page that reads a `data.json` refreshed from the FPL API on a schedule.

## Files

| File | Where it goes |
|---|---|
| `index.html` | repo root |
| `logo.png` | repo root, next to index.html |
| `fetch_data.py` | repo root |
| `data.json` | generated, repo root |
| `update-fpl-data.yml` | `.github/workflows/update-fpl-data.yml` |

## Why not fetch the API from the browser

The FPL API sends no `Access-Control-Allow-Origin` header, so a browser blocks any
direct call from a GitHub Pages origin. The workaround is to fetch server-side in
the Action and commit `data.json`, which the page then loads same-origin.

## Setup

League 7549 and entry 300557 are already set as defaults at the top of `fetch_data.py`.

1. Run it once locally to check the output:
   ```
   python3 fetch_data.py
   ```
   No dependencies, standard library only. Pass a different league as `fetch_data.py 378952`.
2. Commit `index.html`, `logo.png`, `fetch_data.py` and `data.json`.
3. Add the workflow at `.github/workflows/update-fpl-data.yml`.
4. Settings → Actions → General → Workflow permissions → Read and write.
5. Run it manually once from the Actions tab to confirm, then leave it to the cron.

To point the workflow at another league without editing the file, add a repository
variable named `LEAGUE_ID` (Settings → Secrets and variables → Actions → Variables).
It falls back to 7549 when unset.

## Refresh rate

Set to every 30 minutes. GitHub's scheduler is best effort and often runs late,
sometimes much later when the platform is busy. If you want the page to feel live
on a Saturday afternoon, run the workflow manually, or drop the cron to `*/15`
knowing it may still lag.

Each run commits to the repo, so expect a busy commit history. That is normal for
this pattern.

## What the page does with the data

Everything is computed in the browser from `data.json`: ownership, captaincy split,
club stacks, differential and template rankings, the closest pair of squads, chip
usage, and the head to head comparison.

Before the deadline the page shows a picks-only preview. Once points appear it adds
a live standings table and per-player scores in the comparison tool. That switch is
driven by `event.started`, which is set when any player in the gameweek has scored.

## Caveats

- Other managers' picks are only public **after** the gameweek deadline. Run before
  the deadline and most managers will be skipped.
- The FPL API is undocumented and unversioned. If a field name changes, the script
  breaks and the page keeps showing the last good `data.json`.
- One request per manager. An 82-manager league is ~84 requests at 0.4s spacing,
  about a minute per run.
