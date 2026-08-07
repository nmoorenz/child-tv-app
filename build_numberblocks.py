#!/usr/bin/env python3
"""
build_numberblocks.py  —  one-off builder for the Numberblocks channel.

Scrapes the eight official "FULL EPISODES" season playlists (Season 1-8, ~180
complete episodes) and splices a "Numberblocks" channel into catalog.json, leaving
every other channel untouched. Each playlist becomes a "Season N" row; episodes are
ordered by the "S# E#" tag in their titles.

This used to live in build_catalog.py. It's a one-off: run it once locally (and
again only if the playlists change). It also registers a manual:True stub in
build_catalog.py so a full rebuild / the nightly job never drops Numberblocks.

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python build_numberblocks.py
  Updates: catalog.json
--------------------------------------------------------------------
"""

import json
import re
from pathlib import Path

import build_catalog as bc

CATALOG = Path(__file__).with_name("catalog.json")
MAX_VIDEOS_PER_PLAYLIST = 200
SE_RE = re.compile(r"S\s*(\d+)\s*E\s*(\d+)", re.I)

CHANNEL = {
    "id": "numberblocks",
    "title": "Numberblocks",
    "url": "https://www.youtube.com/@Numberblocks",
    "youtubeChannelId": "UCPlwvN0w4qFSP1FllALB92w",
    "color": "#e5322d",
}

# The eight official "FULL EPISODES" season playlists, in order.
PLAYLISTS = [
    {"id": "PL9swKX1PviEr9UfByZqJYiN8KX3AXqyXm", "title": "Season 1", "color": "#d11f1f"},
    {"id": "PL9swKX1PviEpC7x7ZzmxZTVrwOV2zitcu", "title": "Season 2", "color": "#f57c00"},
    {"id": "PL9swKX1PviEruaholwotM1lOcNCQuweCl", "title": "Season 3", "color": "#ffd21e"},
    {"id": "PL9swKX1PviEqpJgWu9DzINYclNC-rzOiF", "title": "Season 4", "color": "#5fbf3b"},
    {"id": "PL9swKX1PviEph7heoMnLEfW2y28kwLNZw", "title": "Season 5", "color": "#39b6ff"},
    {"id": "PL9swKX1PviEqUShSKIf5iS99jq1qAFztz", "title": "Season 6", "color": "#7a52cc"},
    {"id": "PL9swKX1PviEovgpCesV8muL-i8RwogKvL", "title": "Season 7", "color": "#e91e8c"},
    {"id": "PL9swKX1PviErV5UKYedc69ITUoipMhr9M", "title": "Season 8", "color": "#00b8a9"},
]


def parse_episode(raw_title):
    """Return (clean_name, season, episode) from a raw YouTube title."""
    season = episode = None
    m = SE_RE.search(raw_title)
    if m:
        season, episode = int(m.group(1)), int(m.group(2))
    name = raw_title.split("|")[0].strip() or raw_title.strip()
    return name, season, episode


def collect_playlist(base_cmd, pl):
    pl_url = f"https://www.youtube.com/playlist?list={pl['id']}"
    print(f"  - {pl['title']}")
    data = bc.ytdlp_json(base_cmd, pl_url,
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
            "thumbnail": bc.thumb(v["id"]),
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "duration": v.get("duration"),
            "durationText": bc.hms(v.get("duration")),
        })
    # order by (season, episode) when every episode is tagged, else keep playlist order
    if eps and all(e["season"] is not None and e["episode"] is not None for e in eps):
        eps.sort(key=lambda e: (e["season"], e["episode"]))
    for i, e in enumerate(eps, start=1):
        e["episode_index"] = i
    print(f"      {len(eps)} videos")
    return eps


def build_channel(base_cmd):
    print("== Numberblocks ==")
    collections = []
    for pl in PLAYLISTS:
        eps = collect_playlist(base_cmd, pl)
        if eps:
            collections.append({
                "id": pl["id"],
                "title": pl["title"],
                "color": pl.get("color", CHANNEL["color"]),
                "episodes": eps,
            })
    total = sum(len(c["episodes"]) for c in collections)
    print(f"  => {len(collections)} seasons, {total} videos")
    return {
        "id": CHANNEL["id"],
        "title": CHANNEL["title"],
        "youtubeChannelId": CHANNEL.get("youtubeChannelId"),
        "color": CHANNEL["color"],
        "collections": collections,
    }


def main():
    base_cmd = bc.check_ytdlp()
    channel = build_channel(base_cmd)

    if CATALOG.exists():
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    else:
        print(f"{CATALOG.name} not found — creating a new one")
        catalog = {"generatedWith": "build_catalog.py", "channels": []}

    channels = catalog.setdefault("channels", [])
    for i, c in enumerate(channels):
        if c.get("id") == channel["id"]:
            channels[i] = channel
            break
    else:
        channels.append(channel)

    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {CATALOG} — Numberblocks spliced in, other channels untouched.")

    if bc.register_manual_stub(CHANNEL["id"], CHANNEL["title"],
                               CHANNEL["url"], CHANNEL["color"]):
        print("Added a manual:True stub to build_catalog.py so rebuilds keep it.")


if __name__ == "__main__":
    main()
