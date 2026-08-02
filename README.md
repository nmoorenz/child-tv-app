# Kids TV

A simple Android TV app that lets a child watch a few chosen YouTube channels
(Numberblocks, Kid Crew, Half-Asleep Chris, David Rule) as a friendly,
remote-navigable grid — playing each video in-app, with no ads, no browsing, and
no recommendations to wander into.

## What's here

- `build_catalog.py` — scrapes the channels into `catalog.json` (uses yt-dlp, no API key).
- `update_kidcrew.py` — the nightly refresh; re-scrapes the channels flagged `auto_update`.
- `preview.html` — open in a browser to preview the layout and check the data.
- `android/` — the Android TV app (built by GitHub Actions into an APK you sideload).

(`kidstv-player.html` is left over from an earlier web-based player and is no longer used.)

## How it works

`catalog.json` is the content. The app fetches it from this GitHub repo at startup,
so updating content never needs a new APK. Playback is native: when a video is
selected the app extracts a stream on-device and plays it in ExoPlayer at 720p —
which is what keeps it smooth and ad-free on an old TV.

Video channels get **exact upload dates** via a full scrape. `build_catalog.py`
(run locally) does the whole back-catalogue — this is slow. The nightly Action then
only re-scrapes each channel's newest few videos (also exact) and merges them in,
keeping the older exact dates already in `catalog.json`. Channels without
`auto_update` (e.g. Numberblocks) are scraped once and left frozen.

## One-time setup

1. Make this GitHub repo public, and set `CATALOG_URL` in
   `android/app/src/main/java/tv/childtv/app/CatalogRepository.kt` to this repo.
2. Run `python build_catalog.py` once and commit the resulting `catalog.json`.
3. Build the APK (GitHub **Actions → Build APK**), download the artifact, and
   sideload it on the TV.

## Adding or changing channels

Edit the `CHANNELS` list in `build_catalog.py`:

- `source` — how to scrape: `"videos"` (the channel's Videos tab) or `"playlists"`.
- Optional filters — `max_duration_seconds` (drop long videos) and `min_date`
  (only keep videos on/after a `YYYYMMDD` date).
- `auto_update: True` — include the channel in the nightly refresh.

Channels with `auto_update` update on their own each night. For anything else,
re-run `build_catalog.py` and commit `catalog.json`. The app picks up changes with
no rebuild; a rebuild is only needed for changes under `android/`.
