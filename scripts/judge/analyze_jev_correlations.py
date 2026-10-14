#!/usr/bin/env python3
"""Jev dual-taxonomy correlations: co-occurring types + location × type.

  python3 scripts/judge/analyze_jev_correlations.py \\
    papers/rise_education_2026/analysis/jev_judgments/jev_dual_20261012T080844Z.jsonl

Outputs (next to the JSONL by default):
  *_correlations.json  : full summary
  *_label_cooccur.csv  : content×content, discourse×discourse, content×discourse
  *_location_x_type.csv: ActionGeo country/region × content (news join)
  *_lang_x_type.csv    : language / family × content rates
  figures/jev_corr_*.png: optional heatmaps
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from common.analysis_paths import analysis_source_paths, source_path_list  # noqa: E402
from common.evangelization_themes import combined_text  # noqa: E402
from common.geography import (  # noqa: E402
    collection_region_from_fips,
    fips_country_name,
    record_action_fips,
)
from common.label_pretty import pretty_label  # noqa: E402
from scipy.stats import fisher_exact  # noqa: E402

NEWS_SOURCES = {
    "gdelt_news_us",
    "gdelt_news_americas",
    "gdelt_news_main",
    "gdelt_news_2015_2022",
    "americas_news_2015_2022",
    "americas_news_2024",
    "gdelt_news_2025_26",
    "americas_news_2025_26",
}

ALPHA = 0.05


def holm_adjust(pvalues: list[float]) -> list[float]:
    """Holm–Bonferroni adjusted p-values (step-down)."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    adj = [1.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        val = float(pvalues[i]) * (m - rank)
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj


def fisher_2x2(a: int, b: int, c: int, d: int) -> tuple[float, float]:
    """Return (odds_ratio, p_value) for [[a,b],[c,d]]; two-sided Fisher."""
    a, b, c, d = int(a), int(b), int(c), int(d)
    # Guard empty margins
    if min(a + b, c + d, a + c, b + d) <= 0:
        return float("nan"), 1.0
    try:
        oddsratio, p = fisher_exact([[a, b], [c, d]], alternative="two-sided")
        return float(oddsratio), float(p)
    except ValueError:
        return float("nan"), 1.0


def stars(p: float | None) -> str:
    if p is None or p != p:  # NaN
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def attach_holm(rows: list[dict[str, Any]], p_key: str = "p") -> list[dict[str, Any]]:
    if not rows:
        return rows
    ps: list[float] = []
    for r in rows:
        raw = r.get(p_key)
        # Important: p=0.0 is significant: do not use `or 1.0` (0.0 is falsy).
        ps.append(1.0 if raw is None else float(raw))
    adj = holm_adjust(ps)
    for r, q in zip(rows, adj):
        # Keep tiny adjusted values readable without collapsing true zeros wrongly
        r["p_holm"] = 0.0 if q == 0.0 else round(q, 6)
        r["significant"] = bool(q < ALPHA)
        r["stars"] = stars(q)
    return rows


def enrich_pair_stats(
    *,
    both: int,
    n_a: int,
    n_b: int,
    n_docs: int,
) -> dict[str, Any]:
    """Stats for co-occurrence of binary labels A and B."""
    aa = both
    bb = n_a - both  # A only
    cc = n_b - both  # B only
    dd = n_docs - n_a - n_b + both
    expected = (n_a * n_b) / n_docs if n_docs else 0.0
    lift = (aa / expected) if expected else 0.0
    denom = math.sqrt(max(0.0, (aa + bb) * (cc + dd) * (aa + cc) * (bb + dd)))
    phi = ((aa * dd) - (bb * cc)) / denom if denom else 0.0
    jacc = aa / (n_a + n_b - aa) if (n_a + n_b - aa) else 0.0
    oddsr, p = fisher_2x2(aa, bb, cc, dd)
    return {
        "n": aa,
        "n_a": n_a,
        "n_b": n_b,
        "lift": round(lift, 3),
        "phi": round(phi, 3),
        "jaccard": round(jacc, 3),
        "odds_ratio": None if oddsr != oddsr else round(oddsr, 3),
        "p": round(p, 8),
    }


def parse_uid(uid: str) -> tuple[str, str, str]:
    parts = (uid or "").split("|", 2)
    if len(parts) != 3:
        return "", "", ""
    return parts[0], parts[1], parts[2]


def text_hash(text: str, *, max_chars: int = 2500) -> str:
    return hashlib.sha1((text or "")[:max_chars].encode("utf-8")).hexdigest()[:16]


def pairwise_counts(labels: list[str]) -> Counter[tuple[str, str]]:
    labs = sorted({str(x) for x in labels if x})
    out: Counter[tuple[str, str]] = Counter()
    for a, b in combinations(labs, 2):
        out[(a, b)] += 1
    return out


def lift_table(
    pair_n: Counter[tuple[str, str]],
    single_n: Counter[str],
    n_docs: int,
    *,
    min_n: int = 20,
    top: int = 40,
    prefer_sig: bool = True,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (a, b), w in pair_n.items():
        if w < min_n:
            continue
        na, nb = single_n[a], single_n[b]
        if not na or not nb or not n_docs:
            continue
        stats = enrich_pair_stats(both=w, n_a=na, n_b=nb, n_docs=n_docs)
        rows.append({"a": a, "b": b, **stats})
    attach_holm(rows, "p")
    if prefer_sig:
        rows.sort(
            key=lambda r: (
                0 if r.get("significant") else 1,
                r.get("p_holm", 1.0),
                -r["lift"],
                -r["n"],
            )
        )
    else:
        rows.sort(key=lambda r: (-r["lift"], -r["n"]))
    return rows[:top]


def rate_matrix(
    by_loc: dict[str, Counter[str]],
    loc_n: Counter[str],
    labels: Iterable[str],
    *,
    min_loc_n: int = 30,
) -> list[dict[str, Any]]:
    labs = list(labels)
    rows: list[dict[str, Any]] = []
    for loc, n in loc_n.most_common():
        if n < min_loc_n:
            continue
        c = by_loc[loc]
        row: dict[str, Any] = {"location": loc, "n": n}
        for lab in labs:
            row[lab] = round(100.0 * c[lab] / n, 2) if n else 0.0
        rows.append(row)
    return rows


def load_judgments(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("error"):
                continue
            rows.append(rec)
    return rows


def join_news_geo(
    judgments: list[dict],
    *,
    root: Path,
    max_chars: int = 2500,
) -> dict[str, dict[str, str]]:
    """Map judgment id → {fips, country, region} for news rows."""
    needed: dict[str, set[str]] = defaultdict(set)  # source -> event_ids
    want_hash: dict[tuple[str, str], set[str]] = defaultdict(set)  # (source, eid) -> hashes
    news_uids: set[str] = set()
    for rec in judgments:
        uid = rec.get("id") or ""
        source, eid, th = parse_uid(uid)
        if source not in NEWS_SOURCES or not eid:
            continue
        needed[source].add(eid)
        want_hash[(source, eid)].add(th)
        news_uids.add(uid)

    if not news_uids:
        return {}

    paths_map = analysis_source_paths(root)
    matched: dict[str, dict[str, str]] = {}
    remaining = set(news_uids)

    for source, eids in needed.items():
        path_val = paths_map.get(source)
        if not path_val:
            continue
        for path in source_path_list(path_val):
            if not path.exists() or not remaining:
                continue
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if not remaining:
                        break
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    eid = str(rec.get("event_id") or rec.get("record_id") or "")
                    if eid not in eids:
                        continue
                    text = combined_text(rec)
                    th = text_hash(text, max_chars=max_chars)
                    if th not in want_hash[(source, eid)]:
                        # fallback: accept first hit for this event if only one wanted
                        if len(want_hash[(source, eid)]) != 1:
                            continue
                        th = next(iter(want_hash[(source, eid)]))
                    uid = f"{source}|{eid}|{th}"
                    if uid not in remaining:
                        # try any hash for this event that is still open
                        hit = None
                        for h in want_hash[(source, eid)]:
                            cand = f"{source}|{eid}|{h}"
                            if cand in remaining:
                                hit = cand
                                break
                        if not hit:
                            continue
                        uid = hit
                    fips = record_action_fips(rec, source_hint=source)
                    matched[uid] = {
                        "fips": fips or "",
                        "country": fips_country_name(fips) if fips else "",
                        "region": collection_region_from_fips(fips) or "",
                    }
                    remaining.discard(uid)

    return matched


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def maybe_plot(
    out_dir: Path,
    content_pairs: list[dict],
    loc_rates: list[dict],
    content_labels: list[str],
) -> list[str]:
    written: list[str] = []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return written

    # Co-occurrence lift bars (top content pairs)
    if content_pairs:
        top = content_pairs[:12][::-1]
        fig, ax = plt.subplots(figsize=(8.5, 4.5), constrained_layout=True)
        labels = [f"{r['a']} × {r['b']}" for r in top]
        vals = [r["lift"] for r in top]
        ax.barh(labels, vals, color="#2c5f4a")
        ax.axvline(1.0, color="#888", lw=1, ls="--")
        ax.set_xlabel("lift (co-occurrence)")
        ax.set_title("Content labels that travel together (Jev)")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        p = out_dir / "jev_corr_content_pairs.png"
        fig.savefig(p, dpi=150)
        plt.close(fig)
        written.append(str(p))

    # Location × type heatmap (rates)
    if loc_rates and content_labels:
        labs = [c for c in content_labels if c != "other_unclear"][:8]
        locs = [r["location"] for r in loc_rates[:10]]
        if locs and labs:
            mat = np.array([[float(r.get(lab, 0.0)) for lab in labs] for r in loc_rates[:10]])
            fig, ax = plt.subplots(figsize=(10, 4.8), constrained_layout=True)
            im = ax.imshow(mat, aspect="auto", cmap="YlGnBu")
            ax.set_xticks(range(len(labs)))
            ax.set_xticklabels([x.replace("_", "\n") for x in labs], fontsize=8)
            ax.set_yticks(range(len(locs)))
            ax.set_yticklabels(locs, fontsize=8)
            ax.set_title("ActionGeo location × content rate (% of rows)")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="%")
            p = out_dir / "jev_corr_location_x_content.png"
            fig.savefig(p, dpi=150)
            plt.close(fig)
            written.append(str(p))
    return written


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=ROOT
        / "papers/rise_education_2026/analysis/jev_judgments/jev_dual_20261012T080844Z.jsonl",
    )
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--min-pair-n", type=int, default=25)
    p.add_argument("--min-loc-n", type=int, default=40)
    p.add_argument("--skip-geo", action="store_true", help="Skip ActionGeo shard join")
    p.add_argument("--no-plot", action="store_true")
    p.add_argument(
        "--max-chars",
        type=int,
        default=1600,
        help="Must match Jev pipeline --max-chars (hash of capped text)",
    )
    args = p.parse_args()

    judgments = load_judgments(args.path)
    n = len(judgments)
    if not n:
        raise SystemExit("no judgments")

    out_dir = (args.out_dir or args.path.parent).resolve()
    stem = args.path.stem
    fig_dir = (ROOT / "papers/rise_education_2026/figures").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    content_single: Counter[str] = Counter()
    discourse_single: Counter[str] = Counter()
    content_pairs: Counter[tuple[str, str]] = Counter()
    discourse_pairs: Counter[tuple[str, str]] = Counter()
    cross: Counter[tuple[str, str]] = Counter()
    lang_n: Counter[str] = Counter()
    fam_n: Counter[str] = Counter()
    lang_content: dict[str, Counter[str]] = defaultdict(Counter)
    fam_content: dict[str, Counter[str]] = defaultdict(Counter)
    lang_discourse: dict[str, Counter[str]] = defaultdict(Counter)

    for rec in judgments:
        cl = [str(x) for x in (rec.get("content_labels") or [])]
        dl = [str(x) for x in (rec.get("discourse_labels") or [])]
        lang = (rec.get("language") or "?").lower()
        fam = (rec.get("family") or "?").lower()
        lang_n[lang] += 1
        fam_n[fam] += 1
        for c in cl:
            content_single[c] += 1
            lang_content[lang][c] += 1
            fam_content[fam][c] += 1
        for d in dl:
            discourse_single[d] += 1
            lang_discourse[lang][d] += 1
        content_pairs.update(pairwise_counts(cl))
        discourse_pairs.update(pairwise_counts(dl))
        for c in cl:
            for d in dl:
                cross[(c, d)] += 1

    content_co = lift_table(content_pairs, content_single, n, min_n=args.min_pair_n)
    discourse_co = lift_table(discourse_pairs, discourse_single, n, min_n=args.min_pair_n)
    cross_ctr = Counter({k: v for k, v in cross.items()})
    cross_rows: list[dict[str, Any]] = []
    for (a, b), w in cross_ctr.items():
        if w < args.min_pair_n:
            continue
        na, nb = content_single[a], discourse_single[b]
        if not na or not nb:
            continue
        stats = enrich_pair_stats(both=w, n_a=na, n_b=nb, n_docs=n)
        # phi for rectangular content×discourse still meaningful via same 2×2
        cross_rows.append({"a": a, "b": b, "layer": "content×discourse", **stats})
    attach_holm(cross_rows, "p")
    cross_rows.sort(
        key=lambda r: (
            0 if r.get("significant") else 1,
            r.get("p_holm", 1.0),
            -r["lift"],
            -r["n"],
        )
    )
    cross_rows = cross_rows[:50]

    cooccur_csv: list[dict] = []
    for r in content_co:
        cooccur_csv.append({**r, "layer": "content×content"})
    for r in discourse_co:
        cooccur_csv.append({**r, "layer": "discourse×discourse"})
    cooccur_csv.extend(cross_rows)

    content_labs = [k for k, _ in content_single.most_common()]
    discourse_labs = [k for k, _ in discourse_single.most_common()]
    lang_x = rate_matrix(lang_content, lang_n, content_labs, min_loc_n=10)
    fam_x = rate_matrix(fam_content, fam_n, content_labs, min_loc_n=10)
    lang_d = rate_matrix(lang_discourse, lang_n, discourse_labs, min_loc_n=10)

    geo_map: dict[str, dict[str, str]] = {}
    loc_content: dict[str, Counter[str]] = defaultdict(Counter)
    loc_n: Counter[str] = Counter()
    loc_mis: Counter[str] = Counter()
    region_content: dict[str, Counter[str]] = defaultdict(Counter)
    region_n: Counter[str] = Counter()
    geo_join_n = 0
    geo_with_fips = 0

    if not args.skip_geo:
        print("joining news judgments → ActionGeo FIPS (anon shards)…")
        geo_map = join_news_geo(judgments, root=ROOT, max_chars=args.max_chars)
        for rec in judgments:
            uid = rec.get("id") or ""
            g = geo_map.get(uid)
            if not g:
                continue
            geo_join_n += 1
            fips = g.get("fips") or ""
            if not fips:
                continue
            geo_with_fips += 1
            country = g.get("country") or fips
            region = g.get("region") or "other"
            loc_n[country] += 1
            region_n[region] += 1
            clabs = [str(c) for c in (rec.get("content_labels") or [])]
            if "misunderstanding" in clabs:
                loc_mis[country] += 1
            for c in clabs:
                loc_content[country][c] += 1
                region_content[region][c] += 1

    loc_rates = rate_matrix(loc_content, loc_n, content_labs, min_loc_n=args.min_loc_n)
    region_rates = rate_matrix(
        region_content, region_n, content_labs, min_loc_n=max(20, args.min_loc_n // 2)
    )

    # Country distinctive: Fisher country vs rest-of-geo for each label
    distinctive: list[dict[str, Any]] = []
    if geo_with_fips:
        base = Counter()
        for c in loc_content.values():
            base.update(c)
        for country, n_loc in loc_n.items():
            if n_loc < args.min_loc_n:
                continue
            rest_n = geo_with_fips - n_loc
            if rest_n < args.min_loc_n:
                continue
            for lab, hits in loc_content[country].items():
                if lab in {"other_unclear"}:
                    continue
                rest_hits = base[lab] - hits
                rate = hits / n_loc
                base_rate = base[lab] / geo_with_fips if geo_with_fips else 0
                if base_rate <= 0:
                    continue
                lift = rate / base_rate
                if hits < 8 or lift < 1.25:
                    continue
                # [[in∩lab, in\lab], [out∩lab, out\lab]]
                oddsr, p = fisher_2x2(hits, n_loc - hits, rest_hits, rest_n - rest_hits)
                distinctive.append(
                    {
                        "location": country,
                        "label": lab,
                        "n_loc": n_loc,
                        "hits": hits,
                        "rate_pct": round(100 * rate, 2),
                        "baseline_pct": round(100 * base_rate, 2),
                        "lift_vs_geo_news": round(lift, 2),
                        "odds_ratio": None if oddsr != oddsr else round(oddsr, 3),
                        "p": round(p, 8),
                    }
                )
        attach_holm(distinctive, "p")
        distinctive.sort(
            key=lambda r: (
                0 if r.get("significant") else 1,
                r.get("p_holm", 1.0),
                -r["lift_vs_geo_news"],
                -r["hits"],
            )
        )

    def contrast_rates(
        a_name: str,
        a_n: int,
        a_c: Counter[str],
        b_name: str,
        b_n: int,
        b_c: Counter[str],
        *,
        min_hits: int = 20,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if a_n < 50 or b_n < 50:
            return rows
        for lab in set(a_c) | set(b_c):
            if lab == "other_unclear":
                continue
            ha, hb = a_c[lab], b_c[lab]
            if ha + hb < min_hits:
                continue
            ra = ha / a_n
            rb = hb / b_n
            ratio = (ra / rb) if rb > 0 else (99.0 if ra > 0 else 1.0)
            # [[EN∩lab, EN\lab], [ES∩lab, ES\lab]]
            oddsr, p = fisher_2x2(ha, a_n - ha, hb, b_n - hb)
            rows.append(
                {
                    "label": lab,
                    "a": a_name,
                    "b": b_name,
                    "rate_a_pct": round(100 * ra, 2),
                    "rate_b_pct": round(100 * rb, 2),
                    "ratio_a_over_b": round(ratio, 2),
                    "hits_a": ha,
                    "hits_b": hb,
                    "odds_ratio": None if oddsr != oddsr else round(oddsr, 3),
                    "p": round(p, 8),
                }
            )
        attach_holm(rows, "p")
        rows.sort(
            key=lambda r: (
                0 if r.get("significant") else 1,
                r.get("p_holm", 1.0),
                -abs(math.log(max(r["ratio_a_over_b"], 1e-6))),
                -r["hits_a"],
            )
        )
        return rows

    lang_contrast = contrast_rates(
        "english",
        lang_n.get("english", 0),
        lang_content.get("english", Counter()),
        "spanish",
        lang_n.get("spanish", 0),
        lang_content.get("spanish", Counter()),
    )
    fam_contrast = contrast_rates(
        "news",
        fam_n.get("news", 0),
        fam_content.get("news", Counter()),
        "radio",
        fam_n.get("radio", 0),
        fam_content.get("radio", Counter()),
    )

    mis_by_loc: list[dict[str, Any]] = []
    if geo_with_fips:
        mis_total = sum(loc_mis.values())
        for loc in loc_n:
            if loc_n[loc] < args.min_loc_n or loc_mis[loc] < 3:
                continue
            hits = loc_mis[loc]
            n_loc = loc_n[loc]
            rest_n = geo_with_fips - n_loc
            rest_hits = mis_total - hits
            oddsr, p = fisher_2x2(hits, n_loc - hits, rest_hits, rest_n - rest_hits)
            mis_by_loc.append(
                {
                    "location": loc,
                    "n": n_loc,
                    "misunderstanding_n": hits,
                    "misunderstanding_pct": round(100 * hits / n_loc, 2),
                    "baseline_pct": round(100 * mis_total / geo_with_fips, 2),
                    "odds_ratio": None if oddsr != oddsr else round(oddsr, 3),
                    "p": round(p, 8),
                }
            )
        attach_holm(mis_by_loc, "p")
        mis_by_loc.sort(
            key=lambda r: (
                0 if r.get("significant") else 1,
                r.get("p_holm", 1.0),
                -r["misunderstanding_pct"],
            )
        )

    clean_content_co = [
        r
        for r in content_co
        if "other_unclear" not in (r["a"], r["b"]) and r.get("significant")
    ] or [
        r for r in content_co if "other_unclear" not in (r["a"], r["b"])
    ]
    clean_cross = [
        r
        for r in cross_rows
        if "other_unclear" not in (r["a"], r["b"]) and r.get("significant")
    ] or [
        r for r in cross_rows if "other_unclear" not in (r["a"], r["b"])
    ]
    sig_distinctive = [r for r in distinctive if r.get("significant")] or distinctive[:20]
    sig_lang = [r for r in lang_contrast if r.get("significant")] or lang_contrast[:8]
    sig_mis = [r for r in mis_by_loc if r.get("significant")] or mis_by_loc[:8]

    # , ,  Network payloads (Gephi + viz) , , 
    def nid(kind: str, name: str) -> str:
        return f"{kind}:{name}"

    co_nodes: list[dict] = []
    co_edges: list[dict] = []
    for lab, cnt in content_single.most_common():
        if lab == "other_unclear":
            continue
        co_nodes.append(
            {
                "id": nid("content", lab),
                "label": lab.replace("_", " "),
                "type": "content",
                "n": cnt,
            }
        )
    for lab, cnt in discourse_single.most_common():
        if lab == "other_mixed":
            continue
        co_nodes.append(
            {
                "id": nid("discourse", lab),
                "label": lab.replace("_", " "),
                "type": "discourse",
                "n": cnt,
            }
        )
    for r in clean_content_co[:30]:
        if r["lift"] < 1.35:
            continue
        co_edges.append(
            {
                "source": nid("content", r["a"]),
                "target": nid("content", r["b"]),
                "type": "content_cooccur",
                "n": r["n"],
                "lift": r["lift"],
                "phi": r["phi"],
                "odds_ratio": r.get("odds_ratio"),
                "p_holm": r.get("p_holm"),
                "significant": r.get("significant"),
                "stars": r.get("stars"),
            }
        )
    for r in clean_cross[:35]:
        if r["lift"] < 1.5:
            continue
        co_edges.append(
            {
                "source": nid("content", r["a"]),
                "target": nid("discourse", r["b"]),
                "type": "content_discourse",
                "n": r["n"],
                "lift": r["lift"],
                "odds_ratio": r.get("odds_ratio"),
                "p_holm": r.get("p_holm"),
                "significant": r.get("significant"),
                "stars": r.get("stars"),
            }
        )

    place_nodes: list[dict] = []
    place_edges: list[dict] = []
    used_countries: set[str] = set()
    used_labels: set[str] = set()
    for r in sig_distinctive[:45]:
        if r["label"] in {"institutional_news", "other_unclear"}:
            continue
        used_countries.add(r["location"])
        used_labels.add(r["label"])
        place_edges.append(
            {
                "source": nid("place", r["location"]),
                "target": nid("content", r["label"]),
                "type": "place_teaches",
                "n": r["hits"],
                "lift": r["lift_vs_geo_news"],
                "rate_pct": r["rate_pct"],
                "odds_ratio": r.get("odds_ratio"),
                "p_holm": r.get("p_holm"),
                "significant": r.get("significant"),
                "stars": r.get("stars"),
            }
        )
    for c in used_countries:
        place_nodes.append(
            {
                "id": nid("place", c),
                "label": c,
                "type": "place",
                "n": loc_n[c],
            }
        )
    for lab in used_labels:
        place_nodes.append(
            {
                "id": nid("content", lab),
                "label": lab.replace("_", " "),
                "type": "content",
                "n": content_single[lab],
            }
        )

    network = {
        "description": (
            "Jev informal-learning networks with Fisher exact tests + Holm–Bonferroni. "
            "(1) content↔content / content↔discourse co-occurrence; "
            "(2) ActionGeo place × content (country vs rest). Edges prefer p_holm<0.05."
        ),
        "stats": {
            "test": "Fisher exact (two-sided) on 2×2 presence tables",
            "multiple_testing": "Holm–Bonferroni within each contrast family",
            "alpha": ALPHA,
        },
        "n_judgments": n,
        "geo_with_fips": geo_with_fips,
        "types_together": {"nodes": co_nodes, "edges": co_edges},
        "place_x_type": {"nodes": place_nodes, "edges": place_edges},
    }

    inst_pct = round(100 * content_single.get("institutional_news", 0) / n, 1)
    doc_pct = round(100 * content_single.get("doctrine_sacrament", 0) / n, 1)
    mis_pct = round(100 * content_single.get("misunderstanding", 0) / n, 1)
    n_sig_pairs = sum(1 for r in content_co if r.get("significant"))
    n_sig_place = sum(1 for r in distinctive if r.get("significant"))

    def _hook_pair(r: dict) -> str:
        return (
            f"{pretty_label(r['a'])} × {pretty_label(r['b'])} "
            f"(lift {r['lift']}, OR {r.get('odds_ratio')}, "
            f"{r.get('stars') or 'ns'} Holm)"
        )

    def _hook_place(r: dict) -> str:
        return (
            f"{r['location']} · {pretty_label(r['label'])} "
            f"({r['lift_vs_geo_news']}×, OR {r.get('odds_ratio')}, {r.get('stars') or 'ns'})"
        )

    summary = {
        "source": str(args.path),
        "n_judgments": n,
        "geo_join_n": geo_join_n,
        "geo_with_fips": geo_with_fips,
        "stats": {
            "test": "Fisher exact (two-sided)",
            "multiple_testing": "Holm–Bonferroni within family",
            "alpha": ALPHA,
            "n_sig_content_pairs": n_sig_pairs,
            "n_sig_place_lifts": n_sig_place,
            "n_sig_lang_contrasts": sum(1 for r in lang_contrast if r.get("significant")),
        },
        "content_label_counts": dict(content_single.most_common()),
        "discourse_label_counts": dict(discourse_single.most_common()),
        "content_cooccur_top": content_co[:15],
        "content_cooccur_clean_top": clean_content_co[:15],
        "discourse_cooccur_top": discourse_co[:15],
        "content_x_discourse_top": cross_rows[:15],
        "content_x_discourse_clean_top": clean_cross[:15],
        "location_distinctive_top": sig_distinctive[:20],
        "language_contrast_en_vs_es": sig_lang[:12],
        "family_contrast_news_vs_radio": [
            r for r in fam_contrast if r.get("significant")
        ][:12]
        or fam_contrast[:12],
        "misunderstanding_by_location": sig_mis[:15],
        "languages": dict(lang_n),
        "families": dict(fam_n),
        "hooks": {
            "institutional_vs_doctrine": f"~{inst_pct}% institutional news vs ~{doc_pct}% doctrine",
            "misunderstanding_pct": mis_pct,
            "types_together": _hook_pair(clean_content_co[0]) if clean_content_co else "n/a",
            "place_hook": _hook_place(sig_distinctive[0]) if sig_distinctive else "n/a",
            "lang_hook": (
                f"EN {pretty_label(sig_lang[0]['label'])} {sig_lang[0]['rate_a_pct']}% vs "
                f"ES {sig_lang[0]['rate_b_pct']}% "
                f"(OR {sig_lang[0].get('odds_ratio')}, {sig_lang[0].get('stars')})"
                if sig_lang
                else "n/a"
            ),
            "stats_note": (
                f"Fisher + Holm; {n_sig_pairs} sig content pairs, "
                f"{n_sig_place} sig place×type edges (α={ALPHA})"
            ),
        },
        "education_flash": {
            "types_together": (
                f"Top content co-travel: {_hook_pair(clean_content_co[0])}"
                if clean_content_co
                else "n/a"
            ),
            "location_hook": (
                _hook_place(sig_distinctive[0]) if sig_distinctive else "n/a"
            ),
            "location_note": (
                f"News ActionGeo join {geo_with_fips}/{n}; "
                "TV/radio/YouTube use language/family rates, not ActionGeo. "
                "Associations: Fisher exact + Holm–Bonferroni."
            ),
        },
    }

    json_path = out_dir / f"{stem}_correlations.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    net_path = out_dir / f"{stem}_networks.json"
    net_path.write_text(json.dumps(network, indent=2) + "\n", encoding="utf-8")
    write_csv(out_dir / f"{stem}_label_cooccur.csv", cooccur_csv)
    write_csv(
        out_dir / f"{stem}_lang_x_type.csv",
        [{**r, "axis": "language"} for r in lang_x]
        + [{**r, "axis": "family"} for r in fam_x],
    )
    write_csv(out_dir / f"{stem}_location_x_type.csv", loc_rates + [
        {**r, "location": f"region:{r['location']}"} for r in region_rates
    ])
    write_csv(out_dir / f"{stem}_location_distinctive.csv", distinctive)
    write_csv(out_dir / f"{stem}_language_contrast.csv", lang_contrast)
    write_csv(out_dir / f"{stem}_family_contrast.csv", fam_contrast)
    write_csv(out_dir / f"{stem}_misunderstanding_by_location.csv", mis_by_loc)

    plots: list[str] = []
    if not args.no_plot:
        fig_dir.mkdir(parents=True, exist_ok=True)
        plots = maybe_plot(fig_dir, content_co, loc_rates, content_labs)

    def _rel(path: Path) -> str:
        path = path.resolve()
        try:
            return str(path.relative_to(ROOT.resolve()))
        except ValueError:
            return str(path)

    print(f"n={n} geo_joined={geo_join_n} with_fips={geo_with_fips}")
    print(
        f"stats: Fisher + Holm α={ALPHA} · "
        f"sig content pairs={summary['stats']['n_sig_content_pairs']} · "
        f"sig place lifts={summary['stats']['n_sig_place_lifts']}"
    )
    print("top content pairs (sig first):")
    for r in content_co[:8]:
        print(
            f"  {r['a']} × {r['b']}: n={r['n']} lift={r['lift']} "
            f"OR={r.get('odds_ratio')} p_holm={r.get('p_holm')} {r.get('stars')}"
        )
    print("top content×discourse:")
    for r in cross_rows[:6]:
        print(
            f"  {r['a']} × {r['b']}: n={r['n']} lift={r['lift']} "
            f"OR={r.get('odds_ratio')} {r.get('stars')}"
        )
    if sig_distinctive:
        print("top location lifts (sig):")
        for r in sig_distinctive[:8]:
            print(
                f"  {r['location']} · {r['label']}: "
                f"{r['rate_pct']}% (baseline {r['baseline_pct']}%) "
                f"lift={r['lift_vs_geo_news']} OR={r.get('odds_ratio')} {r.get('stars')}"
            )
    if sig_lang:
        print("EN vs ES contrasts (sig):")
        for r in sig_lang[:5]:
            print(
                f"  {r['label']}: EN {r['rate_a_pct']}% / ES {r['rate_b_pct']}% "
                f"OR={r.get('odds_ratio')} {r.get('stars')}"
            )
    if sig_mis:
        print("misunderstanding hotspots (sig):")
        for r in sig_mis[:5]:
            print(
                f"  {r['location']}: {r['misunderstanding_pct']}% "
                f"(baseline {r.get('baseline_pct')}%) OR={r.get('odds_ratio')} {r.get('stars')}"
            )
    print(f"wrote {_rel(json_path)}")
    print(f"wrote {_rel(net_path)}")
    for name in (
        f"{stem}_label_cooccur.csv",
        f"{stem}_lang_x_type.csv",
        f"{stem}_location_x_type.csv",
        f"{stem}_location_distinctive.csv",
        f"{stem}_language_contrast.csv",
        f"{stem}_family_contrast.csv",
        f"{stem}_misunderstanding_by_location.csv",
    ):
        print(f"wrote {_rel(out_dir / name)}")
    for pl in plots:
        print(f"wrote {_rel(Path(pl))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
