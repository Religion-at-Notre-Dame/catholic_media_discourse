#!/usr/bin/env python3
"""Export classroom viz extras: country theme breakdown, compare pairs, exemplars.

  python3 viz/export_viz_extras.py
  python3 viz/export_viz_extras.py --use-cache --jobs 4

Writes viz/extras.js (loaded by index.html alongside data.js).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
VIZ = Path(__file__).resolve().parent
OUT = VIZ / "extras.js"
CACHE_DIR = VIZ / ".cache"
for p in (SCRIPTS, VIZ):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from common.evangelization_themes import (  # noqa: E402
    THEME_PATTERNS,
    combined_text,
    infer_record_language,
    match_theme_labels,
)
from common.gdelt_paths import paragraph_scan_paths  # noqa: E402
from common.geography import fips_country_name, record_action_fips  # noqa: E402
from common.progress import section, write  # noqa: E402
from viz_fast import cache_path, inventory_fingerprint, load_cache, loads_line, save_cache  # noqa: E402

COMPARE_PAIRS = (
    ("US", "MX"),
    ("US", "CI"),
    ("US", "BR"),
    ("MX", "ES"),
)
THEME_DISPLAY = (
    "mission",
    "gospel",
    "evangelio",
    "immigration",
    "guadalupe",
    "laudato_si",
    "liberation_theology",
    "eucharist",
)
EXEMPLAR_CAP = 3
TEXT_SNIP = 220
PER_PATH_CAP = int(os.environ.get("VIZ_MAX_NEWS_ROWS", "0") or "0") or 80_000


def path_source_hint(path: Path) -> str:
    name = path.name
    if "gdelt_us_paragraphs" in name or "gdelt_us" in name:
        return "gdelt_news_us"
    if "gdelt_americas_paragraphs" in name or "americas" in name:
        return "gdelt_news_americas"
    return "gdelt_news"


def country_fips(record: dict, source_hint: str = "") -> str | None:
    fips = record_action_fips(record, source_hint=source_hint)
    return fips or None


def redact_snip(text: str) -> str:
    t = " ".join(text.split())
    if len(t) > TEXT_SNIP:
        t = t[:TEXT_SNIP] + "…"
    return t


def match_themes_trilingual(text: str) -> set[str]:
    hits: set[str] = set()
    for lang in ("english", "spanish", "portuguese"):
        hits |= match_theme_labels(text, lang, THEME_PATTERNS)
    return hits


def scan_path_themes(path: Path, *, cap: int, rng: random.Random) -> dict:
    hint = path_source_hint(path)
    by_country: dict[str, Counter] = defaultdict(Counter)
    country_n: Counter = Counter()
    exemplars: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    scanned = 0

    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scanned += 1
            if cap and scanned > cap:
                break
            try:
                rec = loads_line(line)
            except Exception:
                continue
            text = combined_text(rec)
            if len(text.strip()) < 50:
                continue
            fips = country_fips(rec, source_hint=hint)
            if not fips:
                continue
            lang = infer_record_language(rec, source_hint=hint)
            themes = match_themes_trilingual(text)
            if not themes:
                continue
            country_n[fips] += 1
            for t in themes:
                if t in THEME_DISPLAY:
                    by_country[fips][t] += 1
                    bucket = exemplars[fips][t]
                    snip = redact_snip(text)
                    if len(bucket) < EXEMPLAR_CAP:
                        bucket.append({"text": snip, "source": hint})
                    elif rng.random() < EXEMPLAR_CAP / max(country_n[fips], 1):
                        bucket[rng.randint(0, EXEMPLAR_CAP - 1)] = {"text": snip, "source": hint}

    return {
        "country_n": list(country_n.items()),
        "by_country": {f: list(c.items()) for f, c in by_country.items()},
        "exemplars": {
            f: {t: list(v) for t, v in themes.items()}
            for f, themes in exemplars.items()
        },
        "scanned": scanned,
    }


def merge_scans(partials: list[dict], *, rng: random.Random) -> tuple[Counter, dict[str, Counter], dict]:
    country_n: Counter = Counter()
    by_country: dict[str, Counter] = defaultdict(Counter)
    exemplars: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for part in partials:
        for fips, n in part.get("country_n", []):
            country_n[fips] += n
        for fips, items in part.get("by_country", {}).items():
            for theme, n in items:
                by_country[fips][theme] += n
        for fips, themes in part.get("exemplars", {}).items():
            for theme, rows in themes.items():
                bucket = exemplars[fips][theme]
                for row in rows:
                    if len(bucket) < EXEMPLAR_CAP:
                        bucket.append(row)
                    else:
                        j = rng.randint(0, len(bucket))
                        if j < EXEMPLAR_CAP:
                            bucket[j] = row

    return country_n, by_country, exemplars


def build_countries(country_n: Counter, by_country: dict[str, Counter], exemplars: dict) -> list[dict]:
    countries = []
    for fips, n in country_n.most_common(40):
        if n < 20:
            continue
        rates = {t: round(1000.0 * by_country[fips][t] / n, 2) for t in THEME_DISPLAY}
        countries.append(
            {
                "fips": fips,
                "name": fips_country_name(fips) or fips,
                "n": n,
                "themes_per_1k": rates,
                "exemplars": {t: exemplars[fips].get(t, []) for t in THEME_DISPLAY if exemplars[fips].get(t)},
            }
        )
    return countries


def harvest_country_themes(*, use_cache: bool = False, cap: int = PER_PATH_CAP) -> dict:
    paths = paragraph_scan_paths(ROOT)
    fp = inventory_fingerprint(paths)
    cache_file = cache_path(CACHE_DIR, "country_themes", fp)
    if use_cache:
        cached = load_cache(cache_file)
        if cached and cached.get("countries"):
            write(f"Country themes cache hit ({cache_file.name})")
            return cached

    rng = random.Random(42)
    partials = []
    for path in paths:
        if not path.exists():
            continue
        write(f"Country themes {path.name}")
        partials.append(scan_path_themes(path, cap=cap, rng=rng))

    country_n, by_country, exemplars = merge_scans(partials, rng=rng)
    countries = build_countries(country_n, by_country, exemplars)
    payload = {"countries": countries}
    if use_cache:
        save_cache(cache_file, payload)
        write(f"Cached country themes → {cache_file.name}")
    return payload


def compare_payload(countries: list[dict]) -> dict:
    by_fips = {c["fips"]: c for c in countries}
    pairs = []
    for a, b in COMPARE_PAIRS:
        ca, cb = by_fips.get(a), by_fips.get(b)
        if not ca or not cb:
            continue
        delta = {}
        for t in THEME_DISPLAY:
            ra = ca["themes_per_1k"].get(t, 0)
            rb = cb["themes_per_1k"].get(t, 0)
            delta[t] = round(ra - rb, 2)
        pairs.append(
            {
                "a": {"fips": a, "name": ca["name"], "n": ca["n"]},
                "b": {"fips": b, "name": cb["name"], "n": cb["n"]},
                "delta_per_1k": delta,
            }
        )
    return {"pairs": pairs}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export viz extras (compare + exemplars).")
    parser.add_argument("--use-cache", action="store_true", help="Reuse viz/.cache/ when JSONL mtimes unchanged.")
    args = parser.parse_args()

    section("Export viz extras")
    ct = harvest_country_themes(use_cache=args.use_cache)
    payload = {
        "countryThemes": ct["countries"],
        "compare": compare_payload(ct["countries"]),
        "themeLabels": {t: t.replace("_", " ") for t in THEME_DISPLAY},
        "note": "Exemplars are anonymized snippets for classroom use; rates are lexicon hits per 1k.",
    }
    OUT.write_text("window.VIZ_EXTRAS = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
    n_pairs = len(payload["compare"]["pairs"])
    write(f"Wrote {OUT.name} ({len(ct['countries'])} countries, {n_pairs} compare pairs)", style="bold green")


if __name__ == "__main__":
    main()
