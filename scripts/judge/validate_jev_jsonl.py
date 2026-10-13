#!/usr/bin/env python3
"""Validate Jev judgment JSONL against dual taxonomies.

  python3 scripts/judge/validate_jev_jsonl.py \\
    papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from glob import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from common.taxonomies import (  # noqa: E402
    label_ids,
    load_content_taxonomy,
    load_discourse_taxonomy,
    validate_taxonomy_schema,
)


def expand(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        hits = sorted(glob(pat)) or ([pat] if Path(pat).exists() else [])
        out.extend(Path(h) for h in hits)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="+")
    args = p.parse_args()

    content = load_content_taxonomy()
    discourse = load_discourse_taxonomy()
    for name, tax in (("content", content), ("discourse", discourse)):
        errs = validate_taxonomy_schema(tax, require_examples=True)
        if errs:
            print(f"TAXONOMY {name}:")
            for e in errs:
                print(f"  ✗ {e}")
            return 1
        print(f"taxonomy {name} OK ({len(label_ids(tax))} labels)")

    allowed_c = set(label_ids(content))
    allowed_d = set(label_ids(discourse))
    n = 0
    bad = 0
    for path in expand(args.paths):
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("error"):
                    continue
                n += 1
                for lab in rec.get("content_labels") or []:
                    if lab not in allowed_c:
                        print(f"{path.name}:{i} unknown content label {lab!r}")
                        bad += 1
                for lab in rec.get("discourse_labels") or []:
                    if lab not in allowed_d:
                        print(f"{path.name}:{i} unknown discourse label {lab!r}")
                        bad += 1
                score = rec.get("accuracy_score")
                if score is not None:
                    try:
                        s = float(score)
                        if s < 0 or s > 4.5:
                            print(f"{path.name}:{i} accuracy_score out of range {s}")
                            bad += 1
                    except (TypeError, ValueError):
                        print(f"{path.name}:{i} bad accuracy_score")
                        bad += 1

    print(f"rows_ok_checked={n} problems={bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
