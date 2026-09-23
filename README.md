# Catholic Media — Discourse

Anonymized multimodal corpus, discourse networks, analysis scripts, and interactive classroom viz for the Americas Catholic media project (**2015–Q2 2026**).

Raw GDELT/API collection lives in:

[`../catholic_media_data`](../catholic_media_data)

## What’s included

| Path | Contents |
|------|----------|
| `data/*/…/anonymized/` | De-identified JSONL (news, TV, radio, YouTube) |
| `data/network/` | Discourse graphs (country×teaching, actors, bridges, …) |
| `data/us/network/` | Affiliation graph |
| `scripts/common/` | Themes, geography, stratified sample, path helpers |
| `scripts/build_*.py` | Network rebuild from anonymized inputs |
| `papers/` | Local paper / LaTeX / viz sources (**gitignored**) |

**No** raw `*_paragraphs_*.jsonl`, fetch shards, API keys, or collector launchers.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "import spacy; spacy.cli.download('en_core_web_sm'); spacy.cli.download('es_core_news_sm')"

python3 scripts/corpus_stats.py --quiet
python3 papers/rise_education_2026/viz/serve.py   # if papers/ present locally
```

Open **http://127.0.0.1:8765/index.html**

## Analysis (local `papers/` tree)

```bash
./papers/rise_education_2026/analysis/run_extended_analysis.sh --skip-corpus --resume
python3 papers/rise_education_2026/analysis/print_extended_brief.py
cd papers/rise_education_2026 && pdflatex main.tex
```

## Sync anonymized data from Data

```bash
cd ../catholic_media_data
bash scripts/sync_anonymized_to_discourse.sh
```

## Corpus period

GDELT news paragraphs: **2015-01-01 → 2026-06-30** (U.S. + non-U.S. Americas), plus TV / radio / YouTube.
