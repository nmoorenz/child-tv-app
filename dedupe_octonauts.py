#!/usr/bin/env python3
"""
dedupe_octonauts.py  —  collapse duplicate Octonauts episodes.

Reads octonauts_videos.csv (the channel_to_csv.py scrape, after you've trimmed it
to just the ~10-minute episodes) and writes octonauts_deduped.csv: one row per
unique episode, with a `copies` count and the video ids that were merged.

Duplicates are detected with a key that ignores the things that make copies look
different — emoji, spacing around dashes, punctuation, capitalisation, and filler
words like "The"/"Octonauts". The DISPLAYED title keeps its emoji (a properly
capitalised, emoji-bearing version is chosen). Season and episode numbers are
pulled into their own columns so you can group by them; the `animal` column is a
rough first pass for you to refine.

Review octonauts_deduped.csv (delete rows or fix titles by hand if needed), then
build_octonauts.py turns it into the catalog channel.

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python dedupe_octonauts.py
  Input:  octonauts_videos.csv
  Output: octonauts_deduped.csv
--------------------------------------------------------------------
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

import build_catalog as bc

CSV_IN = Path(__file__).with_name("octonauts_videos.csv")
CSV_OUT = Path(__file__).with_name("octonauts_deduped.csv")

# Filler words that shouldn't affect whether two titles are "the same".
OCTO_STOP = {"the", "a", "an", "and", "of", "octonauts", "creature", "report"}


def dedup_key(name):
    """Emoji/punctuation/case/filler-insensitive key. Word order is preserved so
    genuinely different episodes aren't merged just for sharing words."""
    s = bc.strip_emoji(name).lower()
    s = s.replace("’", "").replace("'", "")        # Lion's -> lions (not "lion s")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [t for t in s.split() if t not in OCTO_STOP]
    return " ".join(toks)


def emoji_count(name):
    return len("".join(bc._EMOJI_RE.findall(name or "")))


def animal_guess(name):
    """Rough first pass at the featured animal: emoji stripped, leading article
    dropped. This is only approximate — pin down the real animal with an LLM pass
    over the finished list (a regex can't tell a species name from an adjective)."""
    s = bc.strip_emoji(name)
    s = re.sub(r"^\s*(the|a|an)\s+", "", s, flags=re.I)
    return s.strip()


def rep_score(name):
    """Pick a nice representative: has emoji, then properly capitalised, then more
    emoji, then longer. Keeps emoji while avoiding an all-lowercase title."""
    return (emoji_count(name) > 0,
            any(c.isupper() for c in name),
            emoji_count(name),
            len(name))


def to_int(s):
    s = (s or "").strip()
    try:
        return int(float(s))
    except ValueError:
        return None


def get_octonauts_channel():
    for c in bc.CHANNELS:
        if c["id"] == "octonauts":
            return c
    return {}   # config is optional here; window guard just won't apply


def main():
    if not CSV_IN.exists():
        raise SystemExit(f"{CSV_IN.name} not found — run: "
                         f"python channel_to_csv.py https://www.youtube.com/@Octonauts")

    ch = get_octonauts_channel()
    min_dur = ch.get("min_duration_seconds", 0)
    max_dur = ch.get("max_duration_seconds")

    with CSV_IN.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows from {CSV_IN.name}")

    groups = defaultdict(list)   # key -> [candidate, ...]
    dropped = 0
    for r in rows:
        raw = r.get("title") or ""
        dur = to_int(r.get("duration_seconds"))
        # Guard: skip anything outside the window (you should already have trimmed).
        if dur is not None and (dur < min_dur or (max_dur and dur > max_dur)):
            dropped += 1
            continue
        name, season, episode = bc.clean_octonauts_title(raw)   # keep emoji
        key = dedup_key(name)
        if not key:
            continue
        groups[key].append({
            "name": name,
            "season": season,
            "episode": episode,
            "durationText": (r.get("duration") or "").strip() or bc.hms(dur),
            "durationSeconds": dur if dur is not None else "",
            "videoId": (r.get("videoId") or "").strip(),
            "url": (r.get("url") or "").strip(),
        })

    out = []
    for key, cands in groups.items():
        # Representative: keep emoji, prefer a properly-capitalised version.
        rep = max(cands, key=lambda c: rep_score(c["name"]))
        merged = [c["videoId"] for c in cands if c["videoId"] != rep["videoId"]]
        # Season / episode: take the first copy that actually has one.
        season = next((c["season"] for c in cands if c["season"] is not None), "")
        episode = next((c["episode"] for c in cands if c["episode"] is not None), "")
        out.append({
            "title": rep["name"],
            "animal": animal_guess(rep["name"]),   # approximate — you'll refine
            "season": season,
            "episode": episode,
            "copies": len(cands),
            "durationText": rep["durationText"],
            "durationSeconds": rep["durationSeconds"],
            "videoId": rep["videoId"],
            "url": rep["url"],
            "mergedVideoIds": ";".join(merged),
            "_key": key,
        })

    # Order by season, then episode, then name (blanks sort last).
    out.sort(key=lambda r: (r["season"] == "", r["season"] or 0,
                            r["episode"] == "", r["episode"] or 0, r["_key"]))

    fields = ["title", "animal", "season", "episode", "copies", "durationText",
              "durationSeconds", "videoId", "url", "mergedVideoIds"]
    with CSV_OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in out:
            w.writerow({k: r[k] for k in fields})

    total_copies = sum(r["copies"] for r in out)
    dup_rows = sum(1 for r in out if r["copies"] > 1)
    print(f"{dropped} outside window skipped" if dropped else "0 skipped")
    print(f"{total_copies} videos -> {len(out)} unique episodes "
          f"({dup_rows} had duplicates merged)")
    print(f"\nWrote {CSV_OUT}")
    print("Check the 'copies' column and spot-check merges (mergedVideoIds), then:")
    print("  python build_octonauts.py")


if __name__ == "__main__":
    main()
