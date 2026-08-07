#!/usr/bin/env python3
"""
build_catalog.py  —  catalog builder + shared library.

Two jobs:
  1. Bootstrap the "videos" channels (Kid Crew, Half-Asleep Chris, David Rule)
     into catalog.json with a full local scrape (exact dates). The nightly job
     (update_nightly.py) then refreshes only their newest few videos.
  2. Act as the shared library that every other script imports: the yt-dlp
     wrappers, date/duration/thumbnail helpers, emoji + title cleaners, the
     Wikipedia loader, and register_manual_stub().

Channels flagged "manual": True are built by their own one-off scripts and are
preserved here, never rebuilt:
  - Numberblocks   -> build_numberblocks.py  (season playlists)
  - Postman Pat    -> postman_pat_metadata.py -> match_postman_pat.py -> build_postman_pat.py
  - Octonauts      -> channel_to_csv.py -> dedupe_octonauts.py -> build_octonauts.py
  - anything else  -> channel_metadata.py -> build_from_csv.py

--------------------------------------------------------------------
SETUP (one time)
--------------------------------------------------------------------
  1. Install Python 3.9+        https://www.python.org/downloads/
  2. Install yt-dlp:            pip install -U yt-dlp
     (Windows: just double-click run_scraper_windows.bat instead.)

--------------------------------------------------------------------
RUN
--------------------------------------------------------------------
      python build_catalog.py
  Output: catalog.json  (next to this script)
"""

import datetime
import difflib
import json
import re
import subprocess
import sys
import shutil
import urllib.request
from pathlib import Path

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
CHANNELS = [
    {
        # Built by its own one-time script, build_numberblocks.py (the eight
        # official season playlists). "manual" keeps a normal build_catalog.py run
        # (and the nightly job) from dropping it.
        "id": "numberblocks",
        "title": "Numberblocks",
        "url": "https://www.youtube.com/@Numberblocks",
        "color": "#e5322d",
        "manual": True,
    },
    {
        "id": "kidcrew",
        "title": "Kid Crew",
        "url": "https://www.youtube.com/@KidCrew",
        "color": "#00a3e0",
        # Scrape the channel's Videos tab instead of playlists, newest first,
        # and keep only videos shorter than max_duration_seconds (drops the long
        # compilations). One collection, in reverse-chronological order.
        "source": "videos",
        "max_duration_seconds": 1800,  # 30 minutes
        "auto_update": True,           # refreshed by the nightly job
        "exact_dates": False,          # this channel won't full-extract; use fast list
    },
    {
        "id": "halfasleepchris",
        "title": "Half-Asleep Chris",
        "url": "https://www.youtube.com/@HalfAsleepChris",
        "color": "#6c5ce7",
        "source": "videos",
        "min_date": "20201210",        # only videos on/after 10 Dec 2020
        "auto_update": True,           # refreshed by the nightly job
    },
    {
        "id": "davidrule",
        "title": "David Rule",
        "url": "https://www.youtube.com/@davidmrule",
        "color": "#e67e22",
        "source": "videos",
        "min_date": "20220601",  # only videos on/after 1 June 2022
        "auto_update": True,     # refreshed by the nightly job
    },
    {
        "id": "postmanpat",
        "title": "Postman Pat",
        "url": "https://www.youtube.com/@PostmanPat",
        "color": "#2e8b57",
        "source": "videos",
        "wiki": "postman_pat",          # match titles to Wikipedia -> Series/Episode
        "min_duration_seconds": 750,    # 12:30
        "max_duration_seconds": 1140,   # ~19:00 (include slightly-long episodes)
        "play_cap_seconds": 900,        # hard-stop playback at 15:00
        "dedupe": True,
        # Built by its own one-time pipeline (postman_pat_metadata.py ->
        # match_postman_pat.py -> build_postman_pat.py) from the full ~1300-video
        # channel, not the 400-latest scrape. "manual" keeps build_catalog.py from
        # overwriting it on a normal run.
        "manual": True,
    },
    {
        "id": "octonauts",
        "title": "Octonauts",
        "url": "https://www.youtube.com/@Octonauts",
        "color": "#1e6fb8",
        "source": "videos",
        "min_duration_seconds": 598,    # 9:58
        "max_duration_seconds": 616,    # 10:16
        "dedupe": True,
        # Built by its own one-time pipeline: channel_to_csv.py (trim by hand) ->
        # dedupe_octonauts.py -> build_octonauts.py. Emoji kept, grouped into
        # "Season N" rows by episode. "manual" keeps a normal run from clobbering it.
        "manual": True,
    },
    # --- one-off manual stubs (auto-added by build_from_csv.py / build_numberblocks.py) ---
]

# NOTE: "source" controls HOW a channel is scraped (currently just the "videos"
# tab). "auto_update" is separate — set it True on any channel you want the nightly
# job to refresh. "manual": True channels are built by their own one-off scripts
# (Numberblocks, Postman Pat, Octonauts) and are preserved, never rebuilt here.

OUTPUT = Path(__file__).with_name("catalog.json")

# Marker line inside CHANNELS (above) where register_manual_stub() inserts stubs.
STUB_MARKER = ("    # --- one-off manual stubs (auto-added by build_from_csv.py "
               "/ build_numberblocks.py) ---\n")

# How many videos to fully-extract per "videos" channel (full extraction = EXACT
# upload dates, but slower). The local bootstrap does the whole back-catalogue;
# the nightly job only refreshes the most recent ones and merges (see update_nightly).
BOOTSTRAP_VIDEO_LIMIT = 400
NIGHTLY_VIDEO_LIMIT = 5      # these channels post rarely; just catch new uploads


def register_manual_stub(channel_id, title, url=None, color="#4a6cf7"):
    """Idempotently add a `manual: True` stub for `channel_id` to CHANNELS in this
    file, so a full build_catalog.py run (and the nightly job) preserve the one-off
    channel that another script spliced into catalog.json. Returns True if it was
    added, False if a stub/entry for that id already existed."""
    src = Path(__file__)
    text = src.read_text(encoding="utf-8")
    if re.search(rf'"id"\s*:\s*"{re.escape(channel_id)}"', text):
        return False
    if STUB_MARKER not in text:
        raise SystemExit(f"register_manual_stub: marker not found in {src.name}")
    lines = ["    {",
             f'        "id": "{channel_id}", "title": {json.dumps(title)},']
    if url:
        lines.append(f'        "url": "{url}",')
    lines.append(f'        "color": "{color}", "manual": True,')
    lines.append("    },")
    stub = "\n".join(lines) + "\n"
    src.write_text(text.replace(STUB_MARKER, stub + STUB_MARKER, 1), encoding="utf-8")
    return True


# ------------------------------------------------------------------
def check_ytdlp():
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       check=True, capture_output=True)
        return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        print("ERROR: yt-dlp is not installed.  Install with:  pip install -U yt-dlp",
              file=sys.stderr)
        sys.exit(1)


def ytdlp_json(base_cmd, url, extra=None, flat=True):
    cmd = base_cmd + ["--dump-single-json", "--no-warnings", "--ignore-errors"]
    if flat:
        cmd.append("--flat-playlist")   # fast list only; no exact dates
    if extra:
        cmd += extra
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not proc.stdout.strip():
        print(f"  ! yt-dlp returned nothing for {url}\n    {proc.stderr[:300]}",
              file=sys.stderr)
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"  ! could not parse yt-dlp output for {url}", file=sys.stderr)
        return None


def ytdlp_video_stream(base_cmd, url, extra=None):
    """Full extraction that STREAMS one JSON per video, printing each as it arrives
    so you can watch progress. Returns a list of entry dicts."""
    cmd = base_cmd + ["--dump-json", "--no-warnings", "--ignore-errors"]
    if extra:
        cmd += extra
    cmd.append(url)
    entries = []
    # stderr is left attached to the terminal so throttling/errors are visible.
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
    for line in proc.stdout:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            v = json.loads(line)
        except json.JSONDecodeError:
            continue
        entries.append(v)
        title = (v.get("title") or "")[:60]
        print(f"      [{len(entries):>3}] {hms(v.get('duration')):>8}  {title}")
    proc.wait()
    return entries


def thumb(vid):
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"


def hms(seconds):
    if not seconds:
        return ""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_date(yyyymmdd):
    """'20250712' -> '12 Jul 2025' (cross-platform)."""
    s = str(yyyymmdd or "")
    if len(s) != 8 or not s.isdigit():
        return ""
    try:
        dt = datetime.datetime.strptime(s, "%Y%m%d")
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except ValueError:
        return ""


def epoch_to_date(ts):
    """Unix timestamp -> '12 Jul 2025'. The fast scrape returns dates this way."""
    try:
        if not ts:
            return ""
        dt = datetime.datetime.utcfromtimestamp(int(ts))
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except (ValueError, TypeError, OSError):
        return ""


def video_date(entry):
    return (fmt_date(entry.get("upload_date"))
            or epoch_to_date(entry.get("timestamp"))
            or epoch_to_date(entry.get("release_timestamp")))


def date_key(entry):
    """A comparable YYYYMMDD int for an entry's upload date, or None if unknown."""
    ud = str(entry.get("upload_date") or "")
    if len(ud) == 8 and ud.isdigit():
        return int(ud)
    for key in ("timestamp", "release_timestamp"):
        ts = entry.get(key)
        if ts:
            try:
                return int(datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y%m%d"))
            except (ValueError, TypeError, OSError):
                pass
    return None


# ------------------------------------------------------------------
# Wikipedia matching + title cleaning (used by "grouped" video channels
# like Postman Pat, whose episodes are grouped into series).
# ------------------------------------------------------------------
WIKI_URLS = {
    "postman_pat":
        "https://en.wikipedia.org/wiki/List_of_Postman_Pat_episodes?action=raw",
}


def norm_title(s):
    """Normalise a title for fuzzy matching."""
    s = (s or "").lower().replace("’", "'").replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def _clean_wiki_title(t):
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    return t.replace("''", "").strip().strip('"').strip()


def load_wiki_episodes(which):
    """Fetch a Wikipedia episode list and return [{series, episode, title}]."""
    url = WIKI_URLS.get(which)
    if not url:
        return []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kids-tv-catalog"})
        text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not fetch Wikipedia ({e})", file=sys.stderr)
        return []
    eps = []
    parts = re.split(r"===+\s*Series\s+(\d+)[^=]*===+", text)
    for i in range(1, len(parts), 2):
        series = int(parts[i])
        body = parts[i + 1]
        for m in re.finditer(r"\|\s*EpisodeNumber2\s*=\s*(\d+).*?\|\s*Title\s*=\s*([^\n|]+)",
                             body, re.S):
            title = _clean_wiki_title(m.group(2))
            if title:
                eps.append({"series": series, "episode": int(m.group(1)), "title": title})
    return eps


# YouTube titles are like: "Postman Pat | Postman Pat on The Road | Full Episodes |
# Cartoons for Kids". We want just the episode name.
_TITLE_BOILERPLATE = ("full episode", "episode", "cartoon", "kids", "official",
                      "compilation", "videos", "special delivery service",
                      "for children", "series")


def clean_episode_title(raw):
    segs = [s.strip() for s in raw.split("|") if s.strip()]
    if not segs:
        return raw.strip()

    def is_boiler(s):
        low = s.lower().strip()
        if low in ("postman pat", "postman pat!"):
            return True
        return any(b in low for b in _TITLE_BOILERPLATE)

    kept = [s for s in segs if not is_boiler(s)]
    return kept[0] if kept else max(segs, key=len)


# Emoji / pictograph ranges (keeps normal punctuation). Used to strip emoji from
# titles, or to build emoji-insensitive keys for de-duplication.
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


# Octonauts titles look like:
#   "🦁 The Lion's mane Jellyfish 🪼 | Season 3 | Full Episodes | Cartoons for Kids"
# Keep the episode NAME exactly (first "|" segment, emoji and all) and read the
# season and episode numbers out of the title. Returns (name, season, episode);
# season/episode are None when not present. Unlike Postman Pat, emoji are kept.
def clean_octonauts_title(raw):
    text = raw or ""
    season = episode = None
    m = re.search(r"\bs(\d+)\s*e\s*(\d+)\b", text, re.I)       # S3 E5 / S3E5 -> both
    if m:
        season, episode = int(m.group(1)), int(m.group(2))
    if season is None:
        m = re.search(r"season\s+(\d+)", text, re.I)           # Season 3
        if m:
            season = int(m.group(1))
    if episode is None:
        m = (re.search(r"\bepisode\s*(\d+)\b", text, re.I)     # Episode 5
             or re.search(r"\bep\.?\s*(\d+)\b", text, re.I))   # Ep 5 / Ep. 5
        if m:
            episode = int(m.group(1))
    name = text.split("|")[0]
    # Drop a leading channel-name prefix: "Octonauts - " or "@Octonauts - " etc.
    name = re.sub(r"^\s*@?octonauts\b\s*[-–—:]+\s*", "", name, flags=re.I)
    return name.strip(), season, episode


def build_grouped_videos_channel(base_cmd, ch, limit):
    """Videos-tab channel whose episodes are matched to a Wikipedia list and grouped
    into Series. Cleans titles, de-dupes, applies a duration window, and (for the
    slightly-too-long items) records a playback cap."""
    url = ch["url"].rstrip("/") + "/videos"
    min_dur = ch.get("min_duration_seconds", 0)
    max_dur = ch.get("max_duration_seconds")
    cap = ch.get("play_cap_seconds")
    print(f"  scraping newest {limit} videos, grouping into series "
          f"(keep {min_dur}-{max_dur}s, cap {cap}s)…")

    data = ytdlp_json(base_cmd, url, extra=[
        "--playlist-end", str(limit),
        "--extractor-args", "youtubetab:approximate_date",
    ])
    entries = (data or {}).get("entries") or []

    wiki = load_wiki_episodes(ch.get("wiki"))
    wiki_index = {norm_title(w["title"]): w for w in wiki}
    wiki_norms = list(wiki_index.keys())
    print(f"      {len(wiki)} Wikipedia episodes loaded")

    seen = set()
    matched = {}            # (series, episode) -> ep
    others = []
    kept = dropped = 0
    for v in entries:
        if not v or not v.get("id") or not v.get("title"):
            continue
        dur = v.get("duration")
        if dur is None or dur < min_dur or (max_dur and dur > max_dur):
            dropped += 1
            continue
        name = clean_episode_title(v["title"])
        key = norm_title(name)
        if ch.get("dedupe") and key in seen:
            continue
        seen.add(key)
        kept += 1
        ep = {
            "name": name,
            "videoId": v["id"],
            "thumbnail": thumb(v["id"]),
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "duration": int(dur),
            "durationText": hms(dur),
            "subtitle": video_date(v),
        }
        if cap and dur > cap:
            ep["capSeconds"] = cap
        w = wiki_index.get(key)
        if not w:
            close = difflib.get_close_matches(key, wiki_norms, n=1, cutoff=0.86)
            if close:
                w = wiki_index[close[0]]
        if w:
            ep["season"] = w["series"]
            ep["episode"] = w["episode"]
            ep["episode_index"] = w["episode"]
            ep["subtitle"] = f"Episode {w['episode']}"
            matched.setdefault((w["series"], w["episode"]), ep)  # de-dupe by S/E
        else:
            others.append(ep)

    collections = []
    for s in sorted({se[0] for se in matched}):
        eps = sorted((e for k, e in matched.items() if k[0] == s),
                     key=lambda x: x["episode"])
        collections.append({"id": f"series-{s}", "title": f"Series {s}", "episodes": eps})
    if others:
        collections.append({"id": "other", "title": "Other", "episodes": others})

    print(f"      {kept} kept, {dropped} outside window, "
          f"{sum(len(c['episodes']) for c in collections if c['id'] != 'other')} matched "
          f"to a series, {len(others)} unmatched")
    return {
        "id": ch["id"],
        "title": ch["title"],
        "youtubeChannelId": ch.get("youtubeChannelId"),
        "color": ch.get("color", "#4a6cf7"),
        "collections": collections,   # no "grid" layout -> rows per series
    }


def collect_videos(base_cmd, ch, limit):
    """Videos-tab mode: newest-first, up to `limit` videos, filtered by
    max_duration_seconds / min_date.

    Primary path is a full extraction (EXACT upload dates). Some channels (e.g. a
    "made for kids" channel) won't full-extract through yt-dlp even though the videos
    play fine elsewhere; if that comes back empty we fall back to the fast list
    (approximate dates) so the channel is never empty."""
    url = ch["url"].rstrip("/") + "/videos"
    max_dur = ch.get("max_duration_seconds")   # None -> no duration limit
    min_date = ch.get("min_date")              # "YYYYMMDD" -> only newer videos
    min_date_int = int(min_date) if min_date else None
    conds = []
    if max_dur:
        conds.append(f"< {max_dur // 60} min")
    if min_date_int:
        conds.append(f"on/after {min_date}")
    print(f"  scraping newest {limit} videos "
          f"(keeping {', '.join(conds) if conds else 'all'})…")

    def build(entries):
        over = before = 0
        out = []
        for v in entries:
            if not v or not v.get("id") or not v.get("title"):
                continue
            dur = v.get("duration")
            if max_dur and dur and dur > max_dur:
                over += 1
                continue
            if min_date_int:
                dk = date_key(v)
                if dk is None or dk < min_date_int:
                    before += 1
                    continue
            out.append({
                "name": v["title"],
                "videoId": v["id"],
                "thumbnail": thumb(v["id"]),
                "url": f"https://www.youtube.com/watch?v={v['id']}",
                "duration": int(dur) if dur else None,
                "durationText": hms(dur),
                "subtitle": video_date(v),   # exact if full extraction, else approximate
            })
        return out, over, before

    # Primary: full extraction (streamed, exact dates) — unless the channel opts out
    # (exact_dates: False) because it can't be full-extracted.
    eps, over, before = [], 0, 0
    if ch.get("exact_dates", True):
        eps, over, before = build(ytdlp_video_stream(
            base_cmd, url, extra=["--playlist-end", str(limit)]))

    # Fast list (approximate dates): used directly when exact_dates is False, or as a
    # fallback if the full extraction came back empty, so the channel is never empty.
    if not eps:
        if ch.get("exact_dates", True):
            print("      full extraction returned nothing — falling back to the fast list")
        else:
            print("      using the fast list (approximate dates)")
        data = ytdlp_json(base_cmd, url, extra=[
            "--playlist-end", str(limit),
            "--extractor-args", "youtubetab:approximate_date",
        ])
        eps, over, before = build((data or {}).get("entries") or [])

    print(f"      {over} over-length · {before} before cutoff · {len(eps)} kept")
    # Videos tab is already newest-first (reverse chronological).
    return {
        "id": "latest",
        "title": ch["title"],
        "color": ch.get("color"),
        "episodes": eps,
    }


def build_channel(base_cmd, ch, videos_limit=BOOTSTRAP_VIDEO_LIMIT):
    print(f"\n== {ch['title']} ==")

    if ch.get("source") == "videos" and ch.get("wiki"):
        return build_grouped_videos_channel(base_cmd, ch, videos_limit)

    if ch.get("source") == "videos":
        collection = collect_videos(base_cmd, ch, videos_limit)
        collections = [collection] if collection["episodes"] else []
        total = len(collection["episodes"])
        print(f"  => 1 collection, {total} videos")
        return {
            "id": ch["id"],
            "title": ch["title"],
            "youtubeChannelId": ch.get("youtubeChannelId"),
            "color": ch.get("color", "#4a6cf7"),
            "layout": "grid",  # wrapping grid of wider cards with dates
            "collections": collections,
        }

    raise SystemExit(f"build_channel: channel '{ch.get('id')}' has no supported "
                     f"source (expected 'videos'; playlist channels like Numberblocks "
                     f"are built by build_numberblocks.py)")


def main():
    base_cmd = check_ytdlp()
    # Preserve any manually-built channels (e.g. Postman Pat) already in catalog.json
    # so a normal run doesn't clobber them.
    existing = {}
    if OUTPUT.exists():
        try:
            for c in json.loads(OUTPUT.read_text(encoding="utf-8")).get("channels", []):
                if c.get("id"):
                    existing[c["id"]] = c
        except (json.JSONDecodeError, OSError):
            pass

    catalog = {"generatedWith": "build_catalog.py", "channels": []}
    for ch in CHANNELS:
        if ch.get("manual"):
            kept = existing.get(ch["id"])
            if kept:
                print(f"\n== {ch['title']} == (manual — keeping existing catalog entry)")
                catalog["channels"].append(kept)
            else:
                print(f"\n== {ch['title']} == (manual — not built yet, skipping; "
                      f"run its own pipeline)")
            continue
        catalog["channels"].append(build_channel(base_cmd, ch))
    OUTPUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(f"\nWrote {OUTPUT}")
    print("Open preview.html and click 'Load catalog.json' to verify the real data.")


if __name__ == "__main__":
    main()
