#!/usr/bin/env python3
"""Export the classroom lexicon as CSV (theme patterns + papal documents + collection keywords)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
VIZ = TOOLS.parent
ROOT = VIZ.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from common.cst_papal_documents import (  # noqa: E402
    CST_PAPAL_DOCUMENTS,
    cst_keywords_en,
    cst_keywords_es,
    cst_keywords_pt,
)
from common.evangelization_themes import (  # noqa: E402
    EVANGELIZATION_KEYWORDS_EN,
    EVANGELIZATION_KEYWORDS_ES,
    EVANGELIZATION_KEYWORDS_PT,
    PAPAL_DOCUMENT_LABELS,
    THEME_GROUP_LABELS,
    THEME_PATTERNS,
)

FIELDS = [
    "kind",
    "theme_id",
    "label",
    "language",
    "group",
    "group_label",
    "pattern_or_phrase",
    "is_papal_document",
    "pontiff",
    "year",
    "document_kind",
]


def _expand_lang(scope: str) -> list[str]:
    s = (scope or "both").lower()
    if s == "both":
        return ["english", "spanish", "portuguese"]
    if s in ("english", "spanish", "portuguese"):
        return [s]
    return [s]


def rows_theme_patterns() -> list[dict]:
    out: list[dict] = []
    for tp in THEME_PATTERNS:
        for lang in _expand_lang(tp.language):
            out.append(
                {
                    "kind": "scoring_pattern",
                    "theme_id": tp.label,
                    "label": tp.label.replace("_", " "),
                    "language": lang,
                    "group": tp.group,
                    "group_label": THEME_GROUP_LABELS.get(tp.group, tp.group),
                    "pattern_or_phrase": tp.pattern.pattern,
                    "is_papal_document": "yes" if tp.label in PAPAL_DOCUMENT_LABELS else "no",
                    "pontiff": "",
                    "year": "",
                    "document_kind": "",
                }
            )
    return out


def rows_papal_catalog() -> list[dict]:
    """Magisterial document catalog (titles used in collection + scoring)."""
    out: list[dict] = []
    for title, kind, pontiff, year in CST_PAPAL_DOCUMENTS:
        theme_id = title.lower().replace(" ", "_").replace("'", "")
        # Prefer matching THEME_PATTERNS id when present
        for tp in THEME_PATTERNS:
            if title.lower().replace(" ", "_") in tp.label or tp.label.replace("_", " ") in title.lower():
                theme_id = tp.label
                break
        # Known renames
        aliases = {
            "Laudato Si": "laudato_si",
            "Fratelli Tutti": "fratelli_tutti",
            "Evangelii Gaudium": "evangelii_gaudium",
            "Evangelii Nuntiandi": "evangelii_nuntiandi",
            "Redemptoris Missio": "redemptoris_missio",
            "Magnifica Humanitas": "magnifica_humanitas",
            "Laudate Deum": "laudate_deum",
            "Dilexit Nos": "dilexit_nos",
            "Querida Amazonia": "querida_amazonia",
        }
        theme_id = aliases.get(title, theme_id)
        for lang in ("english", "spanish", "portuguese"):
            out.append(
                {
                    "kind": "papal_document",
                    "theme_id": theme_id,
                    "label": title,
                    "language": lang,
                    "group": "theology",
                    "group_label": THEME_GROUP_LABELS.get("theology", "theology"),
                    "pattern_or_phrase": title,
                    "is_papal_document": "yes",
                    "pontiff": pontiff,
                    "year": str(year),
                    "document_kind": kind,
                }
            )
    return out


def rows_collection_keywords() -> list[dict]:
    bags = (
        ("english", EVANGELIZATION_KEYWORDS_EN + cst_keywords_en()),
        ("spanish", EVANGELIZATION_KEYWORDS_ES + cst_keywords_es()),
        ("portuguese", EVANGELIZATION_KEYWORDS_PT + cst_keywords_pt()),
    )
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for lang, phrases in bags:
        for phrase in phrases:
            key = (lang, phrase.casefold())
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "kind": "collection_keyword",
                    "theme_id": "",
                    "label": phrase,
                    "language": lang,
                    "group": "collection",
                    "group_label": "Harvest / collection gate",
                    "pattern_or_phrase": phrase,
                    "is_papal_document": "no",
                    "pontiff": "",
                    "year": "",
                    "document_kind": "",
                }
            )
    return out


def write_csv(path: Path) -> int:
    rows = rows_theme_patterns() + rows_papal_catalog() + rows_collection_keywords()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=VIZ / "data" / "lexicon.csv",
        help="Output CSV path (default: viz/data/lexicon.csv)",
    )
    args = p.parse_args()
    n = write_csv(args.output)
    print(f"Wrote {n} rows → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
