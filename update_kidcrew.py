#!/usr/bin/env python3
"""
update_kidcrew.py  —  refresh the auto-updating channels in catalog.json

The nightly GitHub Action runs this. It re-scrapes every channel flagged
"auto_update": True in build_catalog.py (Kid Crew, Half-Asleep Chris, David Rule)
and leaves the others (e.g. Numberblocks) exactly as they are.

Bootstrap (one time): run  python build_catalog.py  to create catalog.json with
ALL channels, and commit it. After that this script keeps the video channels
current. Channel order follows the CHANNELS list in build_catalog.py.
"""

import json
import sys
from pathlib import Path

import build_catalog as bc

OUTPUT = Path(__file__).with_name("catalog.json")


def main():
    base_cmd = bc.check_ytdlp()

    existing = {}
    if OUTPUT.exists():
        data = json.loads(OUTPUT.read_text(encoding="utf-8"))
        for c in data.get("channels", []):
            existing[c.get("id")] = c
    else:
        print("WARNING: catalog.json not found — run build_catalog.py once to "
              "bootstrap it (playlist channels like Numberblocks will be missing "
              "until you do).", file=sys.stderr)

    channels = []
    refreshed = []
    for ch in bc.CHANNELS:
        if ch.get("auto_update"):
            channels.append(bc.build_channel(base_cmd, ch))   # re-scrape nightly
            refreshed.append(ch["title"])
        elif ch["id"] in existing:
            channels.append(existing[ch["id"]])               # preserve as-is

    catalog = {"generatedWith": "update_kidcrew.py", "channels": channels}
    OUTPUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print("Refreshed: " + ", ".join(refreshed) +
          ". Playlist channels left unchanged.")


if __name__ == "__main__":
    main()
