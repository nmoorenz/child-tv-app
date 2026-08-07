#!/usr/bin/env python3
"""
channel_metadata.py  —  quick metadata dump for a YouTube channel.

Flat-scrapes a channel's Videos tab (fast; no exact dates) and writes a CSV of
every video — title, length, approximate date, id, url — so you can open it in a
spreadsheet, sort by duration_seconds, and see the shape of the channel before
deciding what to include.

(channel_to_csv.py does something similar with extra compilation-guessing columns;
this is the lean version.)

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python channel_metadata.py
          -> Genevieve's Playhouse

      python channel_metadata.py https://www.youtube.com/@SomeChannel
          -> any channel

  Output: <handle>_videos.csv  (next to this script)
--------------------------------------------------------------------
"""

import csv
import re
import sys
from pathlib import Path

import build_catalog as bc

DEFAULT_URL = "https://www.youtube.com/@GenevievesPlayhouse"


def slug(url):
    m = re.search(r"@([A-Za-z0-9_.-]+)", url)
    return m.group(1).lower() if m else "channel"


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    url = target.rstrip("/")
    if not url.endswith("/videos"):
        url += "/videos"
    out = Path(__file__).with_name(f"{slug(target)}_videos.csv")

    base_cmd = bc.check_ytdlp()
    print(f"Scraping {url} … (flat, can take a minute for a big channel)")
    data = bc.ytdlp_json(base_cmd, url,
                         extra=["--extractor-args", "youtubetab:approximate_date"])
    entries = (data or {}).get("entries") or []

    n = 0
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["title", "duration_seconds", "durationText", "date",
                    "videoId", "url", "keep"])
        for e in entries:
            if not e or not e.get("id"):
                continue
            dur = e.get("duration")
            w.writerow([
                e.get("title") or "",
                int(dur) if dur else "",
                bc.hms(dur),
                bc.video_date(e),
                e["id"],
                f"https://www.youtube.com/watch?v={e['id']}",
                "",   # keep: mark the rows you want (e.g. "y") for later processing
            ])
            n += 1

    print(f"\nWrote {out}  ({n} videos)")
    print("Open it and sort by duration_seconds to see the channel's shape.")


if __name__ == "__main__":
    main()
