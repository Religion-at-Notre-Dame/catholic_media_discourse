"""Anonymize AAPB US public radio rows (title + description)."""

import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import argparse
import os

from common.anonymize import add_standard_cli, run_field_anonymize_passes


DEFAULT_ENGLISH_INPUT = os.path.join("data", "us", "english", "radio", "aapb_us_2015-01-01_to_2025-12-31.jsonl")
DEFAULT_SPANISH_INPUT = os.path.join("data", "us", "spanish", "radio", "aapb_us_2015-01-01_to_2025-12-31.jsonl")
DEFAULT_ENGLISH_OUTPUT = os.path.join("data", "us", "english", "radio", "anonymized")
DEFAULT_SPANISH_OUTPUT = os.path.join("data", "us", "spanish", "radio", "anonymized")
FIELDS = [("title", "title_deidentified"), ("description", "description_deidentified")]


def main() -> None:
    p = argparse.ArgumentParser(description="Anonymize AAPB radio JSONL.")
    p.add_argument("--language", choices=["english", "spanish", "both"], default="both")
    p.add_argument("--input-english", default=DEFAULT_ENGLISH_INPUT)
    p.add_argument("--input-spanish", default=DEFAULT_SPANISH_INPUT)
    p.add_argument("--output-english", default=DEFAULT_ENGLISH_OUTPUT)
    p.add_argument("--output-spanish", default=DEFAULT_SPANISH_OUTPUT)
    add_standard_cli(p)
    args = p.parse_args()

    specs = {
        "english": (args.input_english, args.output_english, "english"),
        "spanish": (args.input_spanish, args.output_spanish, "spanish"),
    }
    languages = ["english", "spanish"] if args.language == "both" else [args.language]
    passes = []
    for lang in languages:
        input_path, output_dir, fallback = specs[lang]
        passes.append(
            {
                "input": input_path,
                "output_dir": output_dir,
                "source": "aapb",
                "language_field": "language",
                "fallback_language": fallback,
                "progress_desc": f"Anonymizing radio ({fallback})",
                "checkpoint_extra": {"fallback_language": fallback},
            }
        )

    run_field_anonymize_passes(
        args,
        passes=passes,
        field_pairs=FIELDS,
        require_any=("title", "description"),
    )


if __name__ == "__main__":
    main()
