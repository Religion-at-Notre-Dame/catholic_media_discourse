#!/usr/bin/env python3
"""Export formation-relevant Jev rows (drop institutional-only / thin news).

  python3 scripts/judge/export_formation_subset.py \\
    papers/rise_education_2026/analysis/jev_judgments/jev_dual_20261012T080844Z.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEACHING = {
    "doctrine_sacrament",
    "cst_papal",
    "devotion_piety",
    "moral_ethics",
    "migration_politics",
    "evangelization_mission",
    "misunderstanding",
}
THIN = {"institutional_news", "other_unclear"}

DEFAULT_IN = (
    ROOT
    / "papers/rise_education_2026/analysis/jev_judgments/jev_dual_20261012T080844Z.jsonl"
)
OUT_JSONL = (
    ROOT
    / "papers/rise_education_2026/analysis/jev_judgments/formation_subset.jsonl"
)
OUT_CSV = ROOT / "papers/rise_education_2026/teaching/a5_formation_sample.csv"
OUT_QC = (
    ROOT
    / "papers/rise_education_2026/analysis/jev_judgments/qc_sheet_formation_priority.csv"
)

FIELDS = (
    "id",
    "language",
    "source",
    "text_preview",
    "content_labels",
    "discourse_labels",
    "accuracy_score",
    "needs_human_review",
    "priority",
)


def priority(rec: dict) -> str:
    cl = set(rec.get("content_labels") or [])
    if "misunderstanding" in cl:
        return "misunderstanding"
    if rec.get("needs_human_review"):
        return "review"
    try:
        if float(rec.get("accuracy_score") or 99) < 1.5:
            return "low_accuracy"
    except (TypeError, ValueError):
        pass
    if (rec.get("language") or "").lower() in {"spanish", "portuguese"}:
        return "multilingual"
    return "teaching"


def keep(rec: dict) -> bool:
    if rec.get("error"):
        return False
    cl = set(rec.get("content_labels") or [])
    if not cl:
        return False
    if cl <= THIN:
        return False
    return bool(cl & TEACHING)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", type=Path, default=DEFAULT_IN)
    p.add_argument("--limit-csv", type=int, default=120)
    p.add_argument("--limit-qc", type=int, default=200)
    args = p.parse_args()

    kept: list[dict] = []
    with args.path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if keep(rec):
                kept.append(rec)

    # Prefer misunderstanding / ES / review for station CSV
    def sort_key(r: dict) -> tuple:
        pr = priority(r)
        order = {
            "misunderstanding": 0,
            "review": 1,
            "low_accuracy": 2,
            "multilingual": 3,
            "teaching": 4,
        }
        lang = (r.get("language") or "").lower()
        return (order.get(pr, 9), 0 if lang != "english" else 1, r.get("id") or "")

    kept.sort(key=sort_key)

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def row(r: dict) -> dict:
        return {
            "id": r.get("id") or "",
            "language": r.get("language") or "",
            "source": r.get("source") or "",
            "text_preview": (r.get("text_preview") or "")[:320],
            "content_labels": "|".join(r.get("content_labels") or []),
            "discourse_labels": "|".join(r.get("discourse_labels") or []),
            "accuracy_score": r.get("accuracy_score"),
            "needs_human_review": r.get("needs_human_review"),
            "priority": priority(r),
        }

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(row(r) for r in kept[: args.limit_csv])

    with OUT_QC.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=FIELDS
            + ("annotator_content", "annotator_discourse", "annotator_accuracy", "mark", "notes"),
        )
        w.writeheader()
        for r in kept[: args.limit_qc]:
            d = row(r)
            d.update(
                {
                    "annotator_content": "",
                    "annotator_discourse": "",
                    "annotator_accuracy": "",
                    "mark": "",
                    "notes": "",
                }
            )
            w.writerow(d)

    print(f"formation rows={len(kept)} → {OUT_JSONL.relative_to(ROOT)}")
    print(f"classroom CSV n={min(len(kept), args.limit_csv)} → {OUT_CSV.relative_to(ROOT)}")
    print(f"Sidney QC priority n={min(len(kept), args.limit_qc)} → {OUT_QC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
