#!/usr/bin/env python3
"""
match_postman_pat.py  —  step 2 of the one-time Postman Pat pipeline.

Reads postman_pat_videos.json (from step 1) and writes postman_pat_matched.csv,
built around the Wikipedia episode list so you can see coverage at a glance.

The CSV has two parts:

  SECTION A — every Wikipedia episode, in order (series, episode).
    For each canonical episode it shows the single BEST matching video (exact
    title match preferred, then closest fuzzy match), plus videoCount = how many
    videos matched that episode (so duplicates are visible). Episodes with no
    match have videoCount 0 and blank video cells — those are your gaps.

  SECTION B — videos that matched no episode (below a separator row).
    One row each, with series/episode left blank so you can assign them by hand.

Re-run as often as you like while tuning — it never re-scrapes. Shared logic
(title cleaning, wiki loading) is imported from build_catalog.py.

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python match_postman_pat.py
  Output: postman_pat_matched.csv  (next to this script)

  Looser / stricter matching (default 0.72; lower = more matches):
      python match_postman_pat.py --cutoff 0.65
--------------------------------------------------------------------
"""

import csv
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import build_catalog as bc

VIDEOS_IN = Path(__file__).with_name("postman_pat_videos.json")
CSV_OUT = Path(__file__).with_name("postman_pat_matched.csv")

# Similarity threshold for a fuzzy title match. Lower = looser (more matches, but
# more to spot-check); higher = stricter. Override on the command line with
# --cutoff. Fuzzy matches are flagged "fuzzy" in the CSV so you can review them.
DEFAULT_CUTOFF = 0.72

# Emoji / pictograph ranges to strip from YouTube titles (keeps normal punctuation).
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # emoticons, pictographs, transport, supplemental, cards
    "\U00002600-\U000026FF"   # miscellaneous symbols
    "\U00002700-\U000027BF"   # dingbats
    "\U0001F1E6-\U0001F1FF"   # regional indicator letters (flags)
    "\U00002B00-\U00002BFF"   # miscellaneous symbols and arrows
    "\U00002300-\U000023FF"   # misc technical (hourglass, etc.)
    "\U0001F3FB-\U0001F3FF"   # skin-tone modifiers
    "\U000E0000-\U000E007F"   # tag characters (used in flag sequences)
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(s):
    s = _EMOJI_RE.sub("", s or "")
    s = s.replace("‍", "").replace("️", "")   # ZWJ + variation selector
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s.strip(" -–—|").strip()


# Filler words dropped before comparing titles, so "Postman Pat and the Runaway
# Train" and "Runaway Train" both reduce to "runaway train". This matters because
# character-similarity matching is thrown off by long shared prefixes.
STOPWORDS = {
    "postman", "pat", "the", "a", "an", "and", "of", "to", "on", "in", "for",
    "with", "full", "episode", "episodes", "kids", "kid", "cartoon", "cartoons",
    "children", "official", "compilation", "compilations", "video", "videos",
    "series", "special", "delivery", "service", "hd", "new",
}


def match_key(name):
    """Normalised title reduced to its significant words (filler removed)."""
    toks = [t for t in bc.norm_title(name).split() if t not in STOPWORDS]
    key = " ".join(toks)
    return key or bc.norm_title(name)   # fall back if it was all filler


def get_pat_channel():
    for c in bc.CHANNELS:
        if c["id"] == "postmanpat":
            return c
    raise SystemExit("No 'postmanpat' channel found in build_catalog.CHANNELS")


def parse_cutoff():
    if "--cutoff" in sys.argv:
        i = sys.argv.index("--cutoff")
        try:
            c = float(sys.argv[i + 1])
        except (IndexError, ValueError):
            raise SystemExit("--cutoff needs a number between 0 and 1, e.g. --cutoff 0.65")
        if not 0 < c <= 1:
            raise SystemExit("--cutoff must be between 0 and 1")
        return c
    return DEFAULT_CUTOFF


def main():
    if not VIDEOS_IN.exists():
        raise SystemExit(f"{VIDEOS_IN.name} not found — run postman_pat_metadata.py first")

    cutoff = parse_cutoff()
    ch = get_pat_channel()
    min_dur = ch.get("min_duration_seconds", 0)
    max_dur = ch.get("max_duration_seconds")
    cap = ch.get("play_cap_seconds")

    videos = json.loads(VIDEOS_IN.read_text(encoding="utf-8"))
    print(f"Loaded {len(videos)} scraped videos")

    wiki = bc.load_wiki_episodes(ch.get("wiki"))
    wiki.sort(key=lambda w: (w["series"], w["episode"]))
    wiki_index = {}
    for w in wiki:
        wiki_index.setdefault(match_key(w["title"]), w)   # first wins on collision
    wiki_norms = list(wiki_index.keys())
    print(f"Loaded {len(wiki)} Wikipedia episodes")

    # Assign each in-window video to its best Wikipedia episode.
    per_ep = defaultdict(list)          # (series, episode) -> [candidate, ...]
    unmatched = []
    dropped = 0
    for v in videos:
        dur = v.get("duration")
        if dur is None or dur < min_dur or (max_dur and dur > max_dur):
            dropped += 1
            continue
        # Strip emoji BEFORE cleaning so an emoji mid-title doesn't stop the
        # "Postman Pat" segment being recognised as boilerplate.
        name = strip_emoji(bc.clean_episode_title(strip_emoji(v["title"])))
        key = match_key(name)

        w = wiki_index.get(key)
        ratio, mtype = (1.0, "exact") if w else (0.0, "")
        if not w:
            close = difflib.get_close_matches(key, wiki_norms, n=1, cutoff=cutoff)
            if close:
                w = wiki_index[close[0]]
                ratio = difflib.SequenceMatcher(None, key, close[0]).ratio()
                mtype = "fuzzy"

        cand = {
            "cleanTitle": name,
            "durationText": bc.hms(dur),
            "durationSeconds": int(dur),
            "capSeconds": cap if (cap and dur > cap) else "",
            "videoId": v["id"],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "date": v.get("date", ""),
            "ratio": ratio,
            "matchType": mtype,
        }
        if w:
            per_ep[(w["series"], w["episode"])].append(cand)
        else:
            unmatched.append(cand)

    def best_of(cands):
        # exact beats fuzzy; then higher similarity; then longer video (tie-break).
        return sorted(cands, key=lambda c: (
            0 if c["matchType"] == "exact" else 1,
            -c["ratio"],
            -(c["durationSeconds"] or 0),
        ))[0]

    fields = ["series", "episode", "wikiTitle", "videoCount", "matchType",
              "cleanTitle", "durationText", "durationSeconds", "capSeconds",
              "videoId", "url", "date"]

    covered = 0
    with CSV_OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        # SECTION A — the full Wikipedia episode list, in order.
        for ep in wiki:
            cands = per_ep.get((ep["series"], ep["episode"]), [])
            row = {k: "" for k in fields}
            row["series"] = ep["series"]
            row["episode"] = ep["episode"]
            row["wikiTitle"] = ep["title"]
            row["videoCount"] = len(cands)
            if cands:
                covered += 1
                b = best_of(cands)
                for k in ("matchType", "cleanTitle", "durationText",
                          "durationSeconds", "capSeconds", "videoId", "url", "date"):
                    row[k] = b[k]
            w.writerow(row)

        # Collapse duplicate unmatched videos (same normalised title): keep the
        # longest as the representative and note how many copies there were, so
        # the list you review by hand isn't cluttered with repeats.
        uniq = {}
        for c in unmatched:
            dk = bc.norm_title(c["cleanTitle"])
            g = uniq.get(dk)
            if g is None:
                uniq[dk] = dict(c, dupCount=1)
            else:
                g["dupCount"] += 1
                if (c["durationSeconds"] or 0) > (g["durationSeconds"] or 0):
                    uniq[dk] = dict(c, dupCount=g["dupCount"])
        unmatched_unique = sorted(uniq.values(), key=lambda c: c["cleanTitle"].lower())

        # Separator, then SECTION B — videos that matched no episode.
        w.writerow({k: "" for k in fields})
        marker = {k: "" for k in fields}
        marker["wikiTitle"] = "--- UNMATCHED VIDEOS (fill in series/episode to place them) ---"
        w.writerow(marker)
        for c in unmatched_unique:
            row = {k: "" for k in fields}
            row["matchType"] = "unmatched"
            row["videoCount"] = c["dupCount"]   # how many copies collapsed here
            for k in ("cleanTitle", "durationText", "durationSeconds",
                      "capSeconds", "videoId", "url", "date"):
                row[k] = c[k]
            w.writerow(row)

    gaps = len(wiki) - covered
    dup_eps = sum(1 for cands in per_ep.values() if len(cands) > 1)
    print(f"\nfuzzy cutoff {cutoff} (pass --cutoff to change)")
    print(f"{dropped} outside {min_dur}-{max_dur}s window")
    print(f"{len(wiki)} Wikipedia episodes: {covered} covered, {gaps} gaps "
          f"({dup_eps} episodes have duplicate videos)")
    print(f"{len(unmatched)} videos matched no episode "
          f"-> {len(unmatched_unique)} unique after removing duplicates (Section B)")
    print(f"\nWrote {CSV_OUT}")
    print("Scan Section A for gaps (videoCount 0) and spot-check 'fuzzy' rows;")
    print("assign Section B rows by hand if you like, then: python build_postman_pat.py")


if __name__ == "__main__":
    main()
