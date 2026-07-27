# Numberblocks TV — kid-safe episode launcher

A small system so your child can pick a Numberblocks episode from a friendly,
remote-navigable grid on the Android TV — and it opens **that one video** in
YouTube and plays it, without ever browsing YouTube's menus.

This folder is **Phase 1**: the data pipeline + a preview you can verify on your
computer. The Android TV app is **Phase 2** (built once you've signed off on the
data and the look).

## How it fits together

```
   build_catalog.py            preview.html            (Phase 2) Android TV app
   ─────────────────           ────────────            ───────────────────────
   scrapes the YouTube   ─▶    catalog.json     ─▶     same catalog.json,
   channel with yt-dlp        (titles, video IDs,      shown as a Leanback
   (no API key)               thumbnails, links)       grid on your TV
```

One file — `catalog.json` — is the single source of truth. The preview page and
the future app both just read it. Refresh the data anytime by re-running the
scraper. Add another channel later by adding one entry to the scraper config.

## What's in this folder

| File | What it is |
|------|-----------|
| `preview.html` | Open in any browser. Two tabs: **TV App Preview** (a mockup of what your child sees — navigate with arrow keys, Enter to open) and **Data Check** (a table to verify every episode, its video ID, thumbnail and link). Starts with sample data. |
| `build_catalog.py` | The scraper. Run on your PC to produce the real `catalog.json`. Uses `yt-dlp`, no API key. |
| `run_scraper_windows.bat` | Double-click on Windows — installs `yt-dlp` and runs the scraper for you. |
| `README.md` | This file. |

## Why the scraper runs on your machine

The environment Claude runs in blocks direct YouTube access, so the scrape has to
happen where YouTube is reachable — your PC. It's a one-liner to run.

## Getting the real data (5 minutes)

**Windows:** double-click `run_scraper_windows.bat`.

**Mac / Linux / manual:**
```
pip install -U yt-dlp
python build_catalog.py
```

This writes `catalog.json` next to the script. Then open `preview.html`, click
**Load catalog.json…**, and pick that file. The sample art is replaced with the
real episode thumbnails, titles, and working links — that's your verification step.

## The catalog format

```json
{
  "channels": [
    {
      "id": "numberblocks",
      "title": "Numberblocks",
      "youtubeChannelId": "UCPlwvN0w4qFSP1FllALB92w",
      "color": "#e5322d",
      "collections": [
        {
          "id": "PL9swKX1PviEr9UfByZqJYiN8KX3AXqyXm",
          "title": "Season 1",
          "color": "#d11f1f",
          "episodes": [
            {
              "name": "One",
              "rawTitle": "One | S1 E1 | ... | @Numberblocks - Full Episode",
              "season": 1,
              "episode": 1,
              "episode_index": 1,
              "videoId": "xxxxxxxxxxx",
              "thumbnail": "https://i.ytimg.com/vi/xxxxxxxxxxx/hqdefault.jpg",
              "url": "https://www.youtube.com/watch?v=xxxxxxxxxxx",
              "duration": 300
            }
          ]
        }
      ]
    }
  ]
}
```

A note on seasons: the channel publishes eight **"FULL EPISODES"** season playlists
(Season 1 through Season 8, ~180 complete episodes in total — every season is
complete). The scraper uses each as a `Season N` collection your child browses.
Every episode's YouTube title carries an `S# E#` tag (e.g.
`Grid Unlocked | S7 E1 | ... - Full Episode`), which the scraper reads to order
episodes and show a clean name (→ **Grid Unlocked**, Season 7 Ep 1).

Episode counts per season: S1 15, S2 15, S3 30, S4 30, S5 30, S6 15, S7 15, S8 30.

The eight playlist IDs are already filled in at the top of `build_catalog.py`. To
pull every playlist on the channel instead, set `"playlists": "auto"` there.

## How playback works on the TV (Phase 2)

Selecting an episode plays it **inside the app** using YouTube's official IFrame
player, via the well-tested `android-youtube-player` library (which handles the
WebView embedding context reliably). There's only the video on screen — no YouTube
browsing UI, so your child can't wander off. When an episode ends (or Back is
pressed) the app returns to the grid, which also skips the "up next" screen. If a
video can't be played in the embedded player, the app shows an on-screen message
(there is intentionally no YouTube-app fallback).

The menu also has a **Channels** row at the top (currently just Numberblocks, with
a placeholder for more) above the season list.

Tiles show a **progress bar**: a red bar along the bottom of each thumbnail marks
how far that episode has been watched, and playback resumes where it left off.

## Adding more channels later

Open `build_catalog.py`, copy the Numberblocks block in the `CHANNELS` list, point
it at another channel's `@handle`, re-run. The preview and app pick it up
automatically.

## Phase 2 — the Android TV app (`android/`)

A native Android TV app that reads the same `catalog.json` and shows the seasons as
a remote-navigable grid. Selecting an episode plays it inside the app (see above).

### How to get the APK (no Android Studio needed)

The app is compiled in the cloud by GitHub Actions, which hands you a ready-to-
sideload `.apk`:

1. Create a free GitHub account if you don't have one.
2. Make a new repository and upload the entire `child-tv-app` folder to it
   (browser drag-and-drop works, or use GitHub Desktop). Push to the `main` branch.
3. GitHub Actions runs automatically — see the **Actions** tab. When it finishes,
   open the run and download the **`numberblocks-tv-debug-apk`** artifact; it
   contains `app-debug.apk`.
4. Put that APK on your TV with your downloader/file app and install it. You'll
   need to allow "install from unknown sources" for that file app once.

To rebuild after refreshing the catalog: re-run the scraper, commit the updated
`catalog.json`, and push (or click "Run workflow" in the Actions tab). The workflow
copies `catalog.json` into the app automatically.

### The catalog inside the app

Until you commit a scraped `catalog.json`, the app ships with a small **placeholder**
(a few real Season 1 episodes at `android/app/src/main/assets/catalog.json`) so it
always builds and you can test playback right away.

### Honest caveats

Because it uses YouTube's official embedded player, two things are outside our
control: **ads can still play** (YouTube serves them through embeds; for kids'
content they're limited but not zero), and if any episode has **embedding disabled**
by the uploader it will show an on-screen error rather than playing (there is no
YouTube-app fallback, by design). This approach is far more reliable than stream
extraction and needs no ongoing maintenance.

### Local build (optional)

Open the `android/` folder in Android Studio and Run, or from a terminal with the
Android SDK: `cd android && ./gradlew assembleDebug`.
