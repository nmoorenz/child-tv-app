#!/usr/bin/env python3
"""
build_octonauts.py  —  turn octonauts_deduped.csv into the catalog channel.

Reads octonauts_deduped.csv (from dedupe_octonauts.py, after any manual edits) and
splices an "Octonauts" channel into catalog.json, leaving every other channel as
it is. Episodes are grouped into navigation rows: Season 1 (numbered), Season 1
(unnumbered), Season 2, 3, 4 (and any higher season), then episodes that have only
a number, then everything else. Ordered by episode number. Emoji kept in titles.

Octonauts is flagged "manual": True in build_catalog.py, so a normal
build_catalog.py run won't overwrite what this inserts.

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python build_octonauts.py
  Updates: catalog.json
--------------------------------------------------------------------
"""

import csv
import json
import re
from pathlib import Path

import build_catalog as bc

CSV_IN = Path(__file__).with_name("octonauts_deduped.csv")
CATALOG = Path(__file__).with_name("catalog.json")


def get_octonauts_channel():
    for c in bc.CHANNELS:
        if c["id"] == "octonauts":
            return c
    return {"id": "octonauts", "title": "Octonauts", "color": "#1e6fb8"}


def sort_key(name):
    # Alphabetical by the episode name, ignoring leading emoji/punctuation.
    return re.sub(r"[^a-z0-9 ]+", "", bc.strip_emoji(name).lower()).strip()


def to_int(s):
    s = (s or "").strip()
    try:
        return int(float(s))
    except ValueError:
        return None


def build_channel(ch):
    if not CSV_IN.exists():
        raise SystemExit(f"{CSV_IN.name} not found — run dedupe_octonauts.py first")

    with CSV_IN.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # Navigation buckets (order matters — this is the row order in the app):
    #   Season 1 with an episode number, Season 1 without, Season 2, 3, 4 (and any
    #   higher season), then episodes with only a number, then everything else.
    s1_numbered, s1_plain = [], []
    other_seasons = {}      # season (!= 1) -> [episode, ...]
    episode_only, leftover = [], []
    for r in rows:
        vid = (r.get("videoId") or "").strip()
        name = (r.get("title") or "").strip()
        if not vid or not name:
            continue
        season = to_int(r.get("season"))
        episode = to_int(r.get("episode"))
        ep = {
            "name": name,                       # emoji kept
            "videoId": vid,
            "thumbnail": bc.thumb(vid),
            "url": r.get("url") or f"https://www.youtube.com/watch?v={vid}",
            "durationText": (r.get("durationText") or "").strip(),
        }
        if episode is not None:
            ep["episode"] = episode
            ep["episode_index"] = episode
            ep["subtitle"] = f"Episode {episode}"
        if season is not None:
            ep["season"] = season

        if season == 1 and episode is not None:
            s1_numbered.append(ep)
        elif season == 1:
            s1_plain.append(ep)
        elif season is not None:
            other_seasons.setdefault(season, []).append(ep)
        elif episode is not None:
            episode_only.append(ep)
        else:
            leftover.append(ep)

    def order(eps):
        # By episode number when present, otherwise alphabetically by name.
        return sorted(eps, key=lambda e: (e.get("episode") is None,
                                          e.get("episode") or 0, sort_key(e["name"])))

    collections = []
    if s1_numbered:
        collections.append({"id": "season-1", "title": "Season 1",
                            "episodes": order(s1_numbered)})
    if s1_plain:
        collections.append({"id": "season-1-plain", "title": "Season 1 (unnumbered)",
                            "episodes": order(s1_plain)})
    for s in sorted(other_seasons):
        collections.append({"id": f"season-{s}", "title": f"Season {s}",
                            "episodes": order(other_seasons[s])})
    if episode_only:
        collections.append({"id": "episode-only", "title": "Numbered episodes",
                            "episodes": order(episode_only)})
    if leftover:
        collections.append({"id": "other", "title": "Other",
                            "episodes": order(leftover)})

    total = sum(len(c["episodes"]) for c in collections)
    print(f"{total} episodes -> {len(collections)} groups: "
          + ", ".join(f"{c['title']} ({len(c['episodes'])})" for c in collections))
    return {
        "id": ch["id"],
        "title": ch.get("title", "Octonauts"),
        "color": ch.get("color", "#1e6fb8"),
        "collections": collections,   # rows per season (no "grid" layout)
    }


def main():
    ch = get_octonauts_channel()
    octo = build_channel(ch)

    if CATALOG.exists():
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    else:
        print(f"{CATALOG.name} not found — creating a new one with just Octonauts")
        catalog = {"generatedWith": "build_catalog.py", "channels": []}

    channels = catalog.setdefault("channels", [])
    for i, c in enumerate(channels):
        if c.get("id") == octo["id"]:
            channels[i] = octo        # replace in place
            break
    else:
        channels.append(octo)         # new -> append

    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False),
                       encoding="utf-8")
    print(f"Updated {CATALOG} — Octonauts spliced in, other channels untouched.")


if __name__ == "__main__":
    main()
