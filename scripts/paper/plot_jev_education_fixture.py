#!/usr/bin/env python3
"""Bar chart of dual-taxonomy fixture counts for Research Station / results.

  python3 scripts/paper/plot_jev_education_fixture.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from common.label_pretty import pretty_label as pretty  # noqa: E402

PAPER = REPO / "papers/rise_education_2026"
FIX = PAPER / "analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl"
OUT_PNG = PAPER / "figures/jev_education_fixture.png"
OUT_PDF = PAPER / "figures/jev_education_fixture.pdf"


def main() -> int:
    if not FIX.exists():
        raise SystemExit(f"missing fixture {FIX}")
    content: Counter[str] = Counter()
    discourse: Counter[str] = Counter()
    with FIX.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            for x in rec.get("content_labels") or []:
                content[str(x)] += 1
            for x in rec.get("discourse_labels") or []:
                discourse[str(x)] += 1

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    for ax, ctr, title, color in (
        (axes[0], content, "Content labels (fixture)", "#2c5f4a"),
        (axes[1], discourse, "Discourse labels (fixture)", "#3d4f6f"),
    ):
        items = ctr.most_common(8)
        labels = [pretty(k) for k, _ in items][::-1]
        vals = [v for _, v in items][::-1]
        ax.barh(labels, vals, color=color)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("count")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(
        "Education-track dual taxonomy: offline EN/ES/PT fixture (not Theology gold)",
        fontsize=12,
    )
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=160)
    fig.savefig(OUT_PDF)
    print(f"wrote {OUT_PNG.relative_to(REPO)}")
    print(f"wrote {OUT_PDF.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
