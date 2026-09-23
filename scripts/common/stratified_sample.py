"""Stratified reservoir sampling across corpus sources with per-source quotas.

Stops scanning a source once its quota is filled — avoids reading 400k+ news rows
when only a few thousand samples are needed.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import re

from common.analysis_paths import SOURCE_FAMILY, analysis_source_paths, source_path_list
from common.evangelization_themes import combined_text, infer_record_language

# Default quotas tuned for ~5k multimodal classroom/analysis samples.
DEFAULT_QUOTAS: Dict[str, int] = {
    "gdelt_news_us": 1200,
    "gdelt_news_americas": 600,
    "gdelt_news_main": 350,
    "gdelt_news_2015_2022": 900,
    "americas_news_2015_2022": 450,
    "americas_news_2024": 80,
    "gdelt_news_2025_26": 120,
    "americas_news_2025_26": 80,
    "gdelt_tv": 450,
    "aapb_en": 350,
    "aapb_es": 350,
    "americas_radio": 450,
    "youtube": 900,
    "americas_youtube": 120,
}

DEFAULT_SCAN_CAPS: Dict[str, int] = {
    "gdelt_news_us": 150_000,
    "gdelt_news_americas": 80_000,
    "gdelt_news_2015_2022": 120_000,
    "gdelt_news_main": 60_000,
    "americas_news_2015_2022": 70_000,
}


_TIME_CODE = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b")
_JUNK_TOKEN = re.compile(r"^\d{1,2}$")
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_JUNK_TERMS = frozenset({
    "https", "http", "www", "com", "org", "net", "html", "php", "amp",
    "facebook", "instagram", "youtube", "twitter", "tiktok", "linkedin",
    "broadcast", "description", "disclaimer", "accurately", "reflect",
    "content", "actual", "aired", "following", "originating", "covering",
    "issues", "national", "international", "washington", "catalog",
    "americanarchive", "spreaker", "goo", "maps", "http", "https www",
    "pbs", "newshour", "news hour", "news day", "journalists", "journalist",
    "report news", "journalists report", "reporters", "reporter", "anchor",
    "nightly", "morning", "edition", "segment", "program", "programme",
    "cnn", "msnbc", "fox", "cspan", "npr", "bbc", "radio hour",
    "said", "report", "day", "news", "news day", "report news", "day news",
})


def normalize_for_topics(text: str) -> str:
    """Strip broadcast timecodes, URLs, and collapse whitespace before TF-IDF/NMF."""
    cleaned = _URL.sub(" ", text or "")
    cleaned = _TIME_CODE.sub(" ", cleaned)
    # Drop common archive / disclaimer boilerplate lines
    parts = []
    for line in cleaned.split("."):
        low = line.lower()
        if "disclaimer" in low and "broadcast" in low:
            continue
        if "americanarchive.org" in low or "following description was created" in low:
            continue
        parts.append(line)
    return " ".join(" ".join(parts).split())


def is_junk_topic_term(term: str) -> bool:
    t = (term or "").strip().lower()
    if not t or _JUNK_TOKEN.match(t):
        return True
    if all(ch.isdigit() or ch in " :" for ch in t):
        return True
    if len(t) < 3:
        return True
    if t in _JUNK_TERMS:
        return True
    if any(w in _JUNK_TERMS for w in t.split()):
        return True
    return False


def iter_records(
    root: Path,
    *,
    sources: Optional[List[str]] = None,
    min_text: int = 80,
) -> Iterator[tuple[str, dict, str]]:
    """Yield (source_key, record, text) across configured paths."""
    paths = analysis_source_paths(root)
    for source_key, path_val in paths.items():
        if sources and source_key not in sources:
            continue
        for path in source_path_list(path_val):
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = combined_text(rec)
                    if len(text.strip()) < min_text:
                        continue
                    yield source_key, rec, text


def stratified_sample(
    root: Path,
    *,
    total: int = 5000,
    quotas: Optional[Dict[str, int]] = None,
    scan_caps: Optional[Dict[str, int]] = None,
    seed: int = 42,
    min_text: int = 80,
    include_text: bool = True,
    text_cap: int = 2500,
) -> list[dict]:
    """Reservoir sample with per-source quotas and optional scan caps."""
    quotas = dict(quotas or DEFAULT_QUOTAS)
    scan_caps = dict(scan_caps or DEFAULT_SCAN_CAPS)
    rng = random.Random(seed)

    pools: Dict[str, list] = {k: [] for k in quotas}
    seen: Dict[str, int] = {k: 0 for k in quotas}
    scanned: Dict[str, int] = {}

    for source_key, rec, text in iter_records(root, min_text=min_text):
        cap = quotas.get(source_key)
        if cap is None:
            continue
        scanned[source_key] = scanned.get(source_key, 0) + 1
        if scanned[source_key] > scan_caps.get(source_key, 10**9):
            if all(len(pools[k]) >= quotas[k] for k in pools):
                break
            continue

        seen[source_key] += 1
        item = {
            "source": source_key,
            "family": SOURCE_FAMILY.get(source_key, "other"),
            "language": infer_record_language(rec, source_hint=source_key),
            "record_id": rec.get("record_id") or rec.get("event_id") or "",
        }
        if include_text:
            item["text"] = text[:text_cap]

        pool = pools[source_key]
        if len(pool) < cap:
            pool.append(item)
        else:
            j = rng.randint(1, seen[source_key])
            if j <= cap:
                pool[j - 1] = item

        if sum(len(v) for v in pools.values()) >= total and all(
            len(pools[k]) >= min(quotas[k], cap) for k, cap in quotas.items()
        ):
            # All quotas filled to at least their target (or all we could get).
            if all(len(pools[k]) >= quotas[k] for k in quotas):
                break

    out: list[dict] = []
    for key in sorted(pools.keys()):
        out.extend(pools[key])
    if len(out) > total:
        rng.shuffle(out)
        out = out[:total]
    return out


def save_sample_cache(path: Path, sample: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in sample:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_sample_cache(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows
