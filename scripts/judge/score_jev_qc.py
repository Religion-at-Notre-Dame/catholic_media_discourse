#!/usr/bin/env python3
"""Aggregate Sidney/Theology marks from a filled QC sheet CSV.

  python3 scripts/judge/score_jev_qc.py \\
    papers/rise_education_2026/analysis/jev_judgments/qc_sheet.csv

Expected mark values (case-insensitive):
  agree | missing_label | extra_label | discourse_off | accuracy_off | needs_theology
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

KNOWN = {
    "agree",
    "missing_label",
    "extra_label",
    "discourse_off",
    "accuracy_off",
    "needs_theology",
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv_path", type=Path)
    p.add_argument("--write-json", type=Path, default=None)
    args = p.parse_args()

    if not args.csv_path.exists():
        raise SystemExit(f"missing {args.csv_path}")

    rows = list(csv.DictReader(args.csv_path.open(encoding="utf-8")))
    marks = Counter()
    filled = 0
    blank = 0
    unknown = Counter()
    by_lang: dict[str, Counter] = {}

    for r in rows:
        raw = (r.get("mark") or "").strip().lower()
        lang = (r.get("language") or "?").lower()
        by_lang.setdefault(lang, Counter())
        if not raw:
            blank += 1
            continue
        filled += 1
        key = raw.replace(" ", "_")
        if key not in KNOWN:
            unknown[raw] += 1
            marks["other"] += 1
            by_lang[lang]["other"] += 1
        else:
            marks[key] += 1
            by_lang[lang][key] += 1

    agree = marks.get("agree", 0)
    agree_rate = (agree / filled) if filled else None
    out = {
        "rows": len(rows),
        "marked": filled,
        "blank": blank,
        "agree_rate": agree_rate,
        "marks": dict(marks.most_common()),
        "unknown_marks": dict(unknown.most_common()),
        "by_language": {k: dict(v) for k, v in sorted(by_lang.items())},
        "education_note": (
            "agree_rate is among marked rows only; blank rows are still in the QC queue."
        ),
    }

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.write_json}")

    print(
        f"rows={len(rows)} marked={filled} blank={blank} "
        f"agree_rate={agree_rate if agree_rate is not None else 'n/a'}"
    )
    print("marks:", dict(marks.most_common()))
    if unknown:
        print("unknown marks:", dict(unknown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
