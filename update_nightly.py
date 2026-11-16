#!/usr/bin/env python3
"""
update_nightly.py  —  nightly refresh of the auto-updating channels.

Runs on the GitHub Action. For each channel flagged "auto_update": True in
build_catalog.CHANNELS (currently Kid Crew, Half-Asleep Chris, David Rule) it does a
fast flat scrape of the most recent videos (NIGHTLY_VIDEO_LIMIT) and merges them into
the existing catalog.json, leaving every other channel (Numberblocks, Postman Pat,
Octonauts, and any one-off CSV channels) exactly as they are.

Dates: this job does not fetch exact upload dates (full extraction is bot-blocked on
GitHub's datacenter IPs). A new video is stamped with the day the nightly first saw
it; known videos keep their stored date, so nothing drifts. Run build_catalog.py
locally if you ever want exact dates in the back-catalogue.
"""

import datetime
import json
import sys
from pathlib import Path

import build_catalog as bc

OUTPUT = Path(__file__).with_name("catalog.json")


def merge_recent(fresh_channel, existing_channel):
    """Recent episodes first, then the older tail already in the catalog (dedup by
    videoId), so history is preserved.

    Dates: the nightly uses the flat scrape, so it has no reliable upload date. A
    video already in the catalog keeps its stored date (frozen). A video seen for the
    first time is stamped with today's date (the day we found it), which for a job
    that runs regularly is within a day of the real upload. Dates never drift."""
    if not fresh_channel.get("collections"):
        # Nightly scrape returned nothing — keep what we already had.
        return existing_channel or fresh_channel

    fresh_eps = fresh_channel["collections"][0].get("episodes", [])
    existing_eps = []
    if existing_channel and existing_channel.get("collections"):
        existing_eps = existing_channel["collections"][0].get("episodes", [])

    found_date = bc.fmt_date(datetime.date.today().strftime("%Y%m%d"))
    existing_by_id = {e.get("videoId"): e for e in existing_eps}
    for e in fresh_eps:
        prev = existing_by_id.get(e.get("videoId"))
        if prev is None:
            e["subtitle"] = found_date            # new video: the day we found it
        elif prev.get("subtitle"):
            e["subtitle"] = prev["subtitle"]      # known video: keep its stored date

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
            # Force the fast flat scrape. Full extraction (for exact dates) is
            # bot-blocked from GitHub's datacenter IPs, and merge_recent stamps its own
            # found-date, so exact upload dates aren't needed or attempted here.
            nightly_ch = {**ch, "exact_dates": False}
            fresh = bc.build_channel(base_cmd, nightly_ch, videos_limit=bc.NIGHTLY_VIDEO_LIMIT)
            channels.append(merge_recent(fresh, existing.get(ch["id"])))
            refreshed.append(ch["title"])
        elif ch["id"] in existing:
            channels.append(existing[ch["id"]])   # preserve as-is (manual / one-off)

    catalog = {"generatedWith": "update_nightly.py", "channels": channels}
    OUTPUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print("Refreshed recent videos for: " + ", ".join(refreshed))


if __name__ == "__main__":
    main()
