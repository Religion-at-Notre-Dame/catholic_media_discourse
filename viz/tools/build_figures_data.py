#!/usr/bin/env python3
"""Build viz/data/figures-data.js + sync slide PNGs into viz/assets/figures/.

Interactive classroom figures: paper charts + dual-taxonomy vignette examples.
"""

from __future__ import annotations

def _scrub_emdash(obj):
    if isinstance(obj, str):
        return obj.replace(" \u2014 ", ": ").replace("\u2014", ", ")
    if isinstance(obj, list):
        return [_scrub_emdash(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _scrub_emdash(v) for k, v in obj.items()}
    return obj


import json
import shutil
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
VIZ = TOOLS.parent
ROOT = VIZ.parent
PAPER_FIG = ROOT / "papers/rise_education_2026/figures"
ASSET = VIZ / "assets" / "figures"
OUT = VIZ / "data" / "figures-data.js"

# Key slide figures for the classroom site (must exist under papers/.../figures/).
FIGURE_FILES = [
    "jev_educator_flash.png",
    "jev_education_live.png",
    "jev_place_lifts.png",
    "jev_place_network.png",
    "jev_types_together.png",
    "jev_lang_family.png",
    "chile_theme_lifts.png",
    "country_teaching_preview.png",
]

# Classroom-safe fixture vignettes (same arc as the paper force-for-good section).
EXAMPLES = [
    {
        "id": "laudato",
        "lang": "en",
        "text": (
            "In his encyclical, \"Laudato Si', on Care for Our Common Home,\" the pope said that human life depends on the well-being of the planet."
        ),
        "content": ["cst_papal", "moral_ethics"],
        "discourse": ["doctrinal_claim", "news_report"],
        "tags": ["educator", "types", "taxonomy", "cst"],
        "why": "CST/papal traveling with moral/ethics, the Week-0 listening pair.",
    },
    {
        "id": "option",
        "lang": "en",
        "text": (
            "Pope [PERSON] says that just because [ORGANIZATION] bans artificial contraceptives, it does not mean Catholics have to \"breed like rabbits.\""
        ),
        "content": ["moral_ethics", "cst_papal"],
        "discourse": ["question", "homily_devotional"],
        "tags": ["educator", "chile", "gutierrez", "cst"],
        "why": "Preferential option as a live formation question, not only a slogan.",
    },
    {
        "id": "guadalupe",
        "lang": "en",
        "text": (
            "It is a short leap from [LOCATION], Catholic saint, to Bride the folkloric [ORGANIZATION]."
        ),
        "content": ["devotion_piety", "migration_politics", "moral_ethics"],
        "discourse": ["news_report", "advocacy"],
        "tags": ["place", "country", "devotion", "migration"],
        "why": "Mexico / Guadalupe accent: devotion and migration in one media beat.",
    },
    {
        "id": "romero",
        "lang": "es",
        "text": (
            "La primera JMJ del Papa Francisco. Los jóvenes de todo el mundo fueron convocados por Benedicto XVI… y el Papa Francisco recibió a más de 3 millones."
        ),
        "content": ["devotion_piety", "moral_ethics", "migration_politics"],
        "discourse": ["news_report", "opinion_editorial"],
        "tags": ["place", "devotion", "salvador", "gutierrez"],
        "why": "El Salvador devotion/piety lift has a named local memory attached.",
    },
    {
        "id": "mision",
        "lang": "es",
        "text": (
            "Hola amigos de Tekton. ¿Qué intentamos hacer en este canal de youtube católico? Extender el mensaje del Evangelio."
        ),
        "content": ["evangelization_mission"],
        "discourse": ["doctrinal_claim", "homily_devotional", "advocacy"],
        "tags": ["taxonomy", "lang", "mission"],
        "why": "Spanish mission vocabulary that English often names as gospel/mission.",
    },
    {
        "id": "aparecida",
        "lang": "en",
        "text": (
            "Leonardo Boff and Clodovis Boff, Como Fazer Teologia da Libertação, [LOCATION], [LOCATION], 1986, p. 57."
        ),
        "content": ["cst_papal", "evangelization_mission", "devotion_piety"],
        "discourse": ["doctrinal_claim", "news_report"],
        "tags": ["country", "types", "mission", "chile"],
        "why": "Brazil / CELAM Aparecida path; Chile hears related papal timing delays.",
    },
    {
        "id": "eucharist",
        "lang": "en",
        "text": (
            "Catholics and Orthodox Christians believe when a priest consecrates the red and wine, they cease to exist."
        ),
        "content": ["doctrine_sacrament"],
        "discourse": ["doctrinal_claim", "homily_devotional"],
        "tags": ["taxonomy", "educator", "doctrine"],
        "why": "Thin doctrine layer (~3%) that formation still needs to name.",
    },
    {
        "id": "mary_mis",
        "lang": "en",
        "text": (
            "The 'semi' is because Roman Catholic theology also centers on grace, but sees grace as a substance working renewal in the justified person."
        ),
        "content": ["devotion_piety", "misunderstanding", "doctrine_sacrament"],
        "discourse": ["factual_claim", "news_report"],
        "tags": ["educator", "taxonomy", "misunderstanding"],
        "why": "Gentle-correction queue: devotion claim framed as misunderstanding.",
    },
    {
        "id": "borders_mis",
        "lang": "en",
        "text": (
            "[PERSON] is trying to get [ORGANIZATION] to loosen up."
        ),
        "content": ["migration_politics", "misunderstanding", "moral_ethics"],
        "discourse": ["news_report", "opinion_editorial"],
        "tags": ["educator", "misunderstanding", "migration"],
        "why": "Fragment quote → misunderstanding; triage, not culture-war scoring.",
    },
    {
        "id": "diocese_news",
        "lang": "en",
        "text": (
            "She said the archdiocese assured her that the priest, [PERSON], would never be a pastor or counsel women again."
        ),
        "content": ["institutional_news"],
        "discourse": ["factual_claim", "news_report"],
        "tags": ["educator", "taxonomy", "news"],
        "why": "Institutional news bulk: what learners meet first (~31.8% in the pilot).",
    },
    {
        "id": "liberation_def",
        "lang": "pt",
        "text": (
            "irmãos gêmeos, morreram por [ORGANIZATION] que foram [ORGANIZATION]. Santidade é atribuída a [PERSON] exercido a medicina sem cobrar por isso, devotados à fé. Na Igreja Católica."
        ),
        "content": ["moral_ethics"],
        "discourse": ["factual_claim"],
        "tags": ["chile", "gutierrez", "country"],
        "why": "Gutiérrez's frame still circulates; Chile elevates this vocabulary vs U.S. news.",
    },
]

PANELS = [
    {
        "id": "educator",
        "title": "Educator flash",
        "kicker": "Prior knowledge",
        "blurb": (
            "Four headlines from the live dual-taxonomy pilot. Click a card to see "
            "matching media examples."
        ),
        "image": "jev_educator_flash.png",
        "chart": "educator",
        "exampleTags": ["educator", "cst", "misunderstanding", "news", "doctrine"],
        "href": "triage.html#t-hooks",
    },
    {
        "id": "taxonomy",
        "title": "What is said · how it is said",
        "kicker": "Dual taxonomy",
        "blurb": "Multi-label content vs discourse counts. Click a bar to filter examples.",
        "image": "jev_education_live.png",
        "chart": "taxonomy",
        "exampleTags": ["taxonomy", "mission", "doctrine", "news"],
        "href": "triage.html#t-pairs",
    },
    {
        "id": "place",
        "title": "Place × type lifts",
        "kicker": "ActionGeo",
        "blurb": (
            "Where teaching types run hot vs the rest of geolocated news "
            "(Fisher + Holm). Click a lift."
        ),
        "image": "jev_place_lifts.png",
        "chart": "place",
        "exampleTags": ["place", "devotion", "salvador", "migration"],
        "href": "triage.html#t-places",
    },
    {
        "id": "types",
        "title": "Types that travel together",
        "kicker": "Co-occurrence",
        "blurb": "Odds ratios for content labels that co-travel in the same excerpt.",
        "image": "jev_types_together.png",
        "chart": "types",
        "exampleTags": ["types", "cst", "mission"],
        "href": "triage.html#t-pairs",
    },
    {
        "id": "lang",
        "title": "Language & modality",
        "kicker": "EN · ES · radio",
        "blurb": "English vs Spanish content mixes and news vs radio contrasts.",
        "image": "jev_lang_family.png",
        "chart": "lang",
        "exampleTags": ["lang", "mission", "taxonomy"],
        "href": "triage.html#t-lang",
    },
    {
        "id": "chile",
        "title": "Santiago · Chile lifts",
        "kicker": "RISE host",
        "blurb": (
            "Chile vs U.S. theme lifts. Liberation theology elevated; mission near "
            "parity. Gutiérrez → Santiago story."
        ),
        "image": "chile_theme_lifts.png",
        "chart": "chile",
        "exampleTags": ["chile", "gutierrez", "mission"],
        "href": "explore.html#/santiago",
    },
    {
        "id": "country",
        "title": "Country × teaching map",
        "kicker": "QAP map",
        "blurb": (
            "Slide heatmap of distinctive country×theme cells "
            "(Mexico–Guadalupe, Romero, Aparecida)."
        ),
        "image": "country_teaching_preview.png",
        "chart": "country",
        "exampleTags": ["country", "devotion", "mission", "salvador"],
        "href": "findings.html#f-heat",
    },
]


def sync_assets() -> list[str]:
    ASSET.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in FIGURE_FILES:
        src = PAPER_FIG / name
        if src.exists():
            shutil.copy2(src, ASSET / name)
            copied.append(name)
    return copied


def main() -> int:
    copied = sync_assets()
    out = {
        "generated": "viz/tools/build_figures_data.py",
        "assetBase": "../assets/figures/",
        "note": (
            "Interactive paper figures for the classroom site. Charts bind to "
            "FINDINGS/TRIAGE when present; examples are fixture vignettes."
        ),
        "panels": PANELS,
        "examples": EXAMPLES,
    }
    OUT.write_text(
        "window.FIGURES = " + json.dumps(_scrub_emdash(out), ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(VIZ)} ({OUT.stat().st_size:,} B)")
    print(f"synced {len(copied)}/{len(FIGURE_FILES)} PNGs → assets/figures/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
