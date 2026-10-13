#!/usr/bin/env python3
"""Build viz/data/triage-data.js from live Jev correlation + network JSON."""

from __future__ import annotations

import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
VIZ = TOOLS.parent
ROOT = VIZ.parent
JEV = ROOT / "papers/rise_education_2026/analysis/jev_judgments"
STEM = "jev_dual_20261012T080844Z"
CORR = JEV / f"{STEM}_correlations.json"
NET = JEV / f"{STEM}_networks.json"
OUT = VIZ / "data" / "triage-data.js"


def main() -> int:
    if not CORR.exists() or not NET.exists():
        raise SystemExit(
            f"missing {CORR.name} / {NET.name} — run scripts/judge/analyze_jev_correlations.py"
        )
    corr = json.loads(CORR.read_text(encoding="utf-8"))
    net = json.loads(NET.read_text(encoding="utf-8"))
    out = {
        "generated": "viz/tools/build_triage_data.py",
        "n": corr.get("n_judgments"),
        "geo_with_fips": corr.get("geo_with_fips"),
        "stats": corr.get("stats") or net.get("stats") or {},
        "hooks": corr.get("hooks") or {},
        "content_counts": corr.get("content_label_counts") or {},
        "discourse_counts": corr.get("discourse_label_counts") or {},
        "types_together": (corr.get("content_cooccur_clean_top") or corr.get("content_cooccur_top") or [])[
            :10
        ],
        "content_x_discourse": (
            corr.get("content_x_discourse_clean_top") or corr.get("content_x_discourse_top") or []
        )[:10],
        "place_lifts": corr.get("location_distinctive_top") or [],
        "lang_contrast": corr.get("language_contrast_en_vs_es") or [],
        "family_contrast": corr.get("family_contrast_news_vs_radio") or [],
        "misunderstanding_hotspots": corr.get("misunderstanding_by_location") or [],
        "networks": {
            "types_together": net.get("types_together") or {"nodes": [], "edges": []},
            "place_x_type": net.get("place_x_type") or {"nodes": [], "edges": []},
        },
        "note": (
            "Dual-taxonomy Jev pilot — triage for educators, not Theology gold. "
            "Associations use Fisher exact tests with Holm–Bonferroni within each family. "
            "ActionGeo = writing location for news only."
        ),
    }
    OUT.write_text(
        "window.TRIAGE = " + json.dumps(out, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(VIZ)} ({OUT.stat().st_size:,} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
