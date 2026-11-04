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


_ACC_LABELS = {
    0: "Cannot assess",
    1: "Clearly inaccurate",
    2: "Partial or misleading",
    3: "Broadly accurate",
    4: "Accurate and clear",
}


def _iter_judgments(corr_path: Path):
    jsonl = corr_path.with_name(corr_path.name.replace("_correlations.json", ".jsonl"))
    if not jsonl.is_file():
        return
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("error"):
                continue
            yield rec


def _accuracy_breakdown(corr_path: Path) -> list:
    counts = {i: 0 for i in range(5)}
    n = 0
    for rec in _iter_judgments(corr_path):
        n += 1
        score = rec.get("accuracy_score")
        if score is None:
            continue
        try:
            idx = int(score)
        except (TypeError, ValueError):
            continue
        if idx in counts:
            counts[idx] += 1
    rows = []
    for idx in range(5):
        c = counts[idx]
        rows.append(
            {
                "score": idx,
                "label": _ACC_LABELS[idx],
                "n": c,
                "pct": round(100 * c / n, 2) if n else 0,
            }
        )
    return rows


def _mis_by_content(corr_path: Path) -> list:
    labels = (
        "doctrine_sacrament",
        "moral_ethics",
        "migration_politics",
        "other_unclear",
        "devotion_piety",
        "cst_papal",
        "institutional_news",
        "evangelization_mission",
    )
    cat_n = {k: 0 for k in labels}
    mis_n = {k: 0 for k in labels}
    for rec in _iter_judgments(corr_path):
        cl = set(rec.get("content_labels") or [])
        flagged = "misunderstanding" in cl
        for lab in labels:
            if lab not in cl:
                continue
            cat_n[lab] += 1
            if flagged:
                mis_n[lab] += 1
    rows = []
    for lab in labels:
        base = cat_n[lab]
        hits = mis_n[lab]
        rows.append(
            {
                "label": pretty_label(lab),
                "n": base,
                "misunderstanding_n": hits,
                "pct_within": round(100 * hits / base, 2) if base else 0,
            }
        )
    rows.sort(key=lambda r: -r["pct_within"])
    return rows


def _day_key(raw: str) -> str:
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


def _dependence_check(corr_path: Path) -> dict:
    """Collapse paragraphs that share an outlet and a day, then retest."""
    from collections import defaultdict

    from scipy.stats import fisher_exact

    from common.analysis_paths import analysis_source_paths, source_path_list
    from common.api_record import domain_from_url

    judgments = []
    wanted: dict[tuple[str, str], list[int]] = defaultdict(list)
    for rec in _iter_judgments(corr_path):
        uid = str(rec.get("id") or "")
        parts = uid.split("|")
        source = str(rec.get("source") or (parts[0] if parts else ""))
        eid = parts[1] if len(parts) > 1 else ""
        idx = len(judgments)
        judgments.append(
            {
                "source": source,
                "family": str(rec.get("family") or ""),
                "labels": set(rec.get("content_labels") or []),
                "eid": eid,
            }
        )
        if source and eid:
            wanted[(source, eid)].append(idx)

    paths_map = analysis_source_paths(ROOT)
    cluster_for = {}
    for (source, eid), idxs in wanted.items():
        cluster_for[(source, eid)] = None

    def assign(source: str, eid: str, key: str) -> None:
        if (source, eid) in cluster_for and cluster_for[(source, eid)] is None and key:
            cluster_for[(source, eid)] = key

    for source, path_val in paths_map.items():
        if not any(s == source for s, _ in wanted):
            continue
        for path in source_path_list(path_val):
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    eid = str(
                        rec.get("event_id")
                        or rec.get("record_id")
                        or rec.get("item_id")
                        or rec.get("id")
                        or ""
                    )
                    if (source, eid) not in cluster_for or cluster_for[(source, eid)]:
                        continue
                    day = _day_key(
                        rec.get("gdelt_day")
                        or rec.get("show_date")
                        or rec.get("published_at")
                        or rec.get("date")
                        or ""
                    )
                    if source.startswith("gdelt_news"):
                        outlet = domain_from_url(str(rec.get("url") or "")) or source
                    elif source == "gdelt_tv":
                        outlet = str(rec.get("station") or source)
                    elif source.startswith("aapb") or source.endswith("radio"):
                        outlet = str(rec.get("station") or rec.get("series_title") or source)
                    elif "youtube" in source:
                        outlet = str(rec.get("channel_id") or rec.get("channel_title") or source)
                    else:
                        outlet = source
                    assign(source, eid, f"{outlet}|{day or 'nd'}")

    groups: dict[str, dict] = {}
    for i, row in enumerate(judgments):
        key = cluster_for.get((row["source"], row["eid"])) or f"row:{i}"
        g = groups.get(key)
        if g is None:
            groups[key] = {"family": row["family"], "labels": set(row["labels"])}
        else:
            g["labels"].update(row["labels"])

    def rates(units, label="misunderstanding"):
        out = {}
        for fam in ("news", "tv", "youtube", "radio"):
            rows = [u for u in units if u["family"] == fam]
            if not rows:
                continue
            hits = sum(1 for u in rows if label in u["labels"])
            out[fam] = {
                "n": len(rows),
                "hits": hits,
                "pct": round(100 * hits / len(rows), 2),
            }
        return out

    para_units = [
        {"family": r["family"], "labels": r["labels"]} for r in judgments
    ]
    clus_units = list(groups.values())
    para = rates(para_units)
    clus = rates(clus_units)

    def fisher_news_radio(table):
        a = table.get("news") or {"hits": 0, "n": 0}
        b = table.get("radio") or {"hits": 0, "n": 0}
        oddsr, p = fisher_exact(
            [
                [a["hits"], a["n"] - a["hits"]],
                [b["hits"], b["n"] - b["hits"]],
            ]
        )
        ratio = (a["pct"] / b["pct"]) if b.get("pct") else None
        return {
            "odds_ratio": round(float(oddsr), 3),
            "p": float(p),
            "ratio": round(ratio, 2) if ratio else None,
            "significant": bool(p < 0.05),
        }

    within = []
    for lab in (
        "doctrine_sacrament",
        "moral_ethics",
        "migration_politics",
        "institutional_news",
        "devotion_piety",
        "cst_papal",
        "evangelization_mission",
    ):
        base = [u for u in clus_units if lab in u["labels"]]
        if not base:
            continue
        hits = sum(1 for u in base if "misunderstanding" in u["labels"])
        within.append(
            {
                "label": pretty_label(lab),
                "n": len(base),
                "misunderstanding_n": hits,
                "pct_within": round(100 * hits / len(base), 2),
            }
        )
    within.sort(key=lambda r: -r["pct_within"])
    news_radio = fisher_news_radio(clus)
    return {
        "n_paragraphs": len(judgments),
        "n_clusters": len(groups),
        "misunderstanding_paragraph": para,
        "misunderstanding_cluster": clus,
        "news_vs_radio_cluster": news_radio,
        "within_type_cluster": within,
    }


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
        "accuracy_counts": _accuracy_breakdown(CORR),
        "misunderstanding_by_content": _mis_by_content(CORR),
        "dependence": _dependence_check(CORR),
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
