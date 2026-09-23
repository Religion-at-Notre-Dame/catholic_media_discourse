"""Anonymize Spotify podcast rows."""

import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import argparse
import os

from common.anonymize import add_standard_cli, run_field_anonymize


DEFAULT_INPUT = os.path.join("data", "us", "spotify", "spotify_us_2015-01-01_to_2025-12-31.jsonl")
DEFAULT_OUTPUT = os.path.join("data", "us", "spotify", "anonymized")
FIELDS = [
    ("name", "name_deidentified"),
    ("description", "description_deidentified"),
    ("html_description", "html_description_deidentified"),
]


def main() -> None:
    p = argparse.ArgumentParser(description="Anonymize Spotify podcast JSONL.")
    p.add_argument("--input", "-i", default=DEFAULT_INPUT)
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT)
    add_standard_cli(p)
    run_field_anonymize(
        p.parse_args(),
        field_pairs=FIELDS,
        require_any=("name", "description"),
        source="spotify",
        progress_desc="Anonymizing Spotify",
        language_field="keyword_language",
    )


if __name__ == "__main__":
    main()

