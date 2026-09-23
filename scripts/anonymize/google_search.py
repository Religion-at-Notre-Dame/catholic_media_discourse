"""Anonymize Google Search web results."""

import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import argparse
import os

from common.anonymize import add_standard_cli, run_field_anonymize


DEFAULT_INPUT = os.path.join("data", "us", "google_search", "google_search_us_2015-01-01_to_2025-12-31.jsonl")
DEFAULT_OUTPUT = os.path.join("data", "us", "google_search", "anonymized")
FIELDS = [
    ("title", "title_deidentified"),
    ("snippet", "snippet_deidentified"),
]


def main() -> None:
    p = argparse.ArgumentParser(description="Anonymize Google Search JSONL.")
    p.add_argument("--input", "-i", default=DEFAULT_INPUT)
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT)
    add_standard_cli(p)
    run_field_anonymize(
        p.parse_args(),
        field_pairs=FIELDS,
        require_any=("title", "snippet"),
        source="google_search",
        progress_desc="Anonymizing Google Search",
        language_field="search_language",
    )


if __name__ == "__main__":
    main()

