#!/usr/bin/env python3
"""
postman_pat_metadata.py  —  step 1 of the one-time Postman Pat pipeline.

Scrapes EVERY video on the Postman Pat channel (~1300, well past the 400-latest
limit the main build_catalog.py uses) and writes the raw list to
postman_pat_videos.json.

This is the slow part, so it's separate: run it once, then iterate on matching
(step 2, match_postman_pat.py) as often as you like without re-downloading.

A flat scrape is enough here — we only need each video's id, title and duration.
Upload dates don't matter because episodes are ordered by the Wikipedia series /
episode list, not by date.

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python postman_pat_metadata.py
  Output: postman_pat_videos.json  (next to this script)

  Optional: cap how many to scrape (handy for a quick test run):
      python postman_pat_metadata.py --limit 50
--------------------------------------------------------------------
"""

import json
import sys
from pathlib import Path

import build_catalog as bc

OUTPUT = Path(__file__).with_name("postman_pat_videos.json")


def get_pat_channel():
    for c in bc.CHANNELS:
        if c["id"] == "postmanpat":
            return c
    raise SystemExit("No 'postmanpat' channel found in build_catalog.CHANNELS")


def main():
    limit = None
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        try:
            limit = int(sys.argv[i + 1])
        except (IndexError, ValueError):
            raise SystemExit("--limit needs a number, e.g. --limit 50")

    ch = get_pat_channel()
    base_cmd = bc.check_ytdlp()
    url = ch["url"].rstrip("/") + "/videos"

    extra = ["--extractor-args", "youtubetab:approximate_date"]
    if limit:
        extra += ["--playlist-end", str(limit)]

    print(f"Scraping {url} … (this can take a few minutes for the full channel)")
    data = bc.ytdlp_json(base_cmd, url, extra=extra)
    entries = (data or {}).get("entries") or []

    out = []
    for v in entries:
        if not v or not v.get("id") or not v.get("title"):
            continue
        out.append({
            "id": v["id"],
            "title": v["title"],
            "duration": v.get("duration"),
            "date": bc.video_date(v),   # approximate; informational only
        })

    OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUTPUT}  ({len(out)} videos)")
    print("Next: python match_postman_pat.py")


if __name__ == "__main__":
    main()
