# Paper figure & table generators (tracked)

`papers/` is **gitignored** (local LaTeX: `.tex`, `.pdf`, aux files, large analysis JSONL).
Reusable plotting / table code lives here so it stays in git.

| Script | Writes |
|--------|--------|
| [`plot_jev_paper_figures.py`](plot_jev_paper_figures.py) | `papers/rise_education_2026/figures/jev_*.{png,pdf}`, `country_teaching_*.{png,pdf}`, `sections/jev_education_brief.tex` |
| [`generate_results_corpus_table.py`](generate_results_corpus_table.py) | `papers/rise_education_2026/sections/results_corpus_table.tex` |
| [`plot_jev_education_fixture.py`](plot_jev_education_fixture.py) | fixture bar charts under `papers/.../figures/` |

```bash
# From repo root
MPLCONFIGDIR=/tmp/mpl python3 scripts/paper/plot_jev_paper_figures.py
python3 scripts/paper/generate_results_corpus_table.py

# Or via the paper build wrapper (still local under papers/)
bash papers/rise_education_2026/build_main.sh
```

Inputs (still under gitignored `papers/.../analysis/` or tracked `data/` / `viz/`):

- `papers/rise_education_2026/analysis/jev_judgments/*.summary.json`, `*_correlations.json`
- `papers/rise_education_2026/analysis/collection_geography_stats.json`
- `viz/data/findings-data.js`, `data/network/country_teaching/edges.jsonl`

**`jev_education_brief.tex` ownership:** `plot_jev_paper_figures.py` is the live
pilot writer. Do not overwrite it with
`summarize_jev_judgments.py --write-tex` unless you intend a fixture brief.
