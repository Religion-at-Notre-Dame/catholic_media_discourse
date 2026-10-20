#!/usr/bin/env python3
"""Build viz/data/triage-data.js from live Jev correlation + network JSON."""

from __future__ import annotations

def _scrub_emdash(obj):
    """Replace Unicode em dashes in strings so the classroom site never ships them."""
    if isinstance(obj, str):
        return obj.replace(" \u2014 ", ": ").replace("\u2014", ", ")
    if isinstance(obj, list):
        return [_scrub_emdash(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _scrub_emdash(v) for k, v in obj.items()}
    return obj


import json
from pathlib import Path

import sys

TOOLS = Path(__file__).resolve().parent
VIZ = TOOLS.parent
ROOT = VIZ.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from common.jev_paths import jev_paths  # noqa: E402
from common.label_pretty import pretty_hook_text, pretty_label  # noqa: E402

_JEV = jev_paths()
STEM = str(_JEV["stem"])
CORR = Path(_JEV["correlations"])
NET = Path(_JEV["networks"])
OUT = VIZ / "data" / "triage-data.js"


def _outlet_rates(corr_path: Path) -> list:
    """Content-label percents by outlet, from the family rows of lang_x_type.csv."""
    csv_path = corr_path.with_name(corr_path.name.replace("_correlations.json", "_lang_x_type.csv"))
    if not csv_path.is_file():
        return []
    import csv

    rows = []
    with csv_path.open(encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            if (rec.get("axis") or "") != "family":
                continue
            item = {"outlet": rec.get("location") or "", "n": int(float(rec.get("n") or 0))}
            for key, val in rec.items():
                if key in ("location", "n", "axis"):
                    continue
                item[key] = float(val or 0)
            rows.append(item)
    order = {"news": 0, "tv": 1, "youtube": 2, "radio": 3}
    rows.sort(key=lambda r: order.get(r["outlet"], 9))
    return rows


def main() -> int:
    if not CORR.exists() or not NET.exists():
        raise SystemExit(
            f"missing {CORR.name} / {NET.name}: run scripts/judge/analyze_jev_correlations.py"
        )
    corr = json.loads(CORR.read_text(encoding="utf-8"))
    net = json.loads(NET.read_text(encoding="utf-8"))
    hooks = dict(corr.get("hooks") or {})
    for k in ("place_hook", "types_together", "lang_hook", "institutional_vs_doctrine"):
        if hooks.get(k):
            hooks[k] = pretty_hook_text(hooks[k])

    def pretty_rows(rows: list, label_keys: tuple[str, ...] = ("label", "a", "b")) -> list:
        out_rows = []
        for r in rows or []:
            rr = dict(r)
            for lk in label_keys:
                if lk in rr and isinstance(rr[lk], str) and "_" in rr[lk]:
                    rr[lk] = pretty_label(rr[lk])
            out_rows.append(rr)
        return out_rows

    networks = {
        "types_together": net.get("types_together") or {"nodes": [], "edges": []},
        "place_x_type": net.get("place_x_type") or {"nodes": [], "edges": []},
    }
    for bundle in networks.values():
        for n in bundle.get("nodes") or []:
            lid = str(n.get("id") or "")
            if n.get("type") == "content" or lid.startswith("content:"):
                n["label"] = pretty_label(lid.split(":", 1)[-1] if ":" in lid else n.get("label"))

    out = {
        "generated": "viz/tools/build_triage_data.py",
        "stem": STEM,
        "n": corr.get("n_judgments"),
        "geo_with_fips": corr.get("geo_with_fips"),
        "stats": corr.get("stats") or net.get("stats") or {},
        "hooks": hooks,
        "outlet_counts": corr.get("families") or {},
        "outlet_rates": _outlet_rates(CORR),
        "content_counts": corr.get("content_label_counts") or {},
        "discourse_counts": corr.get("discourse_label_counts") or {},
        "types_together": pretty_rows(
            (corr.get("content_cooccur_clean_top") or corr.get("content_cooccur_top") or [])[:10]
        ),
        "content_x_discourse": pretty_rows(
            (corr.get("content_x_discourse_clean_top") or corr.get("content_x_discourse_top") or [])[
                :10
            ]
        ),
        "place_lifts": pretty_rows(corr.get("location_distinctive_top") or []),
        "lang_contrast": pretty_rows(corr.get("language_contrast_en_vs_es") or []),
        "family_contrast": pretty_rows(corr.get("family_contrast_news_vs_radio") or []),
        "misunderstanding_hotspots": corr.get("misunderstanding_by_location") or [],
        "networks": networks,
        "note": (
            "Dual-taxonomy Jev pilot: triage for educators, not Theology gold. "
            "Associations use Fisher exact tests with Holm–Bonferroni within each family. "
            "ActionGeo = writing location for news only."
        ),
    }
    OUT.write_text(
        "window.TRIAGE = " + json.dumps(_scrub_emdash(out), ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(VIZ)} ({OUT.stat().st_size:,} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
