# Preliminary speech-act classification

This experiment applies the existing regex rules in
`scripts/common/content_acts.py` to a reproducible sample of 1,000 anonymized
news paragraphs.

## Important limitation

These labels are **preliminary heuristic surface cues, not verified human
classifications**. A regex match does not establish that a paragraph truly
performs the corresponding speech act. Categories may overlap, and unmatched
records are retained.

The sample is intentionally language-enriched to exercise multilingual rules:

- 700 English-tagged paragraphs
- 274 Spanish-tagged paragraphs
- all 26 Portuguese-tagged paragraphs available in the current news corpus

Because this differs substantially from the corpus language distribution,
reported percentages describe only this sample and must not be interpreted as
corpus-wide prevalence estimates. Language tags inherited from the source data
may themselves be noisy.

## Reproduce

From the repository root:

```bash
python3 research/classification/run_preliminary_experiment.py
```

The fixed default random seed is `20261014`. The script scans the anonymized
U.S. and Americas news shards with separate deterministic reservoir samples for
each language.

## Outputs

- `preliminary_news_classification.csv`: sampled text, provenance, one Boolean
  column per regex category, combined labels, and unmatched status
- `preliminary_category_frequencies.png`: multi-label category frequencies
- `preliminary_summary.json`: machine-readable sample and result summary

`factish_markers` is the existing rule's name for numeric/report-like surface
features. It is not equivalent to a verified factual claim.
