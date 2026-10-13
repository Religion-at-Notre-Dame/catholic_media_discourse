#!/usr/bin/env python3
"""Export Assignment-5 classroom CSV (friendly columns, no raw JSONL needed).

  python3 scripts/judge/export_a5_classroom_csv.py
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = (
    ROOT
    / "papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl"
)
DEFAULT_OUT = ROOT / "papers/rise_education_2026/teaching/a5_fixture_sample.csv"

FIELDS = (
    "id",
    "language",
    "text_preview",
    "content_labels",
    "discourse_labels",
    "accuracy_score",
    "needs_human_review",
    "your_content",
    "your_discourse",
    "your_accuracy",
    "parish_response_notes",
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN)
    p.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()

    rows: list[dict] = []
    with args.inp.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("error"):
                continue
            rows.append(
                {
                    "id": rec.get("id") or "",
                    "language": rec.get("language") or "",
                    "text_preview": (rec.get("text_preview") or "")[:320],
                    "content_labels": "|".join(rec.get("content_labels") or []),
                    "discourse_labels": "|".join(rec.get("discourse_labels") or []),
                    "accuracy_score": rec.get("accuracy_score"),
                    "needs_human_review": rec.get("needs_human_review"),
                    "your_content": "",
                    "your_discourse": "",
                    "your_accuracy": "",
                    "parish_response_notes": "",
                }
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
