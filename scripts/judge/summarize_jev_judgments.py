#!/usr/bin/env python3
"""Summarize dual-taxonomy Jev JSONL for Education-track slides / QC.

  python3 scripts/judge/summarize_jev_judgments.py \\
    papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl \\
    --write-json papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_summary.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from glob import glob
from pathlib import Path


def expand_paths(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        hits = sorted(glob(pat))
        if hits:
            out.extend(Path(h) for h in hits)
        elif Path(pat).exists():
            out.append(Path(pat))
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in out:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="+", help="JSONL paths or globs")
    p.add_argument("--top", type=int, default=12)
    p.add_argument("--json", action="store_true", help="Print JSON to stdout")
    p.add_argument("--write-json", type=Path, default=None)
    p.add_argument("--write-tex", type=Path, default=None, help="Optional short TeX snippet")
    args = p.parse_args()

    paths = expand_paths(args.paths)
    if not paths:
        raise SystemExit("No input files matched")

    n = 0
    err = 0
    cost = 0.0
    langs: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    content: Counter[str] = Counter()
    discourse: Counter[str] = Counter()
    review = 0
    misunderstanding = 0
    acc_scores: list[float] = []
    acc_by_lang: dict[str, list[float]] = defaultdict(list)
    cross: Counter[str] = Counter()

    for path in paths:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("error"):
                    err += 1
                    continue
                n += 1
                lang = rec.get("language") or "?"
                langs[lang] += 1
                sources[rec.get("source") or "?"] += 1
                clabs = list(rec.get("content_labels") or [])
                dlabs = list(rec.get("discourse_labels") or [])
                for lab in clabs:
                    content[str(lab)] += 1
                for lab in dlabs:
                    discourse[str(lab)] += 1
                if "misunderstanding" in clabs:
                    misunderstanding += 1
                if rec.get("needs_human_review"):
                    review += 1
                if rec.get("accuracy_score") is not None:
                    try:
                        s = float(rec["accuracy_score"])
                        acc_scores.append(s)
                        acc_by_lang[lang].append(s)
                    except (TypeError, ValueError):
                        pass
                for c in clabs[:4]:
                    for d in dlabs[:4]:
                        cross[f"{c}×{d}"] += 1
                usage = rec.get("usage") or {}
                try:
                    cost += float(usage.get("cost") or 0)
                except (TypeError, ValueError):
                    pass

    summary = {
        "files": [str(p) for p in paths],
        "rows_ok": n,
        "errors": err,
        "cost_usd": round(cost, 6),
        "needs_human_review": review,
        "misunderstanding_n": misunderstanding,
        "misunderstanding_rate": (misunderstanding / n) if n else None,
        "accuracy_mean": (sum(acc_scores) / len(acc_scores)) if acc_scores else None,
        "accuracy_n": len(acc_scores),
        "accuracy_mean_by_language": {
            k: (sum(v) / len(v) if v else None) for k, v in sorted(acc_by_lang.items())
        },
        "languages": dict(langs.most_common()),
        "sources": dict(sources.most_common(args.top)),
        "content_labels": dict(content.most_common(args.top)),
        "discourse_labels": dict(discourse.most_common(args.top)),
        "content_x_discourse_top": dict(cross.most_common(args.top)),
        "education_flash": {
            "prior_knowledge_note": (
                "Content labels approximate what learners may already 'know' from media "
                "before OCIA/parish formation."
            ),
            "review_queue_note": (
                f"{review} rows flagged needs_human_review; "
                f"{misunderstanding} carry misunderstanding."
            ),
        },
    }

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.write_json}")

    if args.write_tex:
        lines = [
            "% Auto-generated Jev education-layer brief — do not hand-edit.",
            f"Fixture/pilot rows: {n}. "
            f"Misunderstanding rate: {(summary['misunderstanding_rate'] or 0)*100:.0f}\\%. "
            f"Human-review flags: {review}.",
        ]
        if summary["accuracy_mean"] is not None:
            lines.append(f"Mean accuracy triage score: {summary['accuracy_mean']:.2f} (0--4 scale).")
        args.write_tex.parent.mkdir(parents=True, exist_ok=True)
        args.write_tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {args.write_tex}")

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"rows_ok={n} errors={err} cost≈${cost:.4f} "
            f"needs_human_review={review} misunderstanding={misunderstanding}"
        )
        if acc_scores:
            print(f"accuracy_score mean={summary['accuracy_mean']:.3f} n={len(acc_scores)}")
            print("accuracy_by_language:", summary["accuracy_mean_by_language"])
        print("languages:", summary["languages"])
        print("content_labels:", summary["content_labels"])
        print("discourse_labels:", summary["discourse_labels"])
        print("content×discourse:", summary["content_x_discourse_top"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
