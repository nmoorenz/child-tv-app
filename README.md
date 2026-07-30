# Kids TV

A simple Android TV app that lets a child watch a few chosen YouTube channels
(Numberblocks, Kid Crew) as a friendly, remote-navigable grid — playing each video
in-app, with no browsing, no recommendations to wander into.

## What's here

- `build_catalog.py` — scrapes the channels into `catalog.json` (uses yt-dlp, no API key).
- `update_kidcrew.py` — refreshes only Kid Crew (run nightly by the GitHub Action).
- `preview.html` — open in a browser to preview the layout and check the data.
- `kidstv-player.html` — the video player page; you host this on your website.
- `android/` — the Android TV app (built by GitHub Actions into an APK you sideload).

## How it works

`catalog.json` is the content. The app fetches it from your GitHub repo at startup,
so updating content never needs a new APK. Playback loads `kidstv-player.html` from
your site (a real web page is required for the videos to play in the TV's web view).
A nightly Action re-scrapes Kid Crew and republishes the catalog automatically;
Numberblocks is scraped once and left alone.

## One-time setup

1. Host `kidstv-player.html` on your site (Hugo/blogdown: put it in `static/`), and
   set `PLAYER_PAGE_URL` in `android/app/src/main/java/tv/childtv/app/PlaybackActivity.kt`.
2. Make this GitHub repo public, and set `CATALOG_URL` in
   `android/app/src/main/java/tv/childtv/app/CatalogRepository.kt` to your repo.
3. Run `python build_catalog.py` once and commit the resulting `catalog.json`.
4. Build the APK (GitHub **Actions → Build APK**), download the artifact, and
   sideload it on the TV.

## Updating

New Kid Crew videos appear on their own — the nightly **Update catalog** Action
refreshes them. To change what's included, edit `build_catalog.py` (e.g. the
`max_duration_seconds` filter) and re-run it.
