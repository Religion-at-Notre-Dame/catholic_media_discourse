# How the Americas Hear the Church

Notre Dame–themed classroom site (multi-page, no login).

```text
viz/
  pages/          Story · Findings · Triage · Methods · Explore HTML
  css/            site.css
  js/             site.js · story.js · findings.js · triage.js · figures.js
  data/           data.js · extras.js · findings/triage/figures-data.js · lexicon.csv · borders
  assets/figures/ Slide PNGs for interactive figures
  branding/       ND marks & partner logos
  tools/          export · verify · build scripts
  serve.py        local static server
  index.html      redirect → pages/index.html
```

```bash
python3 viz/serve.py
# or with checks:
bash viz/tools/check.sh && python3 viz/serve.py --no-browser
python3 viz/serve.py --verify --build-findings
```

Open **http://127.0.0.1:8765/pages/index.html** (or `/index.html` for the redirect).

| Page | File |
|------|------|
| Story | [`pages/index.html`](pages/index.html) · mounts from `findings-data.js` via [`js/story.js`](js/story.js); interactive figures |
| Findings | [`pages/findings.html`](pages/findings.html) · interactive figures + matrix |
| Triage | [`pages/triage.html`](pages/triage.html) · Jev networks + interactive figures + Fisher/Holm contrasts |
| Methods | [`pages/methods.html`](pages/methods.html) · lexicon CSV download |
| Places / Topics / Santiago | [`pages/explore.html`](pages/explore.html)`#/places` · `#/topics` · `#/santiago` (CSV download: all / region / selected location, with `exported_at`) |

Paper figures (tracked generators → `papers/.../figures/`, synced into `viz/assets/figures/`):

```bash
MPLCONFIGDIR=/tmp/mpl python3 scripts/paper/plot_jev_paper_figures.py
python3 viz/tools/build_figures_data.py
```

Map stack (`data/data.js`, Leaflet, D3) loads only on **explore**. Story loads findings + figures snapshots (no Leaflet).

## Verify & rebuild

```bash
bash viz/tools/check.sh
python3 viz/tools/verify_site.py
python3 viz/tools/build_findings_data.py
python3 viz/tools/build_triage_data.py
python3 viz/tools/build_figures_data.py
```

`check.sh` and `serve.py --build-findings` rebuild findings, triage, and figures snapshots.

## Refresh map data from corpus

```bash
python3 viz/tools/export_map_network.py --use-cache --jobs 4
python3 viz/tools/export_viz_extras.py --use-cache
python3 viz/tools/build_findings_data.py
python3 viz/tools/build_triage_data.py
python3 viz/tools/verify_site.py
```

Time scrubber: **2015Q1 → 2026Q2**. ActionGeo = writing location, not viewership. Chile FIPS `CI`.
