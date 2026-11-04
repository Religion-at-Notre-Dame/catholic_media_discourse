#!/usr/bin/env python3
"""Run a reproducible, regex-based speech-act experiment on anonymized news.

These labels are heuristic surface cues, not verified human classifications.
The language-enriched sample is intended to exercise multilingual rules and is
not representative of the corpus-wide language distribution.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator

os.environ.setdefault("MPLCONFIGDIR", "/tmp/catholic-media-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from common.content_acts import discourse_modes, primary_discourse


SEED = 20261014
DEFAULT_QUOTAS = {"english": 700, "spanish": 274, "portuguese": 26}
MODE_COLUMNS = (
    "question",
    "reporting",
    "opinion",
    "advocacy",
    "devotional",
    "factish_markers",
)
CSV_COLUMNS = (
    "sample_id",
    "source_scope",
    "source_file",
    "source_line",
    "source",
    "article_id",
    "event_id",
    "date",
    "gdelt_day",
    "paragraph_index",
    "language",
    "text",
    *MODE_COLUMNS,
    "unmatched",
    "labels",
    "label_count",
    "primary_discourse",
    "method",
    "verified_human_label",
)


def news_paths(root: Path) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    for scope, directory in (
        ("us", root / "data/us/news/anonymized"),
        ("americas", root / "data/americas/news/anonymized"),
    ):
        paths.extend(
            (scope, path)
            for path in sorted(directory.glob("anonymized_part_*.jsonl"))
        )
    if not paths:
        raise FileNotFoundError("No anonymized news JSONL shards were found.")
    return paths


def iter_news(root: Path) -> Iterator[dict]:
    for scope, path in news_paths(root):
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = record.get("paragraph_text")
                if not isinstance(text, str) or not text.strip():
                    continue
                yield {
                    "source_scope": scope,
                    "source_file": str(path.relative_to(root)),
                    "source_line": line_number,
                    "record": record,
                    "text": text,
                }


def stratified_reservoir_sample(
    root: Path, quotas: dict[str, int], seed: int
) -> tuple[list[dict], Counter]:
    """Sample each declared language deterministically in one corpus scan."""
    pools: dict[str, list[dict]] = {language: [] for language in quotas}
    available: Counter = Counter()
    rng = {
        language: random.Random(f"{seed}:{language}") for language in quotas
    }

    for item in iter_news(root):
        language = str(item["record"].get("language") or "").lower().strip()
        if language not in quotas:
            continue
        available[language] += 1
        pool = pools[language]
        quota = quotas[language]
        if len(pool) < quota:
            pool.append(item)
            continue
        replacement = rng[language].randint(1, available[language])
        if replacement <= quota:
            pool[replacement - 1] = item

    shortfalls = {
        language: quotas[language] - len(pools[language])
        for language in quotas
        if len(pools[language]) < quotas[language]
    }
    if shortfalls:
        raise RuntimeError(f"Insufficient records for requested quotas: {shortfalls}")

    sample: list[dict] = []
    for language in quotas:
        sample.extend(pools[language])
    random.Random(seed).shuffle(sample)
    return sample, available


def classify_sample(sample: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for index, item in enumerate(sample, start=1):
        record = item["record"]
        text = item["text"]
        modes = discourse_modes(text)
        labels = [label for label in MODE_COLUMNS if modes[label]]
        unmatched = not labels
        rows.append(
            {
                "sample_id": f"CMD-{index:04d}",
                "source_scope": item["source_scope"],
                "source_file": item["source_file"],
                "source_line": item["source_line"],
                "source": record.get("source", ""),
                "article_id": record.get("article_id", ""),
                "event_id": record.get("event_id", ""),
                "date": record.get("date", ""),
                "gdelt_day": record.get("gdelt_day", ""),
                "paragraph_index": record.get("paragraph_index", ""),
                "language": str(record.get("language") or "").lower().strip(),
                "text": text,
                **{label: modes[label] for label in MODE_COLUMNS},
                "unmatched": unmatched,
                "labels": ";".join(labels) if labels else "unmatched",
                "label_count": len(labels),
                "primary_discourse": primary_discourse(modes),
                "method": "preliminary_regex_surface_cues",
                "verified_human_label": False,
            }
        )
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def category_counts(rows: list[dict]) -> dict[str, int]:
    categories = (*MODE_COLUMNS, "unmatched")
    return {
        category: sum(bool(row[category]) for row in rows)
        for category in categories
    }


def write_chart(counts: dict[str, int], sample_size: int, path: Path) -> None:
    labels = [
        "Question",
        "Reporting",
        "Opinion",
        "Advocacy",
        "Devotional",
        "Factish markers",
        "Unmatched",
    ]
    values = list(counts.values())
    colors = ["#0c2340"] * 6 + ["#8c8c8c"]

    fig, axis = plt.subplots(figsize=(11, 6.5))
    bars = axis.bar(labels, values, color=colors)
    axis.set_title(
        "Preliminary regex speech-act labels in a language-enriched news sample",
        pad=18,
    )
    axis.set_ylabel(f"Paragraphs (n={sample_size}; multi-label)")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    axis.tick_params(axis="x", rotation=25)

    for bar, value in zip(bars, values):
        percent = 100 * value / sample_size
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + max(values) * 0.015,
            f"{value}\n({percent:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    axis.text(
        0,
        -0.25,
        "Heuristic surface cues only; categories can overlap; not human-verified.",
        transform=axis.transAxes,
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_summary(
    rows: list[dict],
    counts: dict[str, int],
    available: Counter,
    quotas: dict[str, int],
    csv_path: Path,
    chart_path: Path,
    summary_path: Path,
    seed: int,
) -> None:
    sample_size = len(rows)
    summary = {
        "experiment": "preliminary_regex_speech_act_classification",
        "limitation": (
            "Heuristic regex-based surface cues; labels overlap and have not "
            "been verified by human annotators."
        ),
        "sampling_note": (
            "Language-enriched stratified sample; percentages are sample "
            "descriptives and are not corpus prevalence estimates."
        ),
        "seed": seed,
        "sample_size": sample_size,
        "requested_language_quotas": quotas,
        "available_news_records_by_sampled_language": dict(available),
        "sample_language_counts": dict(Counter(row["language"] for row in rows)),
        "category_counts": counts,
        "category_percentages": {
            category: round(100 * count / sample_size, 1)
            for category, count in counts.items()
        },
        "multi_label_records": sum(row["label_count"] > 1 for row in rows),
        "csv": str(csv_path.relative_to(ROOT)),
        "chart": str(chart_path.relative_to(ROOT)),
    }
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--english", type=int, default=DEFAULT_QUOTAS["english"])
    parser.add_argument("--spanish", type=int, default=DEFAULT_QUOTAS["spanish"])
    parser.add_argument(
        "--portuguese", type=int, default=DEFAULT_QUOTAS["portuguese"]
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    quotas = {
        "english": args.english,
        "spanish": args.spanish,
        "portuguese": args.portuguese,
    }
    output_dir = Path(__file__).resolve().parent
    csv_path = output_dir / "preliminary_news_classification.csv"
    chart_path = output_dir / "preliminary_category_frequencies.png"
    summary_path = output_dir / "preliminary_summary.json"

    sample, available = stratified_reservoir_sample(ROOT, quotas, args.seed)
    rows = classify_sample(sample)
    counts = category_counts(rows)
    write_csv(rows, csv_path)
    write_chart(counts, len(rows), chart_path)
    write_summary(
        rows,
        counts,
        available,
        quotas,
        csv_path,
        chart_path,
        summary_path,
        args.seed,
    )

    print(f"Wrote {len(rows):,} rows to {csv_path.relative_to(ROOT)}")
    print(f"Wrote chart to {chart_path.relative_to(ROOT)}")
    print(f"Wrote summary to {summary_path.relative_to(ROOT)}")
    for category, count in counts.items():
        print(f"{category}: {count:,} ({100 * count / len(rows):.1f}%)")


if __name__ == "__main__":
    main()
