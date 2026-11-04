# Jev judge pipeline (Education track)

Dual taxonomies + stratified sampling + USD budget cap via OpenRouter Decisions API (`typesafe/jev-1.13`).

| Taxonomy | File | Role |
|----------|------|------|
| Content | `papers/rise_education_2026/taxonomy/informal_learning_v0.yaml` | What prior teaching learners may absorb + accuracy score |
| Discourse | `papers/rise_education_2026/taxonomy/discourse_acts_v0.yaml` | How the passage speaks (claim, question, report, …) |

## Setup

```bash
cp .env.example .env   # set OPENROUTER_API_KEY for live pilots only
```

## Offline first (no API)

```bash
python3 scripts/judge/run_jev_pipeline.py --self-test
python3 scripts/judge/validate_jev_jsonl.py \
  papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl
python3 scripts/judge/export_jev_qc_sheet.py
python3 scripts/judge/export_a5_classroom_csv.py
python3 scripts/judge/export_formation_subset.py   # live formation CSV + Sidney priority QC
python3 scripts/judge/analyze_jev_correlations.py  # co-occurrence + ActionGeo×type + networks
python3 viz/tools/build_triage_data.py            # → viz Triage page
python3 scripts/judge/summarize_jev_judgments.py \
  papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl \
  --write-json papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_summary.json \
  --write-tex papers/rise_education_2026/sections/jev_education_brief.tex
python3 scripts/judge/score_jev_qc.py \
  papers/rise_education_2026/analysis/jev_judgments/qc_sheet.csv
python3 scripts/paper/plot_jev_education_fixture.py
python3 scripts/paper/plot_jev_paper_figures.py
```

## Live pilot (needs key)

```bash
python3 scripts/judge/run_jev_pipeline.py --dry-run --total 2000 --budget-usd 7
python3 scripts/judge/run_jev_pipeline.py --total 500 --budget-usd 1 --workers 8
python3 scripts/judge/run_jev_pipeline.py --total 40000 --budget-usd 7 --workers 8
python3 scripts/judge/run_jev_pipeline.py --resume path/to/jev_dual_….jsonl --budget-usd 7 --workers 8
python3 scripts/judge/run_jev_pipeline.py --no-discourse --total 80000 --budget-usd 7 --workers 8
```

Outputs in `papers/rise_education_2026/analysis/jev_judgments/`:
- `*.jsonl` — incremental judgments (flushed every row)
- `*.cost.json` — `spent_usd` / `remaining_usd` / `budget_usd` (resume-safe)
- `*.meta.json` / `*.summary.json`
- `qc_sheet.csv` — Sidney/Theology worksheet (`export_jev_qc_sheet.py`)
- `fixtures/` — offline EN/ES/PT demo + `demo_summary.json`
