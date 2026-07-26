#!/usr/bin/env python3
"""
build_catalog.py  —  Numberblocks (and friends) catalog builder.

Scrapes the official Numberblocks YouTube channel with yt-dlp
(NO API key required) and writes catalog.json — the single file the
preview.html page and the Android TV app both read.

It pulls the channel's eight official "FULL EPISODES" season playlists
(Season 1 through Season 8, ~180 complete episodes) and uses each as a
"Season N" collection your child browses. Every episode's YouTube title
carries a "S# E#" tag (e.g. "Grid Unlocked | S7 E1 | ... - Full Episode"),
which this script parses to order episodes and show a clean episode name.

--------------------------------------------------------------------
SETUP (one time)
--------------------------------------------------------------------
  1. Install Python 3.9+        https://www.python.org/downloads/
  2. Install yt-dlp:            pip install -U yt-dlp
     (Windows: just double-click run_scraper_windows.bat instead.)

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python build_catalog.py
  Output: catalog.json  (next to this script)

--------------------------------------------------------------------
ADD / CHANGE WHAT'S INCLUDED
--------------------------------------------------------------------
  Edit the CHANNELS list below. Each channel lists the playlists to
  pull (by playlist ID). Set "playlists": "auto" to instead discover
  every playlist on the channel automatically.
"""

import json
import re
import subprocess
import sys
import shutil
from pathlib import Path

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
CHANNELS = [
    {
        "id": "numberblocks",
        "title": "Numberblocks",
        "url": "https://www.youtube.com/@Numberblocks",
        "youtubeChannelId": "UCPlwvN0w4qFSP1FllALB92w",
        "color": "#e5322d",
        # The eight official "FULL EPISODES" season playlists, in order.
        # Each is a complete season, so these become the "Season N" rows
        # your child browses. Episodes are ordered by their S# E# tag.
        "playlists": [
            {"id": "PL9swKX1PviEr9UfByZqJYiN8KX3AXqyXm",
             "title": "Season 1", "color": "#d11f1f"},   # 15 eps
            {"id": "PL9swKX1PviEpC7x7ZzmxZTVrwOV2zitcu",
             "title": "Season 2", "color": "#f57c00"},   # 15 eps
            {"id": "PL9swKX1PviEruaholwotM1lOcNCQuweCl",
             "title": "Season 3", "color": "#ffd21e"},   # 30 eps
            {"id": "PL9swKX1PviEqpJgWu9DzINYclNC-rzOiF",
             "title": "Season 4", "color": "#5fbf3b"},   # 30 eps
            {"id": "PL9swKX1PviEph7heoMnLEfW2y28kwLNZw",
             "title": "Season 5", "color": "#39b6ff"},   # 30 eps
            {"id": "PL9swKX1PviEqUShSKIf5iS99jq1qAFztz",
             "title": "Season 6", "color": "#7a52cc"},   # 15 eps
            {"id": "PL9swKX1PviEovgpCesV8muL-i8RwogKvL",
             "title": "Season 7", "color": "#e91e8c"},   # 15 eps
            {"id": "PL9swKX1PviErV5UKYedc69ITUoipMhr9M",
             "title": "Season 8", "color": "#00b8a9"},   # 30 eps
        ],
        # keywords used only when "playlists": "auto"
        "auto_keywords": ["season", "series", "full episode"],
    },
    # Add another channel later by copying the block above.
]

MAX_VIDEOS_PER_PLAYLIST = 200
OUTPUT = Path(__file__).with_name("catalog.json")

SE_RE = re.compile(r"S\s*(\d+)\s*E\s*(\d+)", re.I)


# ------------------------------------------------------------------
def check_ytdlp():
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       check=True, capture_output=True)
        return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        print("ERROR: yt-dlp is not installed.  Install with:  pip install -U yt-dlp",
              file=sys.stderr)
        sys.exit(1)


def ytdlp_json(base_cmd, url, extra=None):
    cmd = base_cmd + ["--dump-single-json", "--flat-playlist",
                      "--no-warnings", "--ignore-errors"]
    if extra:
        cmd += extra
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not proc.stdout.strip():
        print(f"  ! yt-dlp returned nothing for {url}\n    {proc.stderr[:300]}",
              file=sys.stderr)
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"  ! could not parse yt-dlp output for {url}", file=sys.stderr)
        return None


def thumb(vid):
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"


def parse_episode(raw_title):
    """Return (clean_name, season, episode) from a raw YouTube title."""
    season = episode = None
    m = SE_RE.search(raw_title)
    if m:
        season, episode = int(m.group(1)), int(m.group(2))
    # clean display name = text before the first "|"
    name = raw_title.split("|")[0].strip()
    if not name:
        name = raw_title.strip()
    return name, season, episode


def collect_playlist(base_cmd, pl):
    pl_url = f"https://www.youtube.com/playlist?list={pl['id']}"
    print(f"  - {pl['title']}")
    data = ytdlp_json(base_cmd, pl_url,
                      extra=["--playlist-end", str(MAX_VIDEOS_PER_PLAYLIST)])
    eps = []
    for v in (data or {}).get("entries") or []:
        if not v or not v.get("id"):
            continue
        raw = v.get("title") or ""
        name, season, episode = parse_episode(raw)
        eps.append({
            "name": name,
            "rawTitle": raw,
            "season": season,
            "episode": episode,
            "videoId": v["id"],
            "thumbnail": thumb(v["id"]),
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "duration": v.get("duration"),
        })
    # order: by (season, episode) when tags exist, else keep playlist order
    if all(e["season"] is not None and e["episode"] is not None for e in eps) and eps:
        eps.sort(key=lambda e: (e["season"], e["episode"]))
    # renumber a simple display index
    for i, e in enumerate(eps, start=1):
        e["episode_index"] = i
    print(f"      {len(eps)} videos")
    return eps


def discover_playlists(base_cmd, ch):
    print("  discovering playlists…")
    data = ytdlp_json(base_cmd, ch["url"].rstrip("/") + "/playlists")
    kws = ch.get("auto_keywords", [])
    found = []
    for e in (data or {}).get("entries") or []:
        if not e or not e.get("id"):
            continue
        title = e.get("title") or "Playlist"
        if kws and not any(k in title.lower() for k in kws):
            continue
        found.append({"id": e["id"], "title": title, "color": ch.get("color")})
    return found


def build_channel(base_cmd, ch):
    print(f"\n== {ch['title']} ==")
    pls = ch.get("playlists")
    if pls == "auto":
        pls = discover_playlists(base_cmd, ch)
    collections = []
    for pl in pls:
        eps = collect_playlist(base_cmd, pl)
        if eps:
            collections.append({
                "id": pl["id"],
                "title": pl["title"],
                "color": pl.get("color", ch.get("color")),
                "episodes": eps,
            })
    total = sum(len(c["episodes"]) for c in collections)
    print(f"  => {len(collections)} collections, {total} videos")
    return {
        "id": ch["id"],
        "title": ch["title"],
        "youtubeChannelId": ch.get("youtubeChannelId"),
        "color": ch.get("color", "#4a6cf7"),
        "collections": collections,
    }


def main():
    base_cmd = check_ytdlp()
    catalog = {"generatedWith": "build_catalog.py", "channels": []}
    for ch in CHANNELS:
        catalog["channels"].append(build_channel(base_cmd, ch))
    OUTPUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(f"\nWrote {OUTPUT}")
    print("Open preview.html and click 'Load catalog.json' to verify the real data.")


if __name__ == "__main__":
    main()
