#!/usr/bin/env python3
"""
build_postman_pat.py  —  step 3 of the one-time Postman Pat pipeline.

Reads postman_pat_matched.csv (from step 2, after any manual edits), groups the
episodes into "Series N" collections, and splices the Postman Pat channel into
the existing catalog.json — leaving every other channel exactly as it is.

Because Postman Pat is flagged "manual": True in build_catalog.py, a normal
build_catalog.py run will NOT overwrite what this script inserts. To pick up new
episodes later, re-run the three steps (or hand-add a row to the CSV and re-run
just this one).

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python build_postman_pat.py
  Updates: catalog.json  (next to this script)
--------------------------------------------------------------------
"""

import csv
import json
from pathlib import Path

import build_catalog as bc

CSV_IN = Path(__file__).with_name("postman_pat_matched.csv")
CATALOG = Path(__file__).with_name("catalog.json")

# Series to leave out of the catalog entirely.
EXCLUDE_SERIES = {1, 2, 8}


def get_pat_channel():
    for c in bc.CHANNELS:
        if c["id"] == "postmanpat":
            return c
    raise SystemExit("No 'postmanpat' channel found in build_catalog.CHANNELS")


def to_int(s):
    s = (s or "").strip()
    try:
        return int(float(s))   # tolerate "1.0" from spreadsheet edits
    except ValueError:
        return None


def build_channel(ch):
    if not CSV_IN.exists():
        raise SystemExit(f"{CSV_IN.name} not found — run match_postman_pat.py first")

    with CSV_IN.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    matched = {}   # (series, episode) -> episode dict
    others = []
    excluded = 0
    for r in rows:
        vid = (r.get("videoId") or "").strip()
        if not vid:
            continue
        series = to_int(r.get("series"))
        episode = to_int(r.get("episode"))
        cap = to_int(r.get("capSeconds"))

        # Prefer the canonical Wikipedia title; fall back to the video's own.
        name = ((r.get("wikiTitle") or "").strip()
                or (r.get("cleanTitle") or "").strip()
                or "Postman Pat")
        ep = {
            "name": name,
            "videoId": vid,
            "thumbnail": bc.thumb(vid),
            "url": r.get("url") or f"https://www.youtube.com/watch?v={vid}",
            "durationText": (r.get("durationText") or "").strip(),
        }
        if cap:
            ep["capSeconds"] = cap
        if series is not None and episode is not None:
            if series in EXCLUDE_SERIES:
                excluded += 1
                continue
            ep["season"] = series
            ep["episode"] = episode
            ep["episode_index"] = episode
            ep["subtitle"] = f"Episode {episode}"
            matched.setdefault((series, episode), ep)   # de-dupe by S/E
        else:
            if r.get("date"):
                ep["subtitle"] = r["date"]
            others.append(ep)

    collections = []
    for s in sorted({se[0] for se in matched}):
        eps = sorted((e for k, e in matched.items() if k[0] == s),
                     key=lambda x: x["episode"])
        collections.append({"id": f"series-{s}", "title": f"Series {s}", "episodes": eps})
    if others:
        collections.append({"id": "other", "title": "Other", "episodes": others})

    total = sum(len(c["episodes"]) for c in collections)
    matched_count = total - len(others)
    print(f"{total} episodes -> {len(collections)} collections "
          f"({matched_count} in a series, {len(others)} in Other); "
          f"{excluded} dropped from excluded series {sorted(EXCLUDE_SERIES)}")
    return {
        "id": ch["id"],
        "title": ch["title"],
        "color": ch.get("color", "#4a6cf7"),
        "collections": collections,   # no "grid" layout -> rows per series
    }


def main():
    ch = get_pat_channel()
    pat = build_channel(ch)

    if CATALOG.exists():
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    else:
        print(f"{CATALOG.name} not found — creating a new one with just Postman Pat")
        catalog = {"generatedWith": "build_catalog.py", "channels": []}

    channels = catalog.setdefault("channels", [])
    for i, c in enumerate(channels):
        if c.get("id") == pat["id"]:
            channels[i] = pat        # replace in place, keep position
            break
    else:
        channels.append(pat)         # new channel -> append

    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False),
                       encoding="utf-8")
    print(f"Updated {CATALOG} — Postman Pat spliced in, other channels untouched.")


if __name__ == "__main__":
    main()
