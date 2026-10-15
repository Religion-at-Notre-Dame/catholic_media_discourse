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
| `scripts/common/` | Themes, geography, stratified sample, Jev path helpers |
| `scripts/judge/` | Dual-taxonomy Jev pipeline (OpenRouter), QC, correlations |
| `scripts/paper/` | **Tracked** paper figure/table generators (`papers/` is gitignored) |
| `scripts/build_*.py` | Network rebuild from anonymized inputs |
| `viz/` | ND site: Story · Findings · Triage · Places · Topics · Methods |

**No** raw `*_paragraphs_*.jsonl`, fetch shards, API keys, or collector launchers.

`papers/` is local-only (LaTeX, PDFs, large Jev JSONL). Generators that rebuild those artifacts live in `scripts/paper/`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "import spacy; spacy.cli.download('en_core_web_sm'); spacy.cli.download('es_core_news_sm')"
```

## Start the website

```bash
python3 viz/serve.py
# rebuild Story/Findings/Triage snapshots then serve:
python3 viz/serve.py --verify --build-findings
```

Then open **http://127.0.0.1:8765/pages/index.html** in your browser.

```bash
bash viz/tools/check.sh          # findings + triage + verify
python3 viz/serve.py --port 8765
python3 viz/serve.py --no-browser
```

## Public site (GitHub Pages)

This repo is **public**. The classroom site deploys from `viz/` via [`.github/workflows/pages.yml`](.github/workflows/pages.yml).

| URL | Host |
|-----|------|
| [religion-at-notre-dame.github.io/catholic_media_discourse](https://religion-at-notre-dame.github.io/catholic_media_discourse/) | This repo (GitHub Pages) |
| [jonathankarr.com/how_the_americas_hear_the_church](https://jonathankarr.com/how_the_americas_hear_the_church/) | Personal site mirror (optional) |

**First-time setup** (once): GitHub → **Settings → Pages → Source: GitHub Actions**. Then push to `main` (or run the workflow manually). Site root is the staged `viz/` payload (no `tools/`).

**Optional personal-site mirror** (same static files under your CNAME):

```bash
bash viz/tools/publish_personal_site.sh
# then commit/push in JonathanKarr33.github.io
```

Refresh map data from anonymized JSONL (when needed):

```bash
python3 viz/tools/export_map_network.py --use-cache
python3 viz/tools/export_viz_extras.py --use-cache
python3 viz/tools/build_findings_data.py
python3 viz/tools/build_triage_data.py
```

## Education track (Jev + paper figures)

```bash
# Correlations / networks (after a live or fixture Jev run)
python3 scripts/judge/analyze_jev_correlations.py

# Slide-ready paper figures → papers/rise_education_2026/figures/
MPLCONFIGDIR=/tmp/mpl python3 scripts/paper/plot_jev_paper_figures.py
python3 scripts/paper/generate_results_corpus_table.py

# Full paper PDF (local; requires TeX under papers/)
bash papers/rise_education_2026/build_main.sh
bash papers/rise_education_2026/build_abstract.sh
```

See [`scripts/paper/README.md`](scripts/paper/README.md) and [`scripts/judge/README.md`](scripts/judge/README.md).

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
