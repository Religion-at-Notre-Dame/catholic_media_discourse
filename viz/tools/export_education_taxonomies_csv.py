#!/usr/bin/env python3
"""Export dual Education-track taxonomies as a classroom CSV.

  python3 viz/tools/export_education_taxonomies_csv.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
VIZ = TOOLS.parent
ROOT = VIZ.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from common.taxonomies import (  # noqa: E402
    load_content_taxonomy,
    load_discourse_taxonomy,
)

OUT = VIZ / "data" / "education_taxonomies.csv"
FIELDS = (
    "layer",
    "label_id",
    "name",
    "description",
    "example_en",
    "example_es",
    "example_pt",
)


def _first(xs) -> str:
    if not xs:
        return ""
    return str(xs[0])


def rows_for(layer: str, tax: dict) -> list[dict]:
    out: list[dict] = []
    for lab in tax.get("labels") or []:
        out.append(
            {
                "layer": layer,
                "label_id": lab.get("id") or "",
                "name": lab.get("name") or "",
                "description": (
                    (lab.get("description") or "")
                    .strip()
                    .replace("\n", " ")
                    .replace(" \u2014 ", ": ")
                    .replace("\u2014", ", ")
                ),
                "example_en": _first(lab.get("examples_en") or lab.get("examples")),
                "example_es": _first(lab.get("examples_es")),
                "example_pt": _first(lab.get("examples_pt")),
            }
        )
    return out


def main() -> int:
    rows = rows_for("content", load_content_taxonomy()) + rows_for(
        "discourse", load_discourse_taxonomy()
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(VIZ)} ({len(rows)} labels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
