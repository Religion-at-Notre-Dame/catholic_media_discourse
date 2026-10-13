#!/usr/bin/env python3
"""Rebuild findings-data.js from data.js + extras.js (fast, no corpus scan).

Merges Education-track fixture summary so `FINDINGS.education` survives rebuilds.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
VIZ = TOOLS.parent
ROOT = VIZ.parent
DATA = VIZ / "data"
EDU_SUMMARY_LIVE = (
    ROOT
    / "papers/rise_education_2026/analysis/jev_judgments/jev_dual_20261012T080844Z.summary.json"
)
EDU_SUMMARY_FIXTURE = (
    ROOT
    / "papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_summary.json"
)
EDU_SUMMARY = EDU_SUMMARY_LIVE if EDU_SUMMARY_LIVE.exists() else EDU_SUMMARY_FIXTURE


def load_assign(path: Path, name: str) -> dict:
    script = f"""
global.window = {{}};
const fs = require('fs');
eval(fs.readFileSync({json.dumps(str(path))}, 'utf8'));
process.stdout.write(JSON.stringify(window[{json.dumps(name)}]));
"""
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True, cwd=str(VIZ))
    if r.returncode != 0:
        raise SystemExit(r.stderr or r.stdout or f"failed loading {path}")
    return json.loads(r.stdout)


def rate(by: dict, fips: str, theme: str) -> float:
    c = by.get(fips) or {}
    return float((c.get("themes_per_1k") or {}).get(theme) or 0)


def lift_vs_us(by: dict, fips: str, theme: str) -> float | None:
    u = rate(by, "US", theme)
    v = rate(by, fips, theme)
    if not u:
        return None if v else 0.0
    return round(v / u, 2)


def main() -> int:
    viz = load_assign(DATA / "data.js", "VIZ")
    extras = load_assign(DATA / "extras.js", "VIZ_EXTRAS")
    by = {c["fips"]: c for c in extras.get("countryThemes") or []}
    labels = extras.get("themeLabels") or {}
    themes = [
        "liberation_theology",
        "mission",
        "gospel",
        "evangelio",
        "guadalupe",
        "laudato_si",
        "immigration",
        "eucharist",
    ]
    focus = ["US", "MX", "BR", "CI", "ES", "AR", "CO", "PE"]
    matrix = []
    for f in focus:
        c = by.get(f)
        if not c:
            continue
        matrix.append(
            {
                "fips": f,
                "name": c.get("name") or f,
                "n": c.get("n") or 0,
                "rates": {t: rate(by, f, t) for t in themes},
                "lifts": {t: lift_vs_us(by, f, t) for t in themes},
            }
        )

    pairs = []
    for p in (extras.get("compare") or {}).get("pairs") or []:
        deltas = sorted(
            (p.get("delta_per_1k") or {}).items(),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )[:6]
        pairs.append(
            {
                "a": p.get("a"),
                "b": p.get("b"),
                "deltas": [
                    {"theme": t, "label": labels.get(t, t), "delta": d} for t, d in deltas
                ],
            }
        )

    node_label = {n["id"]: n.get("label") or n["id"] for n in (viz.get("topics") or {}).get("nodes") or []}
    cooccur = []
    for e in sorted((viz.get("topics") or {}).get("edges") or [], key=lambda x: -x.get("lift", 0))[:12]:
        cooccur.append(
            {
                "a": node_label.get(e["source"], e["source"]),
                "b": node_label.get(e["target"], e["target"]),
                "lift": e.get("lift"),
                "n": e.get("n"),
            }
        )

    metros = [
        {"name": m["name"], "fips": m["fips"], "n": m["n"]}
        for m in sorted(viz.get("metros") or [], key=lambda x: -x.get("n", 0))[:12]
    ]

    education = load_education_block()

    out = {
        "generated": "viz/tools/build_findings_data.py",
        "corpus": {
            "usNews": "446k",
            "americasNews": "128k",
            "tv": "8,557",
            "radioAAPB": "1,777 EN / 217 ES",
            "period": "2015–Q2 2026",
        },
        "santiago": {
            "n": 1000,
            "lifts": [
                {"theme": "misión", "x": 5.4},
                {"theme": "Fratelli Tutti", "x": 3.5},
                {"theme": "liberation theology", "x": 1.7},
            ],
            "note": "Place-level lifts vs. U.S. news (geolocated GDELT ActionGeo).",
        },
        "signatures": [
            {"place": "Brazil", "theme": "Aparecida / CELAM"},
            {"place": "Central America", "theme": "Óscar Romero"},
            {"place": "Mexico", "theme": "Guadalupe / migration"},
            {"place": "Spanish media", "theme": "evangelio · misión"},
        ],
        "matrix": matrix,
        "themes": themes,
        "pairs": pairs,
        "cooccur": cooccur,
        "metros": metros,
        "themeLabels": labels,
        "delayNote": "Papal documents such as Aparecida can reach Chile days after U.S. desks.",
        "education": education,
    }

    dest = DATA / "findings-data.js"
    dest.write_text("window.FINDINGS = " + json.dumps(out, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"wrote {dest.relative_to(VIZ)} ({dest.stat().st_size:,} B)")
    return 0


def load_education_block() -> dict:
    """Build FINDINGS.education from offline Jev fixture summary (or defaults)."""
    pathways = [
        "Week 0 listening — label media snippets learners recall",
        "Correct gently — misunderstanding / low accuracy triage",
        "Multilingual exemplars — EN/ES/PT prior vocabulary",
    ]
    if not EDU_SUMMARY.exists():
        return {
            "source": "fixtures/demo_dual_en_es_pt.jsonl",
            "n": 0,
            "note": "Dual-taxonomy summary missing — run summarize_jev_judgments.py.",
            "misunderstanding_n": 0,
            "misunderstanding_rate": None,
            "needs_human_review": 0,
            "accuracy_mean": None,
            "top_content": [],
            "top_discourse": [],
            "cross_top": [],
            "pathways": pathways,
        }
    s = json.loads(EDU_SUMMARY.read_text(encoding="utf-8"))
    n = int(s.get("rows_ok") or 0)
    mis = int(s.get("misunderstanding_n") or s.get("misunderstanding") or 0)
    rate = s.get("misunderstanding_rate")
    if rate is None and n:
        rate = round(mis / n, 3)
    content = s.get("content_labels") or {}
    discourse = s.get("discourse_labels") or {}
    cross = s.get("content_x_discourse_top") or s.get("content_x_discourse") or {}
    acc = s.get("accuracy_mean")
    if acc is None and isinstance(s.get("accuracy_score"), dict):
        acc = (s.get("accuracy_score") or {}).get("mean")
    live = EDU_SUMMARY.resolve() == EDU_SUMMARY_LIVE.resolve()
    return {
        "source": (
            "jev_dual_20261012T080844Z.jsonl"
            if live
            else "fixtures/demo_dual_en_es_pt.jsonl"
        ),
        "n": n,
        "note": (
            "Live dual-taxonomy pilot (stratified EN/ES/PT) — triage for educators, not Theology gold."
            if live
            else "Offline dual-taxonomy fixture (EN/ES/PT) — not Theology gold."
        ),
        "misunderstanding_n": mis,
        "misunderstanding_rate": rate,
        "needs_human_review": int(s.get("needs_human_review") or 0),
        "accuracy_mean": acc,
        "top_content": [{"label": k, "n": v} for k, v in list(content.items())[:6]],
        "top_discourse": [{"label": k, "n": v} for k, v in list(discourse.items())[:6]],
        "cross_top": [{"pair": k, "n": v} for k, v in list(cross.items())[:6]],
        "pathways": pathways,
    }


if __name__ == "__main__":
    raise SystemExit(main())
