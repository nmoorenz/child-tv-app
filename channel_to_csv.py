#!/usr/bin/env python3
"""
channel_to_csv.py  —  dump a YouTube channel's videos to a CSV (with lengths)

Scrapes every video on a channel's "Videos" tab using yt-dlp (NO API key) and
writes a spreadsheet-friendly CSV. Open it in Excel/Numbers/Sheets and sort by
the `duration_seconds` column to see where the long compilations start — that's
your cutoff. Then send the CSV back and we'll keep only what you want.

--------------------------------------------------------------------
SETUP (one time)
--------------------------------------------------------------------
  1. Install Python 3.9+     https://www.python.org/downloads/
  2. Install yt-dlp:         pip install -U yt-dlp

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
  Default (Kid Crew):
      python channel_to_csv.py

  Any channel:
      python channel_to_csv.py https://www.youtube.com/@SomeChannel

  Output: a CSV named after the channel, e.g. kidcrew_videos.csv
--------------------------------------------------------------------
"""

import csv
import json
import re
import subprocess
import sys
import shutil

DEFAULT_CHANNEL = "https://www.youtube.com/@KidCrew"

# Titles containing any of these are flagged as *maybe* a compilation (advisory
# only — you decide from the length). Case-insensitive.
COMPILATION_HINTS = [
    "compilation", "compilations", "mix", "full episode", "full episodes",
    "marathon", "best of", "hour", "hours", "all ", "mega", "non stop",
    "nonstop", "back to back", "1 hour", "2 hour",
]
LONG_SECONDS = 600  # 10 min: also flags anything this long as maybe-compilation


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


def hms(seconds):
    if not seconds:
        return ""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def channel_slug(url):
    m = re.search(r"@([A-Za-z0-9_.-]+)", url)
    if m:
        return m.group(1).lower()
    m = re.search(r"/(channel|c|user)/([A-Za-z0-9_-]+)", url)
    return (m.group(2).lower() if m else "channel")


def looks_like_compilation(title, seconds):
    t = (title or "").lower()
    if seconds and seconds >= LONG_SECONDS:
        return "yes"
    if any(k in t for k in COMPILATION_HINTS):
        return "yes"
    return ""


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CHANNEL
    if "list=" in target or "/playlist" in target:      # a playlist URL
        scrape_url = target
        m = re.search(r"list=([A-Za-z0-9_-]+)", target)
        out_name = f"playlist_{m.group(1) if m else 'x'}_videos.csv"
    else:                                               # a channel
        scrape_url = target.rstrip("/")
        if not scrape_url.endswith("/videos"):
            scrape_url += "/videos"
        out_name = f"{channel_slug(target)}_videos.csv"

    base_cmd = check_ytdlp()
    print(f"Scraping {scrape_url} … (this can take a minute)")

    cmd = base_cmd + ["--flat-playlist", "--dump-single-json",
                      "--no-warnings", "--ignore-errors", scrape_url]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not proc.stdout.strip():
        print("yt-dlp returned nothing:\n" + proc.stderr[:500], file=sys.stderr)
        sys.exit(1)

    data = json.loads(proc.stdout)
    entries = [e for e in (data.get("entries") or []) if e and e.get("id")]

    with open(out_name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "title", "duration_seconds", "duration", "upload_date",
            "view_count", "maybe_compilation", "videoId", "url", "keep",
        ])
        for e in entries:
            dur = e.get("duration")
            title = e.get("title") or ""
            w.writerow([
                title,
                int(dur) if dur else "",
                hms(dur),
                e.get("upload_date") or "",
                e.get("view_count") or "",
                looks_like_compilation(title, dur),
                e["id"],
                f"https://www.youtube.com/watch?v={e['id']}",
                "",  # <- you fill this: put "y" on the rows you want to keep
            ])

    print(f"\nWrote {out_name}  ({len(entries)} videos)")
    print("Open it in a spreadsheet, sort by 'duration_seconds', find the cutoff,")
    print("and either mark 'y' in the 'keep' column or just tell me the cutoff length.")


if __name__ == "__main__":
    main()
