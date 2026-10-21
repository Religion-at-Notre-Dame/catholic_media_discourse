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
    "pages/triage.html",
    "pages/methods.html",
    "pages/next.html",
    "pages/language.html",
    "pages/misconceptions.html",
    "pages/label.html",
    "pages/explore.html",
    "css/site.css",
    "js/site.js",
    "partials/footer.html",
    "js/story.js",
    "js/findings.js",
    "js/triage.js",
    "js/figures.js",
    "js/label.js",
    "js/misconceptions.js",
    "data/data.js",
    "data/extras.js",
    "data/findings-data.js",
    "data/triage-data.js",
    "data/figures-data.js",
    "assets/figures/jev_educator_flash.png",
    "assets/figures/chile_theme_lifts.png",
    "tools/build_figures_data.py",
    "data/americas-borders.json",
    "data/lexicon.csv",
    "data/education_taxonomies.csv",
    "index.html",
    ".nojekyll",
    "serve.py",
    "tools/export_lexicon_csv.py",
    "tools/export_map_network.py",
    "tools/build_findings_data.py",
    "tools/build_triage_data.py",
    "tools/verify_site.py",
    "tools/publish_personal_site.sh",
    "branding/nd-monogram.svg",
    "branding/wordmark.svg",
    "branding/academic-mark.svg",
    "branding/partners/lucy-family-institute.svg",
    "branding/partners/dac.svg",
    "branding/partners/dial-lab.png",
    "branding/partners/de-nicola.png",
    "branding/nd-monogram-gold-96.png",
]

PAGE_IDS = {
    "index.html": [
        "storyboard",
        "nav-story",
        "cta-explore",
        "cta-abstract",
        "cta-poster",
        "authors",
        "site-footer",
        "research-questions",
        "story-corpus",
        "story-signatures",
        "story-santiago",
        "story-santiago-lead",
        "story-education",
        "story-education-headline",
        "story-education-note",
        "story-education-beats",
        "story-figures",
        "story-figures-board",
        "cta-santiago",
    ],
    "findings.html": [
        "findings",
        "nav-findings",
        "f-corpus",
        "f-education",
        "f-figures",
        "site-footer",
    ],
    "triage.html": [
        "triage",
        "nav-triage",
        "t-howto",
        "t-hooks",
        "t-figures",
        "t-network",
        "t-network-mode",
        "t-network-readout",
        "t-family",
        "site-footer",
    ],
    "methods.html": ["methods", "nav-methods", "techniques", "lexicon", "rigor", "theories", "site-footer"],
    "misconceptions.html": ["misconceptions", "nav-misconceptions", "mis-sources", "mis-outlets", "mis-types", "mis-accuracy", "mis-by-type", "site-footer"],
    "label.html": ["label", "nav-label", "label-post", "label-check", "site-footer"],
    "next.html": ["next", "nav-next", "pending-funding", "site-footer"],
    "language.html": ["language", "nav-language", "lang-table", "site-footer"],
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
    "Jonathan A. Karr Jr.",
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
        elif rel == ".nojekyll":
            # Empty marker is valid for GitHub Pages (disables Jekyll).
            ok(f"file {rel} (Pages marker)")
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
        for href in (
            "index.html",
            "findings.html",
            "triage.html",
            "methods.html",
            "misconceptions.html",
            "language.html",
            "explore.html#/places",
        ):
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
    if "../data/findings-data.js" not in pages["index.html"]:
        err("index.html (Story) missing ../data/findings-data.js")
    else:
        ok("story findings-data path")
    if "../js/story.js" not in pages["index.html"]:
        err("index.html missing ../js/story.js")
    else:
        ok("story.js path")
    if "../data/figures-data.js" not in pages["index.html"]:
        err("index.html missing ../data/figures-data.js")
    else:
        ok("story figures-data path")
    if "../js/figures.js" not in pages["index.html"]:
        err("index.html missing ../js/figures.js")
    else:
        ok("figures.js path")
    if "data-figures" not in pages["index.html"]:
        err("index.html missing figures mount")
    else:
        ok("story figures mount")
    for name in ("index.html", "findings.html", "triage.html", "methods.html"):
        if "Triage lab" in pages[name] or "figures lab" in pages[name].lower():
            err(f"{name} still says lab")
        else:
            ok(f"{name} no lab wording")

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
        "informal learning",
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

    if ".py" in methods:
        err("methods.html should not cite .py script paths (classroom readers)")
    else:
        ok("methods has no .py script paths")

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

    methods = pages["methods.html"]
    if 'id="triage"' not in methods and "id='triage'" not in methods:
        err("methods.html missing #triage section")
    else:
        ok("methods #triage")
    if "education_taxonomies.csv" not in methods:
        err("methods.html missing education_taxonomies.csv download")
    else:
        ok("methods taxonomy CSV link")
    findings_js = (JS / "findings.js").read_text(encoding="utf-8")
    if "renderEducation" not in findings_js:
        err("findings.js missing renderEducation")
    else:
        ok("findings education renderer")
    findings_data = (DATA / "findings-data.js").read_text(encoding="utf-8")
    if '"education"' not in findings_data:
        err("findings-data.js missing education block")
    else:
        ok("findings-data education block")
    tax_csv = DATA / "education_taxonomies.csv"
    if not tax_csv.exists() or tax_csv.stat().st_size < 200:
        err("viz/data/education_taxonomies.csv missing: run export_education_taxonomies_csv.py")
    else:
        ok("education_taxonomies.csv")

    triage = pages["triage.html"]
    if "../data/triage-data.js" not in triage:
        err("triage.html missing triage-data.js")
    else:
        ok("triage data path")
    if "renderTriage" not in (JS / "triage.js").read_text(encoding="utf-8"):
        err("triage.js missing renderTriage")
    else:
        ok("triage renderer")
    if "mode-triage" not in css:
        err("site.css missing mode-triage")
    else:
        ok("mode-triage CSS")
    triage_data = (DATA / "triage-data.js").read_text(encoding="utf-8")
    if "window.TRIAGE" not in triage_data or "networks" not in triage_data:
        err("triage-data.js missing TRIAGE networks")
    else:
        ok("triage-data networks")
    if "family_contrast" not in triage_data:
        err("triage-data.js missing family_contrast")
    else:
        ok("triage-data family_contrast")
    triage_js = (JS / "triage.js").read_text(encoding="utf-8")
    if "renderFamily" not in triage_js:
        err("triage.js missing renderFamily")
    else:
        ok("triage family renderer")
    if "Strong signal" not in triage and "Strong signal" not in triage_js:
        err("triage page should use plain Strong signal badges (not star counts)")
    else:
        ok("triage plain-language signal badges")
    if "place_x_type" not in triage_js or "t-network-readout" not in triage:
        err("triage should expose bipartite place×type map + readout")
    else:
        ok("triage bipartite map + readout")
    if "triage-steps" not in triage or "t-howto" not in triage:
        err("triage.html missing how-to flow steps")
    else:
        ok("triage how-to flow")
    for name, html in pages.items():
        if name == "triage.html":
            continue
        if 'href="triage.html"' not in html:
            err(f"{name} missing triage.html nav link")
        else:
            ok(f"{name} links triage")

    if "renderFindings" not in site_js:
        err("site.js should render findings on findings.html")
    else:
        ok("site.js shared helpers")
    if "renderTriage" not in site_js and "mode-triage" not in site_js:
        err("site.js should boot triage page")
    else:
        ok("site.js triage boot")
    if "renderStory" not in site_js and "mode-story" not in site_js:
        err("site.js should boot story page")
    else:
        ok("site.js story boot")
    footer_html = (VIZ / "partials" / "footer.html").read_text(encoding="utf-8")
    if "../partials/footer.html" not in site_js:
        err("site.js should load the shared footer")
    elif "dial-lab.png" not in footer_html or "de-nicola.png" not in footer_html:
        err("shared footer missing poster logos")
    else:
        ok("shared footer")
        for name, html in pages.items():
            if name == "explore.html":
                continue
            if html.count('id="site-footer"') != 1 or "nd-footer__brands" in html:
                err(f"{name} should mount the shared footer once")
            else:
                ok(f"{name} shared footer mount")
    if "renderStory" not in (JS / "story.js").read_text(encoding="utf-8"):
        err("story.js missing renderStory")
    else:
        ok("story renderer")
    fig_js = (JS / "figures.js").read_text(encoding="utf-8")
    if "renderFigures" not in fig_js:
        err("figures.js missing renderFigures")
    else:
        ok("figures renderer")
    if "figlab" in fig_js or "data-figures-lab" in fig_js:
        err("figures.js still uses lab naming")
    else:
        ok("figures.js naming")

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

    try:
        triage = load_js_assign(DATA / "triage-data.js", "TRIAGE")
        ok("triage-data.js parses")
    except Exception as e:
        err(str(e))
        triage = {}

    try:
        figures = load_js_assign(DATA / "figures-data.js", "FIGURES")
        ok("figures-data.js parses")
        panels = figures.get("panels") or []
        examples = figures.get("examples") or []
        if len(panels) >= 5 and len(examples) >= 8:
            ok(f"FIGURES panels={len(panels)} examples={len(examples)}")
        else:
            err("FIGURES missing panels/examples: run build_figures_data.py")
        for need in ("educator", "chile", "place", "types"):
            if not any(p.get("id") == need for p in panels):
                err(f"FIGURES missing panel {need}")
    except Exception as e:
        err(str(e))
        figures = {}

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

    story = findings.get("story") or {}
    beats = story.get("beats") or []
    if len(beats) >= 2 and story.get("headline"):
        ok(f"FINDINGS.story beats={len(beats)}")
    else:
        err("FINDINGS.story missing headline/beats: rebuild build_findings_data.py")
    # Beat hrefs must land on Triage/Findings mounts
    triage_html = pages["triage.html"]
    findings_html = pages["findings.html"]
    for b in beats:
        href = str(b.get("href") or "")
        if not href:
            err(f"story beat {b.get('id')} missing href")
            continue
        if href.startswith("triage.html#"):
            frag = href.split("#", 1)[1]
            if f'id="{frag}"' not in triage_html:
                err(f"story beat href missing mount: {href}")
            else:
                ok(f"story beat → #{frag}")
        elif href.startswith("findings.html#"):
            frag = href.split("#", 1)[1]
            if f'id="{frag}"' not in findings_html:
                err(f"story beat href missing mount: {href}")
            else:
                ok(f"story beat → #{frag}")
    # Humanized labels (no raw snake_case taxonomy on Story)
    joined = " ".join(str(b.get("text") or "") for b in beats)
    if "devotion_piety" in joined or "cst_papal" in joined:
        err("FINDINGS.story beats still use snake_case taxonomy ids: rebuild findings")
    else:
        ok("FINDINGS.story beats use human labels")

    # Santiago lifts must match Chile matrix (within float rounding).
    ci = next((r for r in matrix if r.get("fips") == "CI"), None)
    if ci and lifts:
        bad = []
        for d in lifts:
            tid = d.get("theme_id")
            if not tid:
                bad.append("missing theme_id")
                continue
            want = (ci.get("lifts") or {}).get(tid)
            got = d.get("x")
            if want is None or got is None:
                bad.append(f"{tid}: missing")
            elif abs(float(want) - float(got)) > 0.051:
                bad.append(f"{tid}: matrix={want} santiago={got}")
        if bad:
            err("santiago lifts diverge from Chile matrix: " + "; ".join(bad))
        else:
            ok("santiago lifts match Chile matrix")
    else:
        err("cannot verify Santiago vs Chile matrix")

    fam = triage.get("family_contrast") or []
    if fam:
        ok(f"TRIAGE.family_contrast n={len(fam)}")
    else:
        err("TRIAGE.family_contrast empty")

    export = TOOLS / "export_map_network.py"
    if export.exists() and "2026Q2" in export.read_text(encoding="utf-8"):
        ok("export_map_network months include through 2026Q2")
    else:
        warn("export_map_network 2026Q2 marker not found")

    for js in (
        JS / "site.js",
        JS / "story.js",
        JS / "findings.js",
        JS / "triage.js",
        JS / "figures.js",
        JS / "label.js",
        JS / "misconceptions.js",
        DATA / "data.js",
        DATA / "extras.js",
        DATA / "findings-data.js",
        DATA / "triage-data.js",
        DATA / "figures-data.js",
    ):
        before = len(errors)
        check_node_syntax(js, errors)
        if len(errors) == before:
            ok(f"syntax {js.name}")
    if explore.count("<script") != explore.count("</script>"):
        err("explore.html unbalanced script tags")
    else:
        ok("explore script tags balanced")

    root_index = (VIZ / "index.html").read_text(encoding="utf-8")
    if "pages/index.html" not in root_index:
        err("root index.html should redirect to pages/index.html")
    else:
        ok("root index redirects to pages/")

    # Subpath-safe for jonathankarr.com/how_the_americas_hear_the_church/
    abs_hits = []
    for html_path in PAGES.glob("*.html"):
        text = html_path.read_text(encoding="utf-8")
        for needle in ('href="/', 'src="/'):
            if needle in text:
                abs_hits.append(f"{html_path.name}:{needle}")
    if abs_hits:
        err("absolute root paths break GitHub Pages subpath: " + ", ".join(abs_hits[:6]))
    else:
        ok("pages use relative asset paths (Pages subpath-safe)")
    publish = TOOLS / "publish_personal_site.sh"
    if publish.exists() and "jonathankarr.com/how_the_americas_hear_the_church" in publish.read_text(
        encoding="utf-8"
    ):
        ok("personal-site publish script")
    else:
        err("publish_personal_site.sh missing public URL")

    if not errors:
        print(f"\n{ok_n} checks passed · {len(warnings)} warnings · 0 errors")
        return 0
    print(f"\n{ok_n} checks passed · {len(warnings)} warnings · {len(errors)} errors")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
