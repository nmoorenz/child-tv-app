#!/usr/bin/env python3
"""
update_kidcrew.py  —  refresh ONLY the Kid Crew channel in catalog.json

The nightly GitHub Action runs this. It re-scrapes just Kid Crew (Videos tab,
< 30 min, newest first) and drops it into the existing catalog.json, leaving the
Numberblocks channel exactly as it is. Numberblocks is generated once by
build_catalog.py and never re-scraped after that.

Bootstrap (one time): run  python build_catalog.py  to create catalog.json with
BOTH channels, and commit it. After that this script keeps Kid Crew current.
"""

import json
import sys
from pathlib import Path

import build_catalog as bc

OUTPUT = Path(__file__).with_name("catalog.json")
KIDCREW_ID = "kidcrew"


def main():
    base_cmd = bc.check_ytdlp()

    kc_config = next((c for c in bc.CHANNELS if c.get("id") == KIDCREW_ID), None)
    if not kc_config:
        sys.exit("No 'kidcrew' channel found in build_catalog.CHANNELS")

    # Scrape just Kid Crew.
    kidcrew_channel = bc.build_channel(base_cmd, kc_config)

    # Load the existing catalog (must already contain Numberblocks).
    if OUTPUT.exists():
        catalog = json.loads(OUTPUT.read_text(encoding="utf-8"))
    else:
        print("WARNING: catalog.json not found — run build_catalog.py once to "
              "bootstrap it (Numberblocks will be missing until you do).",
              file=sys.stderr)
        catalog = {"generatedWith": "build_catalog.py", "channels": []}

    channels = [c for c in catalog.get("channels", []) if c.get("id") != KIDCREW_ID]
    channels.append(kidcrew_channel)  # add/replace Kid Crew (kept last)
    catalog["channels"] = channels

    OUTPUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    kept = sum(len(col["episodes"]) for col in kidcrew_channel["collections"])
    print(f"Kid Crew refreshed: {kept} videos. Numberblocks left unchanged.")


if __name__ == "__main__":
    main()
