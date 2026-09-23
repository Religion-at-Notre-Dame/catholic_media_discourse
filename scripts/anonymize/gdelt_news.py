"""Anonymize GDELT US news paragraphs."""

import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import argparse
import os

from common.anonymize import add_standard_cli, iter_classified_news, run_field_anonymize


DEFAULT_INPUT = os.path.join("data", "us", "news", "classified")
DEFAULT_OUTPUT = os.path.join("data", "us", "news", "anonymized")
FIELDS = [("paragraph_text", "paragraph_text_deidentified")]


def main() -> None:
    p = argparse.ArgumentParser(description="Anonymize GDELT US news paragraphs.")
    p.add_argument("--input", "-i", default=DEFAULT_INPUT)
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT)
    p.add_argument(
        "--fallback-language",
        choices=["english", "spanish", "portuguese"],
        default="english",
    )
    add_standard_cli(p)
    args = p.parse_args()
    run_field_anonymize(
        args,
        field_pairs=FIELDS,
        require_any=("paragraph_text",),
        source="gdelt_news",
        progress_desc="Anonymizing paragraphs",
        progress_unit="para",
        language_field="language",
        fallback_language=args.fallback_language,
        record_iter=iter_classified_news,
        checkpoint_extra={"fallback_language": args.fallback_language},
    )


if __name__ == "__main__":
    main()

