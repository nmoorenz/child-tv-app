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

import datetime
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
    {
        "id": "kidcrew",
        "title": "Kid Crew",
        "url": "https://www.youtube.com/@KidCrew",
        "color": "#00a3e0",
        # Scrape the channel's Videos tab instead of playlists, newest first,
        # and keep only videos shorter than max_duration_seconds (drops the long
        # compilations). One collection, in reverse-chronological order.
        "source": "videos",
        "max_duration_seconds": 1800,  # 30 minutes
        "auto_update": True,           # refreshed by the nightly job
        "exact_dates": False,          # this channel won't full-extract; use fast list
    },
    {
        "id": "halfasleepchris",
        "title": "Half-Asleep Chris",
        "url": "https://www.youtube.com/@HalfAsleepChris",
        "color": "#6c5ce7",
        "source": "videos",
        "min_date": "20201210",        # only videos on/after 10 Dec 2020
        "auto_update": True,           # refreshed by the nightly job
    },
    {
        "id": "davidrule",
        "title": "David Rule",
        "url": "https://www.youtube.com/@davidmrule",
        "color": "#e67e22",
        "source": "videos",
        "min_date": "20220601",  # only videos on/after 1 June 2022
        "auto_update": True,     # refreshed by the nightly job
    },
]

# NOTE: "source" controls HOW a channel is scraped ("videos" tab, "playlists",
# or "auto"). "auto_update" is separate — set it True on any channel you want the
# nightly job to refresh, regardless of how it's scraped. Channels without it
# (e.g. Numberblocks) are scraped once and then left frozen.

MAX_VIDEOS_PER_PLAYLIST = 200
OUTPUT = Path(__file__).with_name("catalog.json")

# How many videos to fully-extract per "videos" channel (full extraction = EXACT
# upload dates, but slower). The local bootstrap does the whole back-catalogue;
# the nightly job only refreshes the most recent ones and merges (see update_kidcrew).
BOOTSTRAP_VIDEO_LIMIT = 400
NIGHTLY_VIDEO_LIMIT = 5      # these channels post rarely; just catch new uploads

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


def ytdlp_json(base_cmd, url, extra=None, flat=True):
    cmd = base_cmd + ["--dump-single-json", "--no-warnings", "--ignore-errors"]
    if flat:
        cmd.append("--flat-playlist")   # fast list only; no exact dates
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


def ytdlp_video_stream(base_cmd, url, extra=None):
    """Full extraction that STREAMS one JSON per video, printing each as it arrives
    so you can watch progress. Returns a list of entry dicts."""
    cmd = base_cmd + ["--dump-json", "--no-warnings", "--ignore-errors"]
    if extra:
        cmd += extra
    cmd.append(url)
    entries = []
    # stderr is left attached to the terminal so throttling/errors are visible.
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
    for line in proc.stdout:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            v = json.loads(line)
        except json.JSONDecodeError:
            continue
        entries.append(v)
        title = (v.get("title") or "")[:60]
        print(f"      [{len(entries):>3}] {hms(v.get('duration')):>8}  {title}")
    proc.wait()
    return entries


def thumb(vid):
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"


def hms(seconds):
    if not seconds:
        return ""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_date(yyyymmdd):
    """'20250712' -> '12 Jul 2025' (cross-platform)."""
    s = str(yyyymmdd or "")
    if len(s) != 8 or not s.isdigit():
        return ""
    try:
        dt = datetime.datetime.strptime(s, "%Y%m%d")
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except ValueError:
        return ""


def epoch_to_date(ts):
    """Unix timestamp -> '12 Jul 2025'. The fast scrape returns dates this way."""
    try:
        if not ts:
            return ""
        dt = datetime.datetime.utcfromtimestamp(int(ts))
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except (ValueError, TypeError, OSError):
        return ""


def video_date(entry):
    return (fmt_date(entry.get("upload_date"))
            or epoch_to_date(entry.get("timestamp"))
            or epoch_to_date(entry.get("release_timestamp")))


def date_key(entry):
    """A comparable YYYYMMDD int for an entry's upload date, or None if unknown."""
    ud = str(entry.get("upload_date") or "")
    if len(ud) == 8 and ud.isdigit():
        return int(ud)
    for key in ("timestamp", "release_timestamp"):
        ts = entry.get(key)
        if ts:
            try:
                return int(datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y%m%d"))
            except (ValueError, TypeError, OSError):
                pass
    return None


def collect_videos(base_cmd, ch, limit):
    """Videos-tab mode: newest-first, up to `limit` videos, filtered by
    max_duration_seconds / min_date.

    Primary path is a full extraction (EXACT upload dates). Some channels (e.g. a
    "made for kids" channel) won't full-extract through yt-dlp even though the videos
    play fine elsewhere; if that comes back empty we fall back to the fast list
    (approximate dates) so the channel is never empty."""
    url = ch["url"].rstrip("/") + "/videos"
    max_dur = ch.get("max_duration_seconds")   # None -> no duration limit
    min_date = ch.get("min_date")              # "YYYYMMDD" -> only newer videos
    min_date_int = int(min_date) if min_date else None
    conds = []
    if max_dur:
        conds.append(f"< {max_dur // 60} min")
    if min_date_int:
        conds.append(f"on/after {min_date}")
    print(f"  scraping newest {limit} videos "
          f"(keeping {', '.join(conds) if conds else 'all'})…")

    def build(entries):
        over = before = 0
        out = []
        for v in entries:
            if not v or not v.get("id") or not v.get("title"):
                continue
            dur = v.get("duration")
            if max_dur and dur and dur > max_dur:
                over += 1
                continue
            if min_date_int:
                dk = date_key(v)
                if dk is None or dk < min_date_int:
                    before += 1
                    continue
            out.append({
                "name": v["title"],
                "videoId": v["id"],
                "thumbnail": thumb(v["id"]),
                "url": f"https://www.youtube.com/watch?v={v['id']}",
                "duration": int(dur) if dur else None,
                "durationText": hms(dur),
                "subtitle": video_date(v),   # exact if full extraction, else approximate
            })
        return out, over, before

    # Primary: full extraction (streamed, exact dates) — unless the channel opts out
    # (exact_dates: False) because it can't be full-extracted.
    eps, over, before = [], 0, 0
    if ch.get("exact_dates", True):
        eps, over, before = build(ytdlp_video_stream(
            base_cmd, url, extra=["--playlist-end", str(limit)]))

    # Fast list (approximate dates): used directly when exact_dates is False, or as a
    # fallback if the full extraction came back empty, so the channel is never empty.
    if not eps:
        if ch.get("exact_dates", True):
            print("      full extraction returned nothing — falling back to the fast list")
        else:
            print("      using the fast list (approximate dates)")
        data = ytdlp_json(base_cmd, url, extra=[
            "--playlist-end", str(limit),
            "--extractor-args", "youtubetab:approximate_date",
        ])
        eps, over, before = build((data or {}).get("entries") or [])

    print(f"      {over} over-length · {before} before cutoff · {len(eps)} kept")
    # Videos tab is already newest-first (reverse chronological).
    return {
        "id": "latest",
        "title": ch["title"],
        "color": ch.get("color"),
        "episodes": eps,
    }


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
            "durationText": hms(v.get("duration")),
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


def build_channel(base_cmd, ch, videos_limit=BOOTSTRAP_VIDEO_LIMIT):
    print(f"\n== {ch['title']} ==")

    if ch.get("source") == "videos":
        collection = collect_videos(base_cmd, ch, videos_limit)
        collections = [collection] if collection["episodes"] else []
        total = len(collection["episodes"])
        print(f"  => 1 collection, {total} videos")
        return {
            "id": ch["id"],
            "title": ch["title"],
            "youtubeChannelId": ch.get("youtubeChannelId"),
            "color": ch.get("color", "#4a6cf7"),
            "layout": "grid",  # wrapping grid of wider cards with dates
            "collections": collections,
        }

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
