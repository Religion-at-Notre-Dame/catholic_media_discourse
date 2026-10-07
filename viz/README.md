# Interactive Places + Topics

Standalone classroom page. Two views, on purpose:

1. **Places** — heatmap and city/state dots from GDELT ActionGeo lat/lon. Filter by **topic** (English, Spanish, and Portuguese names count as the same teaching). **Play** walks 2015Q1–2025Q4 so you can watch a teaching travel. The United States is California, New York, Texas, D.C. — not one country blob.
2. **Topics only** — theme co-occurrence force graph with **no map**. An edge is two teachings that travel in the same story (lift ≥ 1.25).

Gold teaching lifts (Mexico—Guadalupe, El Salvador—Romero, Brazil—Aparecida) stay in the **inspector** when you click a country or city. They are not drawn as one giant U.S. node.

ActionGeo is where a story was *written into* GDELT, not viewership. Chile is FIPS `CI`. Not the CFP PDF.

```bash
python3 viz/export_map_network.py
python3 viz/export_map_network.py --use-cache --jobs 4
python3 viz/serve.py
```

**Faster on Mac:** `--use-cache` skips rescans when JSONL mtimes are unchanged; `--jobs N` parallelizes per-file place scans (defaults to performance cores − 1). Set `VIZ_MAX_NEWS_ROWS=50000` to cap rows during dev.

**Disk cleanup** (removes redundant GDELT shards after `*_fetched.jsonl` merges):

```bash
bash scripts/cleanup_data.sh          # dry-run
bash scripts/cleanup_data.sh --apply
```

Then open the printed `http://127.0.0.1:8765/index.html`.

- **Places / Topics** — top navbar (active tab in gold)
- **Search** — type `evangelho`, `misión`, `Guadalupe`, `Aparecida` (matches id, label, and EN · ES · PT `also`)
- **Story chips** — Guadalupe, Óscar Romero, Aparecida, *Laudato Si'*, Evangelii Gaudium, gospel / evangelio / evangelho
- **Play** — cinematic time dock: year ticks 2015…2025, cumulative vs this quarter, 0.5× / 1× / 2×; Space play/pause, ← → step quarters
- **Papal documents** — click *Laudato Si'*, *Amoris Laetitia*, *Fratelli Tutti*, or *Evangelii Gaudium* to watch **daily** spread from the promulgation day. Stacked area is mentions by writing region (U.S., Mexico, Brazil, Chile, Andes, Central America, Caribbean, Canada). 8× is the default; the playhead is the calendar day; **This day** is a 7-day rolling count. *Evangelii Gaudium* (2013) starts in 2015, when the corpus begins.
- **Promulgation captions** — *Laudato Si'* 2015, *Amoris Laetitia* 2016, *Querida Amazonia* 2020, *Fratelli Tutti* 2020
- **Inspector** — trilingual names; first ActionGeo mentions; hypothesized teaching; lift vs U.S. news
- **United States** chip — states and metros, sqrt-scaled
- **Heat / Cities / States** — toggles
- **Tour** — Mexico City → San Salvador → São Paulo → Santiago
- **Compare** — US–Mexico, US–Chile, and other pairs (per-1k theme deltas; run `export_viz_extras.py`)
- **Topics:** group legend in the left card, lift slider, papal-only; click a node for neighbors

```bash
./papers/rise_education_2026/analysis/run_extended_analysis.sh --skip-corpus --resume
python3 papers/rise_education_2026/analysis/print_extended_brief.py
python3 viz/export_viz_extras.py --use-cache
```

The pipeline now includes map export (`data.js`), skips slow steps on `--resume`, and uses a **stratified radar sample** (~18s vs full corpus scan).
