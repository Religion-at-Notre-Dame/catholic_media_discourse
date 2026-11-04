#!/usr/bin/env python3
"""Rebuild findings-data.js from data.js + extras.js (fast, no corpus scan).

Derives corpus / Santiago / signatures from the live matrix, merges Jev education
summary + correlation hooks into FINDINGS.education and FINDINGS.story.
"""

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
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
VIZ = TOOLS.parent
ROOT = VIZ.parent
DATA = VIZ / "data"
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from common.jev_paths import jev_paths  # noqa: E402
from common.label_pretty import pretty_hook_text  # noqa: E402

_JEV = jev_paths()
STEM = str(_JEV["stem"])
EDU_SUMMARY_LIVE = Path(_JEV["summary"])
EDU_SUMMARY_FIXTURE = Path(_JEV["fixture_summary"])
EDU_SUMMARY = EDU_SUMMARY_LIVE if EDU_SUMMARY_LIVE.exists() else EDU_SUMMARY_FIXTURE
CORR_LIVE = Path(_JEV["correlations"])

# Media-layer counts not yet in data.js / extras (until export includes them).
CORPUS_MEDIA_FALLBACK = {
    "tv": "8,557",
    "radioAAPB": "1,777 EN / 217 ES",
    "period": "2015–Q2 2026",
}


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


def theme_label(labels: dict, theme_id: str) -> str:
    raw = labels.get(theme_id) or theme_id.replace("_", " ")
    # Prefer title case when the extras map stores bare ids.
    if raw == theme_id or "_" in raw or raw.islower():
        return theme_id.replace("_", " ").title().replace("Si", "Si'")
    return raw


def fmt_k(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 10_000:
        return f"{round(n / 1000)}k"
    if n >= 1000:
        return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(n)


def derive_corpus(viz: dict) -> dict:
    us = 0
    americas = 0
    for p in viz.get("places") or []:
        n = int(p.get("n") or 0)
        if p.get("us") or p.get("fips") == "US":
            us += n
        else:
            americas += n
    out = dict(CORPUS_MEDIA_FALLBACK)
    if us:
        out["usNews"] = fmt_k(us)
    else:
        out["usNews"] = "n/a"
    if americas:
        out["americasNews"] = fmt_k(americas)
    else:
        out["americasNews"] = "n/a"
    out["usNewsN"] = us
    out["americasNewsN"] = americas
    return out


def derive_santiago(by: dict, labels: dict, viz: dict, themes: list[str]) -> dict:
    metro = next(
        (
            m
            for m in (viz.get("metros") or [])
            if m.get("name") == "Santiago" and m.get("fips") == "CI"
        ),
        None,
    )
    n = int((metro or {}).get("n") or (by.get("CI") or {}).get("n") or 0)
    lifts_raw = []
    for t in themes:
        x = lift_vs_us(by, "CI", t)
        if x is None:
            continue
        lifts_raw.append(
            {
                "theme": theme_label(labels, t),
                "theme_id": t,
                "x": x,
            }
        )
    lifts_raw.sort(key=lambda d: d["x"], reverse=True)
    lifts = lifts_raw[:3]
    return {
        "n": n,
        "fips": "CI",
        "lifts": lifts,
        "note": (
            "Chile ActionGeo lifts vs. U.S. news (country rates); "
            "N = Santiago metro panel when available."
        ),
    }


def derive_signatures(by: dict, labels: dict, themes: list[str]) -> list[dict]:
    """Distinctive country×theme lifts for the Story signature list."""
    picks = [
        ("MX", "Mexico"),
        ("ES", "El Salvador"),
        ("GT", "Guatemala"),
        ("BR", "Brazil"),
        ("CI", "Chile"),
    ]
    seen_themes: set[str] = set()
    out: list[dict] = []
    scored: list[tuple[float, str, str, str]] = []
    for fips, place in picks:
        if fips not in by:
            continue
        best = None
        for t in themes:
            x = lift_vs_us(by, fips, t)
            if x is None or x < 1.15:
                continue
            if best is None or x > best[0]:
                best = (x, t)
        if best:
            scored.append((best[0], place, best[1], fips))
    scored.sort(reverse=True)
    for x, place, tid, fips in scored:
        if tid in seen_themes and len(out) >= 2:
            continue
        seen_themes.add(tid)
        out.append(
            {
                "place": place,
                "theme": theme_label(labels, tid),
                "theme_id": tid,
                "lift": x,
                "fips": fips,
            }
        )
        if len(out) >= 4:
            break
    if len(out) < 4:
        # Lexicon accent still useful for Story when matrix is thin.
        out.append(
            {
                "place": "Spanish media",
                "theme": "evangelio · misión",
                "theme_id": "evangelio",
                "lift": None,
                "fips": None,
            }
        )
    return out[:4]


def load_hooks() -> dict:
    if not CORR_LIVE.exists():
        return {}
    corr = json.loads(CORR_LIVE.read_text(encoding="utf-8"))
    raw = corr.get("hooks") or {}
    # Humanize taxonomy ids for Story / Findings copy
    out = dict(raw)
    for k in ("place_hook", "types_together", "lang_hook", "institutional_vs_doctrine"):
        if out.get(k):
            out[k] = pretty_hook_text(out[k])
    return out


def build_story(education: dict, hooks: dict) -> dict:
    n = int(education.get("n") or 0)
    mis_pct = hooks.get("misunderstanding_pct")
    if mis_pct is None and education.get("misunderstanding_rate") is not None:
        mis_pct = round(100 * float(education["misunderstanding_rate"]), 1)
    headline = hooks.get("institutional_vs_doctrine") or (
        f"n={n} dual-taxonomy excerpts" if n else "Education triage pending"
    )
    beats = []
    if hooks.get("place_hook"):
        beats.append(
            {
                "id": "place",
                "text": hooks["place_hook"],
                "href": "triage.html#t-places",
            }
        )
    if hooks.get("types_together"):
        beats.append(
            {
                "id": "types",
                "text": hooks["types_together"],
                "href": "triage.html#t-pairs",
            }
        )
    if hooks.get("lang_hook"):
        beats.append(
            {
                "id": "lang",
                "text": hooks["lang_hook"],
                "href": "triage.html#t-lang",
            }
        )
    if mis_pct is not None:
        beats.append(
            {
                "id": "mis",
                "text": f"~{mis_pct}% misunderstanding flags (gentle-correction queue)",
                "href": "triage.html#t-mis",
            }
        )
    beats.append(
        {
            "id": "pathway",
            "text": "Week 0 → correct gently → transfer",
            "href": "findings.html#f-education",
        }
    )
    note = education.get("note") or (
        "Jev pilot: educator triage, not Theology gold. ActionGeo = writing location."
    )
    return {
        "n": n,
        "headline": headline,
        "misunderstanding_pct": mis_pct,
        "review_queue_n": int(education.get("needs_human_review") or 0),
        "accuracy_mean": education.get("accuracy_mean"),
        "beats": beats,
        "note": note,
    }


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
    focus = ["US", "MX", "BR", "CI", "ES", "AR", "CO", "PE", "GT"]
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

    node_label = {
        n["id"]: n.get("label") or n["id"]
        for n in (viz.get("topics") or {}).get("nodes") or []
    }
    cooccur = []
    for e in sorted(
        (viz.get("topics") or {}).get("edges") or [], key=lambda x: -x.get("lift", 0)
    )[:12]:
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
    hooks = load_hooks()
    if hooks:
        education["hooks"] = hooks
    story = build_story(education, hooks)
    santiago = derive_santiago(by, labels, viz, themes)
    # Story/Findings meters must match Chile matrix lifts (verify contract).
    ci_row = next((r for r in matrix if r["fips"] == "CI"), None)
    if ci_row and santiago.get("lifts"):
        for d in santiago["lifts"]:
            tid = d.get("theme_id")
            if tid and ci_row["lifts"].get(tid) is not None:
                d["x"] = ci_row["lifts"][tid]

    out = {
        "generated": "viz/tools/build_findings_data.py",
        "corpus": derive_corpus(viz),
        "santiago": santiago,
        "signatures": derive_signatures(by, labels, themes),
        "matrix": matrix,
        "themes": themes,
        "pairs": pairs,
        "cooccur": cooccur,
        "metros": metros,
        "themeLabels": labels,
        "delayNote": "Papal documents such as Aparecida can reach Chile days after U.S. desks.",
        "education": education,
        "story": story,
    }

    dest = DATA / "findings-data.js"
    dest.write_text(
        "window.FINDINGS = " + json.dumps(_scrub_emdash(out), ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {dest.relative_to(VIZ)} ({dest.stat().st_size:,} B)")
    return 0


def load_education_block() -> dict:
    """Build FINDINGS.education from live or fixture Jev summary."""
    pathways = [
        "Week 0 listening: label media snippets learners recall",
        "Correct gently: misunderstanding / low accuracy triage",
        "Multilingual exemplars: EN/ES/PT prior vocabulary",
    ]
    if not EDU_SUMMARY.exists():
        return {
            "source": "fixtures/demo_dual_en_es_pt.jsonl",
            "live": False,
            "n": 0,
            "note": "Dual-taxonomy summary missing: run summarize_jev_judgments.py.",
            "misunderstanding_n": 0,
            "misunderstanding_rate": None,
            "needs_human_review": 0,
            "accuracy_mean": None,
            "accuracy_mean_by_language": {},
            "languages": {},
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
            f"{STEM}.jsonl" if live else "fixtures/demo_dual_en_es_pt.jsonl"
        ),
        "live": live,
        "n": n,
        "note": (
            "Live dual-taxonomy pilot (stratified EN/ES/PT): triage for educators, not Theology gold."
            if live
            else "Offline dual-taxonomy fixture (EN/ES/PT): not Theology gold."
        ),
        "misunderstanding_n": mis,
        "misunderstanding_rate": rate,
        "needs_human_review": int(s.get("needs_human_review") or 0),
        "accuracy_mean": acc,
        "accuracy_mean_by_language": s.get("accuracy_mean_by_language") or {},
        "languages": s.get("languages") or {},
        "top_content": [{"label": k, "n": v} for k, v in list(content.items())[:6]],
        "top_discourse": [{"label": k, "n": v} for k, v in list(discourse.items())[:6]],
        "cross_top": [{"pair": k, "n": v} for k, v in list(cross.items())[:6]],
        "pathways": pathways,
    }


if __name__ == "__main__":
    raise SystemExit(main())
