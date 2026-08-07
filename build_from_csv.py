#!/usr/bin/env python3
"""
build_from_csv.py  —  build a catalog channel from a curated CSV.

Generic, reusable version of the per-channel builders. Point it at a CSV (e.g.
one from channel_metadata.py, with the rows you want marked in the `keep` column)
and it splices a channel into catalog.json, leaving every other channel untouched.

Reuse this for any straightforward channel instead of writing a new script.

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
  Flat grid of the kept rows:
      python build_from_csv.py genevievesplayhouse_videos.csv \
          --id genevieve --title "Genevieve's Playhouse"

  Grouped into "Season N" rows (uses season/episode CSV columns if present,
  otherwise parses them from the title):
      python build_from_csv.py some_videos.csv --id foo --title "Foo" --layout seasons

  Options:
      --color "#1e6fb8"     accent colour
      --layout grid|seasons  (default grid)
      --clean-title          show only the text before the first " | "
      --url  <channel url>   included in the reminder snippet at the end

  Rows: if the CSV has a `keep` column with anything marked, only those rows are
  used; otherwise every row is used.
--------------------------------------------------------------------
"""

import argparse
import csv
import json
import re
from pathlib import Path

import build_catalog as bc

CATALOG = Path(__file__).with_name("catalog.json")


def kept_rows(rows):
    marked = [r for r in rows if (r.get("keep") or "").strip()]
    return marked if marked else rows


def clean_title(title):
    return title.split("|")[0].strip()


def parse_se(title):
    """Best-effort season/episode from a title (Season 3 / S1E2 / Episode 5)."""
    season = episode = None
    m = re.search(r"\bs(\d+)\s*e\s*(\d+)\b", title, re.I)
    if m:
        season, episode = int(m.group(1)), int(m.group(2))
    if season is None:
        m = re.search(r"season\s+(\d+)", title, re.I)
        if m:
            season = int(m.group(1))
    if episode is None:
        m = (re.search(r"\bepisode\s*(\d+)\b", title, re.I)
             or re.search(r"\bep\.?\s*(\d+)\b", title, re.I))
        if m:
            episode = int(m.group(1))
    return season, episode


def to_int(s):
    s = (s or "").strip()
    try:
        return int(float(s))
    except ValueError:
        return None


def make_episode(row, use_clean):
    vid = (row.get("videoId") or "").strip()
    raw = (row.get("title") or "").strip()
    if not vid or not raw:
        return None
    name = clean_title(raw) if use_clean else raw
    dur_txt = (row.get("durationText") or "").strip() or bc.hms(to_int(row.get("duration_seconds")))
    ep = {
        "name": name,
        "videoId": vid,
        "thumbnail": bc.thumb(vid),
        "url": (row.get("url") or "").strip() or f"https://www.youtube.com/watch?v={vid}",
        "durationText": dur_txt,
    }
    if (row.get("date") or "").strip():
        ep["subtitle"] = row["date"].strip()
    return ep


def build_grid(rows, use_clean):
    episodes = [ep for r in rows if (ep := make_episode(r, use_clean))]
    return [{"id": "episodes", "title": "Full Episodes", "episodes": episodes}] if episodes else []


def build_seasons(rows, use_clean):
    by_season, other = {}, []
    for r in rows:
        ep = make_episode(r, use_clean)
        if not ep:
            continue
        season = to_int(r.get("season"))
        episode = to_int(r.get("episode"))
        if season is None and episode is None:          # nothing in columns
            season, episode = parse_se(r.get("title") or "")
        if episode is not None:
            ep["episode"] = episode
            ep["episode_index"] = episode
            ep["subtitle"] = f"Episode {episode}"
        if season is not None:
            ep["season"] = season
            by_season.setdefault(season, []).append(ep)
        else:
            other.append(ep)

    def order(eps):
        return sorted(eps, key=lambda e: (e.get("episode") is None, e.get("episode") or 0,
                                          e["name"].lower()))

    collections = [{"id": f"season-{s}", "title": f"Season {s}", "episodes": order(by_season[s])}
                   for s in sorted(by_season)]
    if other:
        collections.append({"id": "other", "title": "Other", "episodes": order(other)})
    return collections


def main():
    ap = argparse.ArgumentParser(description="Build a catalog channel from a CSV.")
    ap.add_argument("csv", help="path to the curated CSV")
    ap.add_argument("--id", required=True, help="channel id (e.g. genevieve)")
    ap.add_argument("--title", required=True, help='channel title (e.g. "Genevieve\'s Playhouse")')
    ap.add_argument("--color", default="#4a6cf7", help="accent colour hex")
    ap.add_argument("--layout", choices=["grid", "seasons"], default="grid")
    ap.add_argument("--clean-title", action="store_true",
                    help='show only the text before the first " | "')
    ap.add_argument("--url", default="", help="channel URL (for the reminder snippet)")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"{csv_path} not found")

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = kept_rows(list(csv.DictReader(f)))

    if args.layout == "seasons":
        collections = build_seasons(rows, args.clean_title)
    else:
        collections = build_grid(rows, args.clean_title)

    channel = {"id": args.id, "title": args.title, "color": args.color}
    if args.layout == "grid":
        channel["layout"] = "grid"
    channel["collections"] = collections

    total = sum(len(c["episodes"]) for c in collections)
    print(f"{total} episodes -> {len(collections)} "
          f"{'group(s)' if args.layout == 'seasons' else 'grid'} from {len(rows)} kept rows")

    if CATALOG.exists():
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    else:
        print(f"{CATALOG.name} not found — creating a new one")
        catalog = {"generatedWith": "build_catalog.py", "channels": []}

    channels = catalog.setdefault("channels", [])
    for i, c in enumerate(channels):
        if c.get("id") == channel["id"]:
            channels[i] = channel
            break
    else:
        channels.append(channel)

    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {CATALOG} — '{args.title}' spliced in, other channels untouched.")

    # Register a manual:True stub in build_catalog.py so a full rebuild / the nightly
    # job never drops this one-off channel. Idempotent.
    if bc.register_manual_stub(args.id, args.title, args.url or None, args.color):
        print(f"Added a manual:True stub for '{args.id}' to build_catalog.py.")
    else:
        print(f"'{args.id}' already has an entry in build_catalog.py — left as is.")


if __name__ == "__main__":
    main()
