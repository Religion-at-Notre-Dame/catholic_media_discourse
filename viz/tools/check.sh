#!/usr/bin/env bash
# One-shot classroom site check: regenerate findings snapshot + verify.
set -euo pipefail
cd "$(dirname "$0")"
echo "== build findings-data =="
python3 build_findings_data.py
echo "== export lexicon CSV =="
python3 export_lexicon_csv.py
echo "== verify site =="
python3 verify_site.py
echo "OK"
