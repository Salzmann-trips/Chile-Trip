# Chile Road Trip (standalone site)

Read-only mirror of the Claude planner (https://claude.ai/artifact/R36zMGZKf33HLWfk1A3Boj).
Editing stays in the planner; this site shows the same trip with real OpenStreetMap maps,
road routing (OSRM) and buttons that hand each drive to Waze, Google Maps, Apple Maps or a GPX file.

## Files
- `index.html` – the whole site (no build step)
- `data/trip.json` – the trip data, generated from the planner
- `tools/sync.py` – turns an export of the planner's database into `data/trip.json`

## What gets published
Title, type, dates/times, place name, coordinates and link. **Costs are never published. Notes are
left out by default** (they may hold booking numbers); pass `--include-notes` to include them.
Example entries are skipped. The site has `noindex`, but a GitHub Pages site is public: anyone
with the link can open it.

## One-time setup (GitHub Pages)
1. Create a free account at github.com.
2. New repository, e.g. `chile-trip`, **Public** (free Pages needs a public repo).
3. "Add file → Upload files": upload `index.html`, the `data` folder, `tools` folder and this README. Commit.
4. Settings → Pages → Source: "Deploy from a branch", Branch `main`, folder `/ (root)`. Save.
5. After a minute the site is at `https://<your-username>.github.io/chile-trip/`.

## Daily sync
A scheduled Claude task reads the planner's database, runs `tools/sync.py`, and commits
`data/trip.json` only when something changed. It needs write access to this one repository
(connect the repo to Claude, or a fine-grained token limited to this repo with "Contents: read and write").

## Later: making it editable (option 2)
All data loading goes through `loadTrip()` in `index.html`. Swapping that for a database
(e.g. Firebase or Supabase, both free tiers) plus a login makes the site editable.

## Services used
- Map tiles: © OpenStreetMap contributors (tile.openstreetmap.org, fine for personal, low-traffic use)
- Routing: OSRM public demo server (router.project-osrm.org): one request per day route, cached in the browser
