"""Paths for analysis scripts — includes fetch shards before merge."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterator, List

from tqdm import tqdm

from common.progress import iter_jsonl_records


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _event_shards(base: Path, stem: str) -> List[Path]:
    """Day-partitioned event JSONL (excludes ``*_articles.jsonl`` sidecars)."""
    return [
        p
        for p in sorted(base.glob(f"{stem}_shard*of04.jsonl"))
        if "_articles" not in p.name
    ]


def gdelt_fetch_shard_jsonls(base: Path, stem: str) -> List[Path]:
    """Paragraph rows written by --fetch-only (not the unique-event merge)."""
    return _event_shards(base, stem)


def americas_fetch_shard_jsonls(root: Path | None = None) -> List[Path]:
    """Americas fetch shards whose paragraph_text is missing from the unique-event JSONL."""
    root = root or project_root()
    base = root / "data/americas/news"
    out: List[Path] = []
    for stem in (
        "gdelt_americas_geolocated_2015_2022",
        "gdelt_americas_geolocated_20240609_to_20241231",
        "gdelt_americas_geolocated_20250101_to_20260630",
    ):
        out.extend(gdelt_fetch_shard_jsonls(base, stem))
    return out


def gdelt_period_jsonls(base: Path, stem: str, *, include_shards: bool = True) -> List[Path]:
    """Unique-event JSONL for one GDELT period.

    Preference order:
      1. ``{stem}_fetched.jsonl`` — post-fetch unique merge (U.S. 2015–22 paragraphs)
      2. Americas unique-event merge ``{stem}.jsonl`` (shards overlap across keyword expansions)
      3. Day shards (U.S. live collection before a fetched merge exists)
      4. Stale/partial ``{stem}.jsonl``
    """
    fetched = base / f"{stem}_fetched.jsonl"
    if fetched.exists():
        return [fetched]
    main = base / f"{stem}.jsonl"
    shards = _event_shards(base, stem) if include_shards else []
    is_americas = "americas" in stem or "americas" in str(base)
    if is_americas and main.exists():
        return [main]
    if shards:
        return shards
    return [main] if main.exists() else []


def gdelt_2015_22_jsonls(root: Path | None = None, *, include_shards: bool = True) -> List[Path]:
    """U.S. 2015–22 unique-event JSONL (fetched merge, else shards)."""
    base = (root or project_root()) / "data/us/news"
    return gdelt_period_jsonls(base, "gdelt_us_geolocated_2015_2022", include_shards=include_shards)


from common.gdelt_paths import americas_corpus_path, us_corpus_path  # noqa: E402


# Modality family for every key in analysis_source_paths().
SOURCE_FAMILY: Dict[str, str] = {
    "gdelt_news_us": "news",
    "gdelt_news_americas": "news",
    "gdelt_news_main": "news",
    "gdelt_news_2015_2022": "news",
    "americas_news_2015_2022": "news",
    "americas_news_2024": "news",
    "gdelt_news_2025_26": "news",
    "americas_news_2025_26": "news",
    "gdelt_tv": "tv",
    "aapb_en": "radio",
    "aapb_es": "radio",
    "americas_radio": "radio",
    "youtube": "youtube",
    "americas_youtube": "youtube",
}


def _split_us_news_paths(root: Path) -> Dict[str, Path | List[Path]]:
    us = root / "data/us"
    return {
        "gdelt_news_main": us / "news/gdelt_us_geolocated_2015-01-01_to_2025-12-31.jsonl",
        "gdelt_news_2015_2022": gdelt_2015_22_jsonls(root),
        "gdelt_news_2025_26": gdelt_period_jsonls(
            us / "news", "gdelt_us_geolocated_20250101_to_20260630"
        ),
    }


def _split_americas_news_paths(root: Path) -> Dict[str, Path | List[Path]]:
    am = root / "data/americas"
    am_fetched = am / "news/gdelt_americas_fetched.jsonl"
    am_merged = [am_fetched] if am_fetched.exists() else None
    return {
        "americas_news_2015_2022": am_merged if am_merged else gdelt_period_jsonls(
            am / "news", "gdelt_americas_geolocated_2015_2022"
        ),
        "americas_news_2024": [] if am_merged else gdelt_period_jsonls(
            am / "news", "gdelt_americas_geolocated_20240609_to_20241231"
        ),
        "americas_news_2025_26": gdelt_period_jsonls(
            am / "news", "gdelt_americas_geolocated_20250101_to_20260630"
        ),
    }


def _anon_glob(base: Path) -> List[Path]:
    return sorted(base.glob("anonymized/anonymized_part_*.jsonl"))


def analysis_source_paths(root: Path | None = None) -> Dict[str, Path | List[Path]]:
    """Corpus paths for RQ / viz — prefer anonymized shards (research repo)."""
    root = root or project_root()
    us = root / "data/us"
    am = root / "data/americas"

    us_news_anon = _anon_glob(us / "news")
    am_news_anon = _anon_glob(am / "news")
    us_corpus = us_corpus_path(root)
    am_corpus = americas_corpus_path(root)

    if us_news_anon or am_news_anon:
        news = {
            "gdelt_news_us": us_news_anon,
            "gdelt_news_americas": am_news_anon,
            "gdelt_news_main": [],
            "gdelt_news_2015_2022": [],
            "americas_news_2015_2022": [],
            "americas_news_2024": [],
            "gdelt_news_2025_26": [],
            "americas_news_2025_26": [],
        }
    elif us_corpus and am_corpus:
        news = {
            "gdelt_news_us": us_corpus,
            "gdelt_news_americas": am_corpus,
            "gdelt_news_main": [],
            "gdelt_news_2015_2022": [],
            "americas_news_2015_2022": [],
            "americas_news_2024": [],
            "gdelt_news_2025_26": [],
            "americas_news_2025_26": [],
        }
    else:
        news = {**_split_us_news_paths(root), **_split_americas_news_paths(root)}
        news.setdefault("gdelt_news_us", [])
        news.setdefault("gdelt_news_americas", [])

    def prefer_anon(anon_dir: Path, raw: Path) -> Path | List[Path]:
        parts = _anon_glob(anon_dir.parent if anon_dir.name == "anonymized" else anon_dir)
        # anon_dir is .../tv or .../youtube parent; pass the modality folder
        return parts if parts else raw

    tv_anon = _anon_glob(us / "tv")
    aapb_en_anon = _anon_glob(us / "english/radio")
    aapb_es_anon = _anon_glob(us / "spanish/radio")
    am_radio_anon = _anon_glob(am / "radio")
    yt_anon = _anon_glob(us / "youtube")
    am_yt_anon = _anon_glob(am / "youtube")

    return {
        **news,
        "gdelt_tv": tv_anon or (us / "tv/gdelt_tv_us_2015-01-01_to_2025-12-31.jsonl"),
        "aapb_en": aapb_en_anon or (us / "english/radio/aapb_us_2015-01-01_to_2025-12-31.jsonl"),
        "aapb_es": aapb_es_anon or (us / "spanish/radio/aapb_us_2015-01-01_to_2025-12-31.jsonl"),
        "americas_radio": am_radio_anon or (am / "radio/archive_radio_americas_2015_2025.jsonl"),
        "youtube": yt_anon or (us / "youtube/youtube_us_2015-01-01_to_2025-12-31.jsonl"),
        "americas_youtube": am_yt_anon or (am / "youtube/youtube_americas_2015-01-01_to_2025-12-31.jsonl"),
    }


def source_path_list(value: Path | List[Path]) -> List[Path]:
    if isinstance(value, list):
        return [p for p in value if p.exists()]
    return [value] if value.exists() else []


def count_source(value: Path | List[Path], *, desc: str) -> tuple[int, int, dict]:
    """Return (rows, paragraphs, year_counts) across one or more JSONL files."""
    from collections import Counter

    rows = paras = 0
    years: Counter = Counter()
    for path in source_path_list(value):
        for o in iter_jsonl_records(path, desc=f"{desc} {path.name}"):
            rows += 1
            if o.get("paragraph_text"):
                paras += 1
            d = str(
                o.get("gdelt_day")
                or o.get("date")
                or o.get("published_at")
                or o.get("air_date")
                or ""
            )
            y = d[:4] if len(d) >= 4 and d[:4].isdigit() else None
            if y:
                years[y] += 1
    return rows, paras, dict(sorted(years.items()))


def iter_source(
    value: Path | List[Path],
    *,
    desc: str,
) -> Iterator[dict]:
    """Iterate records across one or more JSONL files with a single progress bar."""
    paths = source_path_list(value)
    if not paths:
        return
    import sys

    use_bar = sys.stderr.isatty() or os.environ.get("FORCE_TQDM") == "1"
    bar = tqdm(
        desc=desc,
        unit="row",
        dynamic_ncols=True,
        file=sys.stderr,
        mininterval=2.0,
        disable=not use_bar and os.environ.get("TQDM_DISABLE") == "1",
    )
    try:
        for path in paths:
            bar.set_postfix(file=path.name, refresh=False)
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    bar.update(1)
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
    finally:
        bar.close()