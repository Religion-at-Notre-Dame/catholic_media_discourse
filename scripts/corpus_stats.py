#!/usr/bin/env python3
"""Print row counts for raw and anonymized corpus files (with progress bars)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from common.analysis_paths import SOURCE_FAMILY, analysis_source_paths, count_source
from common.progress import count_glob_rows, count_jsonl_rows, print_table, section


def main() -> None:
    p = argparse.ArgumentParser(description="Corpus row counts with progress bars.")
    p.add_argument("--quiet", "-q", action="store_true", help="Skip progress bars while counting.")
    args = p.parse_args()

    root = Path("data/us")
    am = Path("data/americas")
    paths = analysis_source_paths()

    if not args.quiet:
        section("Corpus stats")

    table_rows: list[tuple[str, int]] = []
    for key, value in paths.items():
        fam = SOURCE_FAMILY.get(key, key)
        rows, paras, _years = count_source(value, desc=f"{key}")
        table_rows.append((f"{key} ({fam}) rows", rows))
        table_rows.append((f"{key} ({fam}) paragraphs", paras))

    table_rows.extend(
        [
            ("GDELT news US classified", count_glob_rows(str(root / "news/classified/classified_part_*.jsonl"))),
            ("GDELT news US anonymized", count_glob_rows(str(root / "news/anonymized/anonymized_part_*.jsonl"))),
            (
                "GDELT news US unified corpus",
                count_jsonl_rows(
                    Path("data/us/news/gdelt_us_paragraphs_20150101_20260630.jsonl"),
                    desc="us_corpus",
                )
                if Path("data/us/news/gdelt_us_paragraphs_20150101_20260630.jsonl").exists()
                else 0,
            ),
            (
                "GDELT news Americas unified corpus",
                count_jsonl_rows(
                    Path("data/americas/news/gdelt_americas_paragraphs_20150101_20260630.jsonl"),
                    desc="am_corpus",
                )
                if Path("data/americas/news/gdelt_americas_paragraphs_20150101_20260630.jsonl").exists()
                else 0,
            ),
            ("GDELT TV anonymized", count_glob_rows(str(root / "tv/anonymized/anonymized_part_*.jsonl"))),
            ("YouTube US anonymized", count_glob_rows(str(root / "youtube/anonymized/anonymized_part_*.jsonl"))),
            ("Americas news anonymized", count_glob_rows(str(am / "news/anonymized/anonymized_part_*.jsonl"))),
            ("Americas radio anonymized", count_glob_rows(str(am / "radio/anonymized/anonymized_part_*.jsonl"))),
            ("Americas YouTube anonymized", count_glob_rows(str(am / "youtube/anonymized/anonymized_part_*.jsonl"))),
            ("Network nodes", count_jsonl_rows(root / "network/nodes.jsonl", desc="nodes")),
            ("Network edges", count_jsonl_rows(root / "network/edges.jsonl", desc="edges")),
            (
                "Discourse country×teaching edges",
                count_jsonl_rows(Path("data/network/country_teaching/edges.jsonl"), desc="ct-edges"),
            ),
            (
                "Discourse GDELT actor edges",
                count_jsonl_rows(Path("data/network/gdelt_actors/edges.jsonl"), desc="actor-edges"),
            ),
        ]
    )

    print_table(table_rows)


if __name__ == "__main__":
    main()
