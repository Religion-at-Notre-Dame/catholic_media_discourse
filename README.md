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
| `viz/` | ND site: Story · Findings · Places · Topics · Methods (`bash viz/tools/check.sh`) |

**No** raw `*_paragraphs_*.jsonl`, fetch shards, API keys, or collector launchers.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "import spacy; spacy.cli.download('en_core_web_sm'); spacy.cli.download('es_core_news_sm')"
```

## Start the website

```bash
python3 viz/serve.py
```

Then open **http://127.0.0.1:8765/pages/index.html** in your browser.

Optional flags:

```bash
python3 viz/serve.py --port 8765
python3 viz/serve.py --no-browser   # print URL only
```

Refresh map data from anonymized JSONL (when needed):

```bash
python3 viz/tools/export_map_network.py --use-cache
python3 viz/tools/export_viz_extras.py --use-cache
```

## Corpus stats

```bash
python3 scripts/corpus_stats.py --quiet
```

## Sync anonymized data from Data

```bash
cd ../catholic_media_data
bash scripts/sync_anonymized_to_discourse.sh
```

## Corpus period

GDELT news paragraphs: **2015-01-01 → 2026-06-30** (U.S. + non-U.S. Americas), plus TV / radio / YouTube.
