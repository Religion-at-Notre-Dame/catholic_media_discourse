#!/usr/bin/env python3
"""Export a Sidney/Theology QC worksheet from Jev JSONL (fixture or live).

  python3 scripts/judge/export_jev_qc_sheet.py \\
    papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl

Marks (fill annotator columns): agree | missing_label | extra_label |
discourse_off | accuracy_off | needs_theology
"""

from __future__ import annotations

import argparse
import csv
import json
from glob import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = (
    ROOT
    / "papers"
    / "rise_education_2026"
    / "analysis"
    / "jev_judgments"
    / "qc_sheet.csv"
)

FIELDNAMES = (
    "item_id",
    "language",
    "source",
    "family",
    "text_preview",
    "jev_content_labels",
    "jev_discourse_labels",
    "jev_accuracy_score",
    "jev_needs_human_review",
    "annotator_content",
    "annotator_discourse",
    "annotator_accuracy",
    "mark",
    "notes",
)


def expand(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        hits = sorted(glob(pat)) or ([pat] if Path(pat).exists() else [])
        out.extend(Path(h) for h in hits)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "paths",
        nargs="*",
        default=[
            str(
                ROOT
                / "papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl"
            )
        ],
    )
    p.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    rows: list[dict] = []
    for path in expand(args.paths):
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("error"):
                    continue
                rows.append(
                    {
                        "item_id": rec.get("id") or "",
                        "language": rec.get("language") or "",
                        "source": rec.get("source") or "",
                        "family": rec.get("family") or "",
                        "text_preview": (rec.get("text_preview") or "")[:280],
                        "jev_content_labels": "|".join(rec.get("content_labels") or []),
                        "jev_discourse_labels": "|".join(rec.get("discourse_labels") or []),
                        "jev_accuracy_score": rec.get("accuracy_score"),
                        "jev_needs_human_review": rec.get("needs_human_review"),
                        "annotator_content": "",
                        "annotator_discourse": "",
                        "annotator_accuracy": "",
                        "mark": "",
                        "notes": "",
                    }
                )
                if args.limit and len(rows) >= args.limit:
                    break
        if args.limit and len(rows) >= args.limit:
            break

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
