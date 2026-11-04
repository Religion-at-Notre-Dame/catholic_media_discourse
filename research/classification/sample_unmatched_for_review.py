#!/usr/bin/env python3
"""Create a reproducible multilingual review sample from unmatched paragraphs."""

from __future__ import annotations

import csv
import random
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
INPUT_PATH = HERE / "preliminary_news_classification.csv"
OUTPUT_PATH = HERE / "unmatched_review_sample.csv"
SEED = 20261014
QUOTAS = {"english": 70, "spanish": 15, "portuguese": 15}

OUTPUT_COLUMNS = (
    "review_id",
    "sample_id",
    "language",
    "source_scope",
    "date",
    "paragraph_index",
    "text",
    "exploratory_category",
    "exploratory_notes",
)


def main() -> None:
    with INPUT_PATH.open(encoding="utf-8", newline="") as handle:
        unmatched = [
            row for row in csv.DictReader(handle) if row["unmatched"] == "True"
        ]

    pools: dict[str, list[dict]] = {
        language: [] for language in QUOTAS
    }
    for row in unmatched:
        if row["language"] in pools:
            pools[row["language"]].append(row)

    available = Counter(row["language"] for row in unmatched)
    shortfalls = {
        language: quota - available[language]
        for language, quota in QUOTAS.items()
        if available[language] < quota
    }
    if shortfalls:
        raise RuntimeError(f"Insufficient unmatched records: {shortfalls}")

    selected: list[dict] = []
    for language, quota in QUOTAS.items():
        rng = random.Random(f"{SEED}:{language}")
        selected.extend(rng.sample(pools[language], quota))
    random.Random(SEED).shuffle(selected)

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for index, row in enumerate(selected, start=1):
            writer.writerow(
                {
                    "review_id": f"UM-{index:03d}",
                    "sample_id": row["sample_id"],
                    "language": row["language"],
                    "source_scope": row["source_scope"],
                    "date": row["date"],
                    "paragraph_index": row["paragraph_index"],
                    "text": row["text"],
                    "exploratory_category": "",
                    "exploratory_notes": "",
                }
            )

    print(f"Wrote {len(selected)} rows to {OUTPUT_PATH}")
    print(f"Language quotas: {QUOTAS}")


if __name__ == "__main__":
    main()
