#!/usr/bin/env python3
"""Verify the classroom site: multi-page HTML, assets, data through 2026Q2."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
VIZ = TOOLS.parent
PAGES = VIZ / "pages"
CSS = VIZ / "css"
JS = VIZ / "js"
DATA = VIZ / "data"

REQUIRED_FILES = [
    "pages/index.html",
    "pages/findings.html",
    "pages/methods.html",
    "pages/explore.html",
    "css/site.css",
    "js/site.js",
    "js/findings.js",
    "data/data.js",
    "data/extras.js",
    "data/findings-data.js",
    "data/americas-borders.json",
    "data/lexicon.csv",
    "index.html",
    "serve.py",
    "tools/export_lexicon_csv.py",
    "tools/export_map_network.py",
    "tools/verify_site.py",
    "branding/nd-monogram.svg",
    "branding/wordmark.svg",
    "branding/academic-mark.svg",
    "branding/partners/lucy-family-institute.svg",
    "branding/nd-monogram-gold-96.png",
]

PAGE_IDS = {
    "index.html": ["storyboard", "nav-story", "cta-explore", "authors", "site-footer", "research-questions"],
    "findings.html": ["findings", "nav-findings", "f-corpus", "site-footer"],
    "methods.html": ["methods", "nav-methods", "techniques", "lexicon", "site-footer"],
    "explore.html": [
        "explorer",
        "map",
        "graph",
        "tab-places",
        "tab-topics",
        "time",
        "topic-search",
        "btn-dl-all",
        "btn-dl-view",
    ],
}

AUTHOR_NEEDLES = [
    "Jonathan A. Karr",
    "Yessica Herrera-Guzmán",
    "Ingrid Corpus",
    "Brenda Nogueira",
    "Sidney Almanza Anjos",
    "Nitesh V. Chawla",
    "linkedin.com/in/jonathankarr",
]

def load_js_assign(path: Path, name: str) -> dict:
    script = f"""
global.window = {{}};
const fs = require('fs');
eval(fs.readFileSync({json.dumps(str(path))}, 'utf8'));
if (!window[{json.dumps(name)}]) {{
  console.error('missing', {json.dumps(name)});
  process.exit(2);
}}
process.stdout.write(JSON.stringify(window[{json.dumps(name)}]));
"""
    r = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        cwd=str(VIZ),
    )
    if r.returncode != 0:
        raise RuntimeError(f"Failed to load {path.name}: {r.stderr.strip() or r.stdout.strip()}")
    return json.loads(r.stdout)


def expected_months() -> list[str]:
    out = []
    for y in range(2015, 2027):
        for q in range(1, 5):
            if y == 2026 and q > 2:
                break
            out.append(f"{y}Q{q}")
    return out


def check_node_syntax(path: Path, errors: list[str]) -> None:
    if path.suffix != ".js":
        return
    r = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        errors.append(f"syntax {path.name}: {r.stderr.strip()}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    ok_n = 0

    def ok(msg: str) -> None:
        nonlocal ok_n
        ok_n += 1
        print(f"  ✓ {msg}")

    def err(msg: str) -> None:
        errors.append(msg)
        print(f"  ✗ {msg}")

    def warn(msg: str) -> None:
        warnings.append(msg)
        print(f"  ! {msg}")

    print("verify_site · catholic media viz (multi-page)")

    for rel in REQUIRED_FILES:
        p = VIZ / rel
        if not p.exists():
            err(f"missing file: {rel}")
        elif p.stat().st_size < 10:
            err(f"empty/tiny file: {rel}")
        else:
            ok(f"file {rel} ({p.stat().st_size:,} B)")

    pages = {name: (PAGES / name).read_text(encoding="utf-8") for name in PAGE_IDS}
    css = (CSS / "site.css").read_text(encoding="utf-8")
    site_js = (JS / "site.js").read_text(encoding="utf-8")

    for name, html in pages.items():
        if html.count("<main") != html.count("</main>"):
            err(f"{name}: unbalanced <main>")
        else:
            ok(f"{name}: balanced <main>")
        for eid in PAGE_IDS[name]:
            if f'id="{eid}"' not in html:
                err(f"{name}: missing id={eid}")
            else:
                ok(f"{name} #{eid}")
        for href in ("index.html", "findings.html", "methods.html", "explore.html#/places"):
            if href not in html:
                err(f"{name}: missing nav href {href}")
            else:
                ok(f"{name} links {href}")
        if "../css/site.css" not in html:
            err(f"{name}: missing ../css/site.css")
        else:
            ok(f"{name} css path")
        if "../branding/nd-monogram.svg" not in html:
            err(f"{name}: missing branding path")
        else:
            ok(f"{name} branding path")
        if name != "explore.html" and "../js/site.js" not in html:
            err(f"{name}: missing ../js/site.js")
        elif name != "explore.html":
            ok(f"{name} site.js path")

    if "../data/data.js" not in pages["explore.html"]:
        err("explore.html missing ../data/data.js")
    else:
        ok("explore data.js path")
    if "../data/extras.js" not in pages["explore.html"]:
        err("explore.html missing ../data/extras.js")
    else:
        ok("explore extras.js path")
    if "../data/findings-data.js" not in pages["findings.html"]:
        err("findings.html missing ../data/findings-data.js")
    else:
        ok("findings data path")

    index = pages["index.html"]
    if "orcid.org" in index.lower():
        err("ORCID links should not appear")
    else:
        ok("no ORCID links")
    if "SiteGate" in index:
        err("SiteGate login UI must not ship")
    else:
        ok("no SiteGate")

    missing_authors = [n for n in AUTHOR_NEEDLES if n not in index]
    if missing_authors:
        for n in missing_authors:
            err(f"authors/links missing: {n}")
    else:
        ok("author roster + LinkedIn present")

    story_needles = (
        'id="research-questions"',
        "circulate across the media",
        "How this prototype breaks it down",
        "rq-list",
    )
    for n in story_needles:
        if n not in index:
            err(f"story missing: {n}")
        else:
            ok(f"story has {n[:40]}")

    methods = pages["methods.html"]
    methods_needles = (
        'id="lexicon"',
        'id="techniques"',
        "Controlled lexicon matching",
        "Education &amp; impact",
        "THEME_PATTERNS",
        "methods-toc",
        "lexicon.csv",
        "papal / magisterial document titles",
        "language",
    )
    missing_m = [n for n in methods_needles if n not in methods]
    if missing_m:
        for n in missing_m:
            err(f"methods missing: {n}")
    else:
        ok("methods: techniques + lexicon + impact")

    if "viz/tools/export_lexicon_csv.py" not in methods:
        warn("methods regenerate path may still say old location")

    explore = pages["explore.html"]
    if "window.__bootVizApp" not in explore:
        err("explore.html missing __bootVizApp")
    else:
        ok("explore boots map app")
    for needle in ("__downloadGeoAll", "exported_at", "collectGeoRows"):
        if needle not in explore:
            err(f"explore download missing: {needle}")
        else:
            ok(f"explore download {needle}")
    if "geo-download" not in pages["methods.html"]:
        err("methods missing ActionGeo download note")
    else:
        ok("methods geo-download note")
    if "americas-borders.json" not in explore:
        warn("explore may not reference americas-borders.json inline (fetch OK)")

    if "mode-explore" not in css:
        err("site.css missing mode-explore rules")
    else:
        ok("mode-explore CSS present")

    if "renderFindings" not in site_js:
        err("site.js should render findings on findings.html")
    else:
        ok("site.js shared helpers")

    try:
        viz = load_js_assign(DATA / "data.js", "VIZ")
        ok("data.js parses")
    except Exception as e:
        err(str(e))
        viz = {}

    try:
        load_js_assign(DATA / "extras.js", "VIZ_EXTRAS")
        ok("extras.js parses")
    except Exception as e:
        err(str(e))

    try:
        findings = load_js_assign(DATA / "findings-data.js", "FINDINGS")
        ok("findings-data.js parses")
    except Exception as e:
        err(str(e))
        findings = {}

    months = (viz.get("spread") or {}).get("months") or []
    want = expected_months()
    if months[:1] == ["2015Q1"] and months[-1:] == ["2026Q2"] and len(months) == len(want):
        ok(f"months 2015Q1 → 2026Q2 ({len(months)} quarters)")
    else:
        err(f"months bad: len={len(months)} first={months[:1]} last={months[-1:]}")

    if 'id="time"' in explore and 'max="45"' in explore:
        ok("time scrubber max=45")
    else:
        if 'id="time"' in explore:
            ok("time scrubber present")
        else:
            err("time scrubber missing")

    places = viz.get("places") or []
    metros = viz.get("metros") or []
    ok(f"places={len(places)} metros={len(metros)}")
    edges = (viz.get("topics") or {}).get("edges") or []
    ok(f"topic edges={len(edges)}")

    try:
        extras = load_js_assign(DATA / "extras.js", "VIZ_EXTRAS")
        cts = extras.get("countryThemes") or []
        ok(f"extras countries={len(cts)}")
    except Exception:
        pass

    matrix = findings.get("matrix") or []
    if any(r.get("fips") == "CI" for r in matrix):
        ok("findings matrix includes Chile")
    else:
        err("findings matrix missing Chile")

    lifts = (findings.get("santiago") or {}).get("lifts") or []
    if len(lifts) >= 3:
        ok(f"santiago lifts={len(lifts)}")
    else:
        err("santiago lifts thin")

    export = TOOLS / "export_map_network.py"
    if export.exists() and "2026Q2" in export.read_text(encoding="utf-8"):
        ok("export_map_network months include through 2026Q2")
    else:
        warn("export_map_network 2026Q2 marker not found")

    for js in (
        JS / "site.js",
        JS / "findings.js",
        DATA / "data.js",
        DATA / "extras.js",
        DATA / "findings-data.js",
    ):
        check_node_syntax(js, errors)
    if explore.count("<script") != explore.count("</script>"):
        err("explore.html unbalanced script tags")
    else:
        ok("explore script tags balanced")

    root_index = (VIZ / "index.html").read_text(encoding="utf-8")
    if "pages/index.html" not in root_index:
        err("root index.html should redirect to pages/index.html")
    else:
        ok("root index redirects to pages/")

    if not errors:
        print(f"\n{ok_n} checks passed · {len(warnings)} warnings · 0 errors")
        return 0
    print(f"\n{ok_n} checks passed · {len(warnings)} warnings · {len(errors)} errors")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
