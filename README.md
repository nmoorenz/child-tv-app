# Kids TV

A simple Android TV app that lets a child watch a few chosen YouTube channels
(Numberblocks, Kid Crew, Half-Asleep Chris, David Rule, Postman Pat, Octonauts, and
more) as a friendly, remote-navigable grid — playing each video in-app, with no ads,
no browsing, and no recommendations to wander into.

## What's here

- `build_catalog.py` — bootstraps the auto-updating "videos" channels into
  `catalog.json`, and is the shared library every other script imports.
- `update_nightly.py` — the nightly refresh (run by GitHub Actions); re-scrapes the
  channels flagged `auto_update` and merges them in, leaving everything else alone.
- `channel_metadata.py` + `build_from_csv.py` — the one-off path: dump a channel to a
  CSV, keep the rows you want, then build it into a channel.
- `build_numberblocks.py`, `build_postman_pat.py`, `build_octonauts.py` — bespoke
  one-off builders for channels that need special handling.
- `preview.html` — open in a browser to preview the layout and check the data.
- `android/` — the Android TV app (built by GitHub Actions into an APK you sideload).

(`kidstv-player.html` is left over from an earlier web-based player and is no longer used.)

## How it works

`catalog.json` is the content. The app fetches it from this GitHub repo at startup,
so updating content never needs a new APK. Playback is native: when a video is
selected the app extracts a stream on-device and plays it in ExoPlayer at 720p —
which is what keeps it smooth and ad-free on an old TV.

Content is maintained by two processes:

**Nightly** — `update_nightly.py` runs on a schedule (GitHub Actions) and refreshes
only the channels flagged `auto_update` (Kid Crew, Half-Asleep Chris, David Rule). It
re-scrapes each one's newest few videos and merges them in, freezing dates already in
`catalog.json` so they don't drift, and never touching any other channel.

**One-off** — everything else is built once and pinned. Get the channel into a CSV
with `channel_metadata.py`, mark the `keep` rows, and run `build_from_csv.py` to build
and splice it in. Channels needing special handling have their own builders
(`build_numberblocks.py`, the Postman Pat and Octonauts pipelines). Each one-off
registers a `manual: True` stub in `build_catalog.py`, which is what stops a full
rebuild or the nightly job from dropping it.

## One-time setup

1. Make this GitHub repo public, and set `CATALOG_URL` in
   `android/app/src/main/java/tv/childtv/app/CatalogRepository.kt` to this repo.
2. Run `python build_catalog.py` once and commit the resulting `catalog.json`.
3. Build the APK (GitHub **Actions → Build APK**), download the artifact, and
   sideload it on the TV.

## Adding or changing channels

**A channel that should refresh every night** (posts regularly, plays fine through a
full scrape): add it to the `CHANNELS` list in `build_catalog.py` with
`source: "videos"`, `auto_update: True`, and optional filters `max_duration_seconds`
(drop long videos) / `min_date` (only keep videos on/after a `YYYYMMDD` date). Run
`build_catalog.py` once to bootstrap it; the nightly job keeps it fresh after that.

**A one-off channel** (hand-picked, doesn't need nightly updates):

1. `python channel_metadata.py <channel-url>` → writes `<handle>_videos.csv`.
2. Open the CSV, mark the rows you want in the `keep` column.
3. `python build_from_csv.py <csv> --id <id> --title "<Title>" [--layout grid|seasons] [--clean-title]`.

That splices the channel into `catalog.json` and auto-registers a `manual: True` stub
in `build_catalog.py` so rebuilds keep it. Commit `catalog.json`. The app picks up
changes with no rebuild; a rebuild is only needed for changes under `android/`.
