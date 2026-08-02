#!/usr/bin/env python3
"""
update_kidcrew.py  —  nightly refresh of the auto-updating channels

Runs on the GitHub Action. For each channel flagged "auto_update": True it
re-scrapes only the most recent videos (NIGHTLY_VIDEO_LIMIT) with exact dates, then
MERGES them into the existing catalog.json — keeping the older episodes (and their
exact dates from your one-time local build_catalog.py run) untouched. Channels
without "auto_update" (e.g. Numberblocks) are left exactly as they are.

Bootstrap once, locally:  python build_catalog.py   (does the full back-catalogue
with exact dates), then commit catalog.json.
"""

import json
import sys
from pathlib import Path

import build_catalog as bc

OUTPUT = Path(__file__).with_name("catalog.json")


def merge_recent(fresh_channel, existing_channel):
    """Recent exact episodes first, then the older tail already in the catalog
    (dedup by videoId) so history and older exact dates are preserved."""
    if not fresh_channel.get("collections"):
        # Nightly scrape returned nothing — keep what we already had.
        return existing_channel or fresh_channel

    fresh_eps = fresh_channel["collections"][0].get("episodes", [])
    existing_eps = []
    if existing_channel and existing_channel.get("collections"):
        existing_eps = existing_channel["collections"][0].get("episodes", [])

    fresh_ids = {e.get("videoId") for e in fresh_eps}
    tail = [e for e in existing_eps if e.get("videoId") not in fresh_ids]
    fresh_channel["collections"][0]["episodes"] = fresh_eps + tail
    return fresh_channel


def main():
    base_cmd = bc.check_ytdlp()

    existing = {}
    if OUTPUT.exists():
        data = json.loads(OUTPUT.read_text(encoding="utf-8"))
        for c in data.get("channels", []):
            existing[c.get("id")] = c
    else:
        print("WARNING: catalog.json not found — run build_catalog.py once to "
              "bootstrap it.", file=sys.stderr)

    channels = []
    refreshed = []
    for ch in bc.CHANNELS:
        if ch.get("auto_update"):
            fresh = bc.build_channel(base_cmd, ch, videos_limit=bc.NIGHTLY_VIDEO_LIMIT)
            channels.append(merge_recent(fresh, existing.get(ch["id"])))
            refreshed.append(ch["title"])
        elif ch["id"] in existing:
            channels.append(existing[ch["id"]])   # preserve as-is

    catalog = {"generatedWith": "update_kidcrew.py", "channels": channels}
    OUTPUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print("Refreshed recent videos for: " + ", ".join(refreshed))


if __name__ == "__main__":
    main()
