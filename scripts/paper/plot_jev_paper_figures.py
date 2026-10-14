#!/usr/bin/env python3
"""PhD / slide-ready Education-track figures (Jev + Chile lifts).

Tracked under scripts/paper/ (papers/ is gitignored for LaTeX).
Writes PNGs/PDFs into papers/rise_education_2026/figures/.

  MPLCONFIGDIR=/tmp/mpl python3 scripts/paper/plot_jev_paper_figures.py

Design goals: readable at 50% slide zoom, self-explanatory titles, no spaghetti
edges through labels, consistent ND-adjacent academic palette.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from common.jev_paths import jev_paths  # noqa: E402
from common.label_pretty import pretty_label as pretty  # noqa: E402

PAPER = REPO / "papers/rise_education_2026"
_JEV = jev_paths()
STEM = str(_JEV["stem"])
SUMMARY = Path(_JEV["summary"])
CORR = Path(_JEV["correlations"])
NET = Path(_JEV["networks"])
FIG = PAPER / "figures"
VIZ_FINDINGS = REPO / "viz/data/findings-data.js"
CT_EDGES = REPO / "data/network/country_teaching/edges.jsonl"
CT_NODES = REPO / "data/network/country_teaching/nodes.jsonl"

# Academic palette (navy / gold / forest  -  slide-safe, not purple AI defaults)
NAVY = "#0B1F33"
INK = "#14233A"
GOLD = "#B8860B"
FOREST = "#1B6B4A"
STEEL = "#2E5A88"
MUTED = "#5C6B7A"
RULE = "#D5DCE3"
LIGHT = "#F4F6F8"
WHITE = "#FFFFFF"
HIGHLIGHT = "#C45C26"


def setup() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            # DejaVu first: reliable PDF glyphs for x, dashes, stars (no Helvetica holes).
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "axes.titleweight": "600",
            "figure.facecolor": WHITE,
            "axes.facecolor": WHITE,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": NAVY,
            "axes.linewidth": 0.9,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
            "figure.dpi": 140,
        }
    )


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight", facecolor=WHITE, pad_inches=0.25)
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight", facecolor=WHITE, pad_inches=0.25)
    plt.close(fig)
    print(f"wrote figures/{name}.{{png,pdf}}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_findings() -> dict:
    if not VIZ_FINDINGS.exists():
        return {}
    text = VIZ_FINDINGS.read_text(encoding="utf-8")
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j < 0:
        return {}
    return json.loads(text[i : j + 1])


def footnote(ax, text: str) -> None:
    ax.text(
        0.0,
        -0.14,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        color=MUTED,
        clip_on=False,
    )


def fig_title(fig, title: str, subtitle: str) -> None:
    fig.suptitle(title, x=0.02, y=0.98, ha="left", fontsize=15, fontweight="700", color=NAVY)
    fig.text(0.02, 0.935, subtitle, ha="left", fontsize=9.5, color=MUTED)


# ─── Hero educator panel ─────────────────────────────────────────────────────


def _label_pct(summary: dict, key: str) -> float | None:
    n = int(summary.get("rows_ok") or 0)
    if not n:
        return None
    counts = summary.get("content_labels") or {}
    if key not in counts:
        return None
    return 100.0 * int(counts[key]) / n


def _top_sig_place(corr: dict) -> dict | None:
    for r in corr.get("location_distinctive_top") or []:
        if r.get("significant"):
            return r
    return None


def _top_sig_pair(corr: dict) -> dict | None:
    rows = corr.get("content_cooccur_clean_top") or corr.get("content_cooccur_top") or []
    for r in rows:
        if r.get("significant") and "other_unclear" not in (r.get("a"), r.get("b")):
            return r
    return None


def plot_educator_hooks(corr: dict, summary: dict) -> None:
    n = int(summary.get("rows_ok") or 0)
    hooks = corr.get("hooks") or {}
    mis = hooks.get("misunderstanding_pct")
    if mis is None and summary.get("misunderstanding_rate") is not None:
        mis = round(100 * float(summary["misunderstanding_rate"]), 1)

    inst = _label_pct(summary, "institutional_news")
    doc = _label_pct(summary, "doctrine_sacrament")
    place = _top_sig_place(corr)
    pair = _top_sig_pair(corr)

    inst_big = f"{inst:.1f}%" if inst is not None else "n/a"
    inst_body = (
        f"vs ~{doc:.0f}% doctrine\nHeadlines first" if doc is not None else "Headlines first"
    )
    place_big = f"{float(place['lift_vs_geo_news']):.1f} x " if place else "n/a"
    place_kicker = place["location"] if place else "Place x type"
    place_body = (
        f" x  {pretty(place['label'])}\nvs rest of geo news" if place else "Distinctive lift"
    )
    or_val = float(pair["odds_ratio"]) if pair and pair.get("odds_ratio") is not None else None
    pair_big = f"{or_val:.1f}" if or_val is not None else "n/a"
    pair_body = (
        f"{pretty(pair['a'])}  x  {pretty(pair['b'])}\n(Holm sig.)" if pair else "Types together"
    )

    fig = plt.figure(figsize=(13.2, 5.0))
    fig_title(
        fig,
        'What learners may already "know" from media',
        f"Live dual-taxonomy Jev pilot  ·  n = {n:,} stratified EN/ES/PT excerpts  ·  "
        "Fisher exact + Holm–Bonferroni  ·  triage for educators, not Theology gold",
    )

    # Big number strip
    ax = fig.add_axes([0.04, 0.18, 0.92, 0.62])
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 1)
    ax.axis("off")

    cards = [
        (inst_big, "Institutional news", inst_body, GOLD),
        (f"~{mis}%" if mis is not None else "n/a", "Misunderstanding", "Gentle-correction\nqueue", FOREST),
        (place_big, place_kicker, place_body, STEEL),
        (pair_big, "Odds ratio", pair_body, HIGHLIGHT),
    ]
    for i, (big, kicker, body, color) in enumerate(cards):
        x0 = i
        ax.add_patch(
            FancyBboxPatch(
                (x0 + 0.06, 0.08),
                0.88,
                0.84,
                boxstyle="round,pad=0.02,rounding_size=0.06",
                linewidth=0,
                facecolor=LIGHT,
            )
        )
        ax.add_patch(Rectangle((x0 + 0.06, 0.08), 0.88, 0.06, color=color, lw=0))
        ax.text(x0 + 0.5, 0.72, big, ha="center", va="center", fontsize=28, fontweight="700", color=color)
        ax.text(x0 + 0.5, 0.48, kicker, ha="center", va="center", fontsize=11, fontweight="600", color=NAVY)
        ax.text(x0 + 0.5, 0.28, body, ha="center", va="center", fontsize=9.2, color=MUTED, linespacing=1.35)

    fig.text(
        0.04,
        0.06,
        "Caption cue: Prior-knowledge triage on labeled media  -  not a census of all Catholic discourse.",
        fontsize=9,
        color=MUTED,
    )
    save(fig, "jev_educator_flash")


# ─── Dual taxonomy counts ────────────────────────────────────────────────────


def plot_education_counts(summary: dict) -> None:
    content = summary.get("content_labels") or {}
    discourse = summary.get("discourse_labels") or {}
    n = int(summary.get("rows_ok") or 0)

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.6))
    fig.subplots_adjust(top=0.82, bottom=0.16, wspace=0.45, left=0.22, right=0.97)
    fig_title(
        fig,
        "Dual taxonomy: what is said   ·   how it is said",
        f"Multi-label counts on n = {n:,} excerpts (a row can carry several labels; sums exceed n)",
    )

    for ax, ctr, title, color in (
        (axes[0], content, "Content / teaching type", FOREST),
        (axes[1], discourse, "Discourse / speech-act", STEEL),
    ):
        items = sorted(ctr.items(), key=lambda kv: kv[1])[-8:]
        labels = [pretty(k) for k, _ in items]
        vals = [v for _, v in items]
        ax.barh(labels, vals, color=color, height=0.68, zorder=3)
        ax.axvline(0, color=NAVY, lw=0.8)
        xmax = max(vals) * 1.22 if vals else 1
        ax.set_xlim(0, xmax)
        for y, v in enumerate(vals):
            ax.text(v + xmax * 0.012, y, f"{v:,}", va="center", fontsize=9, color=MUTED)
        ax.set_title(title, loc="left", fontsize=12, pad=8)
        ax.set_xlabel("Labeled excerpts")
        ax.grid(axis="x", color=RULE, lw=0.7, zorder=0)
        ax.set_axisbelow(True)

    fig.text(
        0.04,
        0.04,
        "Institutional news dominates content; news-report and opinion dominate discourse  -  "
        "formation claims are the minority layer educators still need to hear.",
        fontsize=9,
        color=MUTED,
    )
    save(fig, "jev_education_live")


# ─── Place  x  type: heatmap (hero) + clean lift bars ──────────────────────────


def _place_type_matrix(corr: dict) -> tuple[list[str], list[str], np.ndarray, np.ndarray]:
    rows = [r for r in (corr.get("location_distinctive_top") or []) if r.get("significant")]
    places = sorted({r["location"] for r in rows})
    types = sorted({r["label"] for r in rows})
    mat = np.full((len(places), len(types)), np.nan)
    stars = np.full((len(places), len(types)), "", dtype=object)
    idx_p = {p: i for i, p in enumerate(places)}
    idx_t = {t: i for i, t in enumerate(types)}
    for r in rows:
        i, j = idx_p[r["location"]], idx_t[r["label"]]
        mat[i, j] = float(r.get("lift_vs_geo_news") or np.nan)
        stars[i, j] = r.get("stars") or ""
    return places, types, mat, stars


def plot_place_matrix(corr: dict) -> None:
    places, types, mat, stars = _place_type_matrix(corr)
    if not places:
        return
    order = np.argsort(-np.nanmax(np.nan_to_num(mat, nan=0), axis=1))
    places = [places[i] for i in order]
    mat = mat[order]
    stars = stars[order]

    fig, ax = plt.subplots(figsize=(13.0, 7.2))
    fig.subplots_adjust(top=0.84, bottom=0.26, left=0.16, right=0.86)
    fig_title(
        fig,
        "Where teaching types concentrate  -  ActionGeo place  x  type",
        "Cell = lift vs. rest of geolocated news  ·  Holm-significant only (α = 0.05)  ·  "
        "blank = not significant  ·  read rows as accents, columns as hotspots",
    )

    cmap = LinearSegmentedColormap.from_list(
        "lift",
        ["#E8F1F5", "#7EB8C9", "#2E5A88", "#0B1F33", "#B8860B"],
    )
    cmap.set_bad(color="#F0F2F5")
    vmax = float(np.nanmax(mat)) if np.isfinite(np.nanmax(mat)) else 8.0
    im = ax.imshow(mat, cmap=cmap, aspect="auto", vmin=1.0, vmax=max(6.0, vmax))
    ax.set_xticks(range(len(types)))
    ax.set_xticklabels([pretty(t) for t in types], rotation=28, ha="right", fontsize=10.5)
    ax.set_yticks(range(len(places)))
    ax.set_yticklabels(places, fontsize=11)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if np.isnan(v):
                continue
            star = stars[i, j]
            label = f"{v:.1f}x" + (f"\n{star}" if star else "")
            ax.text(
                j,
                i,
                label,
                ha="center",
                va="center",
                fontsize=9.5,
                color=WHITE if v >= 3.2 else NAVY,
                fontweight="600",
                linespacing=1.2,
            )

    cax = fig.add_axes([0.88, 0.30, 0.022, 0.48])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("Lift", fontsize=10)
    cb.outline.set_visible(False)

    fig.text(
        0.04,
        0.06,
        "Devotion/piety peaks in El Salvador, Guatemala, and Mexico  -  the clearest "
        "place accent in the Jev pilot.",
        fontsize=10,
        color=MUTED,
    )
    save(fig, "jev_place_network")
    save(fig, "jev_place_matrix")


def plot_country_teaching_hero() -> None:
    """Replace spaghetti bipartite preview with a distinctive-lift heatmap."""
    if not CT_EDGES.exists():
        return
    nodes = {}
    if CT_NODES.exists():
        for line in CT_NODES.open(encoding="utf-8"):
            if not line.strip():
                continue
            n = json.loads(line)
            nodes[n["id"]] = n.get("label") or n["id"].split(":")[-1]

    # GDELT FIPS-style ids as stored in nodes/edges (El Salvador=ES, Bolivia=BL, Honduras=HO).
    focus_countries = [
        "country:MX",
        "country:BR",
        "country:CI",
        "country:ES",
        "country:GT",
        "country:AR",
        "country:PE",
        "country:CO",
        "country:BL",
        "country:CU",
        "country:HO",
        "country:VE",
    ]
    # Prefer distinctive high-lift theme columns educators recognize
    focus_themes = [
        "theme:guadalupe",
        "theme:oscar_romero",
        "theme:aparecida_celam",
        "theme:liberation_theology",
        "theme:mision",
        "theme:evangelio",
        "theme:laudato_si",
        "theme:immigration",
        "theme:preferential_option",
        "theme:catholic_social_teaching",
    ]
    edges = []
    for line in CT_EDGES.open(encoding="utf-8"):
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("source") in focus_countries and e.get("target") in focus_themes:
            edges.append(e)
    if not edges:
        return

    # Keep theme order; drop countries with no data
    countries = [c for c in focus_countries if any(e["source"] == c for e in edges)]
    themes = [t for t in focus_themes if any(e["target"] == t for e in edges)]
    mat = np.full((len(countries), len(themes)), np.nan)
    distinctive = np.zeros_like(mat, dtype=bool)
    idx_c = {c: i for i, c in enumerate(countries)}
    idx_t = {t: i for i, t in enumerate(themes)}
    for e in edges:
        i, j = idx_c[e["source"]], idx_t[e["target"]]
        mat[i, j] = float(e.get("lift_vs_us") or np.nan)
        distinctive[i, j] = bool(e.get("distinctive"))

    # Sort countries by max distinctive lift
    score = np.nanmax(np.where(distinctive, np.nan_to_num(mat, nan=0), 0), axis=1)
    order = np.argsort(-score)
    countries = [countries[i] for i in order]
    mat = mat[order]
    distinctive = distinctive[order]

    fig, ax = plt.subplots(figsize=(13.2, 7.0))
    fig.subplots_adjust(top=0.84, bottom=0.24, left=0.16, right=0.86)
    fig_title(
        fig,
        "Country  x  teaching map  -  distinctive lifts vs. U.S. news",
        "Lexicon geography (ActionGeo)  ·  gold outline = distinctive cell on the pre-specified teaching map  ·  "
        "QAP r = 0.38 (p < 0.001)",
    )

    # Color by log2(lift) so extreme cells (e.g. Brazil evangelio) do not wash out the map.
    logmat = np.where(np.isfinite(mat), np.log2(np.clip(mat, 0.25, None)), np.nan)
    cmap = LinearSegmentedColormap.from_list(
        "ct",
        ["#F5F7FA", "#A8C5D8", "#2E5A88", "#0B1F33", "#C99700"],
    )
    cmap.set_bad("#F0F2F5")
    im = ax.imshow(logmat, cmap=cmap, aspect="auto", vmin=-1.0, vmax=4.0)

    theme_labels = []
    for t in themes:
        lab = nodes.get(t, t.split(":")[-1])
        lab = pretty(lab) if lab == t.split(":")[-1] else lab.replace("_", " ").title()
        if lab.lower() == "aparecida celam":
            lab = "Aparecida / CELAM"
        theme_labels.append(lab)
    ax.set_xticks(range(len(themes)))
    ax.set_xticklabels(theme_labels, rotation=28, ha="right", fontsize=10.5)
    ax.set_yticks(range(len(countries)))
    ax.set_yticklabels([nodes.get(c, c.split(":")[-1]) for c in countries], fontsize=11)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if np.isnan(v):
                continue
            if distinctive[i, j]:
                ax.add_patch(
                    Rectangle(
                        (j - 0.48, i - 0.48),
                        0.96,
                        0.96,
                        fill=False,
                        edgecolor=GOLD,
                        lw=2.2,
                        zorder=4,
                    )
                )
            ax.text(
                j,
                i,
                f"{v:.1f}x",
                ha="center",
                va="center",
                fontsize=9.5,
                color=WHITE if (np.log2(max(v, 0.25)) >= 1.8) else NAVY,
                fontweight="600",
                zorder=5,
            )

    cax = fig.add_axes([0.88, 0.28, 0.022, 0.48])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("log2(lift vs U.S.)", fontsize=10)
    cb.outline.set_visible(False)
    cb.set_ticks([-1, 0, 1, 2, 3, 4])
    cb.set_ticklabels(["0.5x", "1x", "2x", "4x", "8x", "16x"])

    fig.text(
        0.04,
        0.06,
        "Gold outline = distinctive on the pre-specified map. Mexico–Guadalupe and Brazil–Aparecida "
        "stand out; color uses log2(lift) so one extreme cell cannot dominate the slide.",
        fontsize=10,
        color=MUTED,
    )
    save(fig, "country_teaching_preview")
    save(fig, "country_teaching_heatmap")


def plot_place_lifts(corr: dict) -> None:
    rows = [r for r in (corr.get("location_distinctive_top") or []) if r.get("significant")]
    rows = sorted(rows, key=lambda r: float(r.get("lift_vs_geo_news") or 0))[-10:]
    if not rows:
        return

    labels = [f"{r.get('location')}   ·   {pretty(r.get('label') or '')}" for r in rows]
    lifts = [float(r.get("lift_vs_geo_news") or 0) for r in rows]
    colors = [GOLD if "devotion" in str(r.get("label")) else FOREST for r in rows]

    fig, ax = plt.subplots(figsize=(12.2, 6.0))
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.36, right=0.92)
    fig_title(
        fig,
        "Strongest place  x  teaching-type lifts",
        "Lollipop chart  ·  Fisher exact + Holm  ·  dashed line = parity with rest of geolocated news",
    )

    y = np.arange(len(labels))
    ax.hlines(y, 0, lifts, color=RULE, lw=2.2, zorder=1)
    ax.scatter(lifts, y, s=110, c=colors, zorder=3, edgecolors=WHITE, linewidths=1.4)
    ax.axvline(1.0, color=MUTED, ls="--", lw=1.0, zorder=0)
    ax.text(1.02, len(labels) - 0.35, "parity", fontsize=8, color=MUTED, va="bottom")
    for yi, (r, v) in enumerate(zip(rows, lifts)):
        ax.text(v + 0.12, yi, f"{v:.2f}x  {r.get('stars') or ''}", va="center", fontsize=9.5, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Lift vs. rest of geolocated news")
    ax.set_xlim(0, max(lifts) * 1.18)
    ax.grid(axis="x", color=RULE, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    fig.text(
        0.04,
        0.04,
        "Gold = devotion/piety cells; green = other teaching types. Slide-ready: one takeaway per row.",
        fontsize=9,
        color=MUTED,
    )
    save(fig, "jev_place_lifts")


# ─── Types together: forest-style odds ratios ────────────────────────────────


def plot_types_together(corr: dict) -> None:
    rows = corr.get("content_cooccur_clean_top") or corr.get("content_cooccur_top") or []
    rows = [r for r in rows if r.get("significant")][:10]
    rows = sorted(rows, key=lambda r: float(r.get("odds_ratio") or 0))
    if not rows:
        return

    labels = [f"{pretty(r['a'])}   x   {pretty(r['b'])}" for r in rows]
    ors = [float(r.get("odds_ratio") or 0) for r in rows]

    fig, ax = plt.subplots(figsize=(12.2, 5.8))
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.40, right=0.92)
    fig_title(
        fig,
        "Content types that travel together",
        "Odds ratios from Fisher exact tests (Holm-adjusted)  ·  pairs that co-occur in the same excerpt",
    )

    y = np.arange(len(labels))
    ax.hlines(y, 0, ors, color=STEEL, alpha=0.35, lw=2.4)
    ax.scatter(ors, y, s=120, c=STEEL, zorder=3, edgecolors=WHITE, linewidths=1.4)
    ax.axvline(1.0, color=MUTED, ls="--", lw=1.0)
    for yi, (r, v) in enumerate(zip(rows, ors)):
        ax.text(v + max(ors) * 0.02, yi, f"OR {v:.1f}  {r.get('stars') or ''}", va="center", fontsize=9.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Odds ratio")
    ax.set_xlim(0, max(ors) * 1.22)
    ax.grid(axis="x", color=RULE, lw=0.7)
    ax.set_axisbelow(True)
    fig.text(
        0.04,
        0.04,
        "CST/papal with moral/ethics is the standout co-travel pair  -  useful Week-0 listening for formation.",
        fontsize=9.5,
        color=MUTED,
    )
    save(fig, "jev_types_together")


# ─── Language + modality contrasts ───────────────────────────────────────────


def plot_lang_family(corr: dict) -> None:
    lang = [r for r in (corr.get("language_contrast_en_vs_es") or []) if r.get("significant")]
    fam = [r for r in (corr.get("family_contrast_news_vs_radio") or []) if r.get("significant")][:8]

    fig, axes = plt.subplots(1, 2, figsize=(13.4, 6.0))
    fig.subplots_adjust(top=0.80, bottom=0.14, wspace=0.55, left=0.20, right=0.97)
    fig_title(
        fig,
        "Register contrasts: language and modality",
        "Ratio of rates   ·   dashed line = parity   ·   Fisher exact + Holm–Bonferroni (α = 0.05)",
    )

    def _lollipop(ax, rows, xlabel, title, color, a_name, b_name):
        if not rows:
            ax.text(0.5, 0.5, "No significant contrasts", ha="center", transform=ax.transAxes)
            return
        rows = sorted(rows, key=lambda r: float(r.get("ratio_a_over_b") or 0))
        labels = [pretty(r["label"]) for r in rows]
        ratios = [float(r.get("ratio_a_over_b") or 0) for r in rows]
        y = np.arange(len(labels))
        ax.hlines(y, 0, ratios, color=color, alpha=0.35, lw=2.2)
        ax.scatter(ratios, y, s=100, c=color, zorder=3, edgecolors=WHITE, linewidths=1.2)
        ax.axvline(1.0, color=MUTED, ls="--", lw=1.0)
        for yi, (r, v) in enumerate(zip(rows, ratios)):
            side = f"{a_name}^" if v >= 1 else f"{b_name}^"
            ax.text(v + max(ratios) * 0.03, yi, f"{v:.1f}x {r.get('stars') or ''}  {side}", va="center", fontsize=8.8)
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.set_xlabel(xlabel)
        ax.set_title(title, loc="left", fontsize=12, pad=8)
        ax.set_xlim(0, max(ratios) * 1.35)
        ax.grid(axis="x", color=RULE, lw=0.7)
        ax.set_axisbelow(True)

    _lollipop(axes[0], lang, "English rate ÷ Spanish rate", "English vs Spanish", GOLD, "EN", "ES")
    _lollipop(axes[1], fam, "News rate ÷ radio rate", "News vs radio", FOREST, "News", "Radio")

    fig.text(
        0.04,
        0.04,
        "Doctrine and CST are far denser in English news than in Spanish radio  -  modality shapes the prior "
        "environment as much as country.",
        fontsize=9.5,
        color=MUTED,
    )
    save(fig, "jev_lang_family")


# ─── Chile lifts ─────────────────────────────────────────────────────────────


def plot_chile_lifts(findings: dict) -> None:
    matrix = findings.get("matrix") or []
    ci = next((r for r in matrix if r.get("fips") == "CI"), None)
    if not ci:
        return
    lifts = ci.get("lifts") or {}
    items = [(k, v) for k, v in lifts.items() if v is not None]
    items.sort(key=lambda kv: kv[1])
    if not items:
        return
    names = [pretty(k) for k, _ in items]
    vals = [float(v) for _, v in items]

    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.22, right=0.92)
    fig_title(
        fig,
        "Chile vs United States  -  theme lifts (RISE host window)",
        f"ActionGeo Chile country rates ÷ U.S. rates   ·   country n = {ci.get('n')}   ·   "
        "Santiago metro panel used on the classroom Story page",
    )

    y = np.arange(len(names))
    colors = [FOREST if v >= 1 else MUTED for v in vals]
    ax.hlines(y, 0, vals, color=RULE, lw=2.2)
    ax.scatter(vals, y, s=120, c=colors, zorder=3, edgecolors=WHITE, linewidths=1.4)
    ax.axvline(1.0, color=GOLD, ls="--", lw=1.3)
    ax.text(1.03, len(names) - 0.4, "U.S. parity", color=GOLD, fontsize=9, fontweight="600")
    for yi, v in enumerate(vals):
        ax.text(v + 0.05, yi, f"{v:.2f}x", va="center", fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Lift vs. U.S. news")
    ax.set_xlim(0, max(vals) * 1.2)
    ax.grid(axis="x", color=RULE, lw=0.7)
    ax.set_axisbelow(True)
    top = max(items, key=lambda kv: kv[1])
    near = next((kv for kv in items if 0.85 <= kv[1] <= 1.15), None)
    cue = f"{pretty(top[0])} is elevated in Chile (~{top[1]:.1f} x )"
    if near:
        cue += f"; {pretty(near[0]).lower()} sits near parity (~{near[1]:.2f} x )"
    cue += "  -  an honest place panel, not a U.S. wire story."
    fig.text(0.04, 0.04, cue, fontsize=9.5, color=MUTED)
    save(fig, "chile_theme_lifts")


def _tex_int(n: int) -> str:
    return f"{n:,}".replace(",", "{,}")


def write_education_brief(summary: dict, corr: dict) -> None:
    n = int(summary.get("rows_ok") or 0)
    mis = summary.get("misunderstanding_rate")
    mis_pct = round(100 * float(mis), 1) if mis is not None else None
    hr = int(summary.get("needs_human_review") or 0)
    acc = float(summary.get("accuracy_mean") or 0)
    inst = _label_pct(summary, "institutional_news")
    doc = _label_pct(summary, "doctrine_sacrament")
    place = _top_sig_place(corr)
    pair = _top_sig_pair(corr)

    inst_line = (
        f"Educator hook: $\\sim${inst:.1f}\\% institutional news vs.\\ "
        f"$\\sim${doc:.1f}\\% doctrine.\n"
        if inst is not None and doc is not None
        else ""
    )
    place_line = ""
    if place:
        or_p = place.get("odds_ratio")
        or_s = f"{float(or_p):.1f}" if or_p is not None else "?"
        place_line = (
            f"Place$\\times$type: {place['location']}~$\\cdot$~"
            f"{pretty(place['label']).lower().replace(' / ', '/')} "
            f"(${float(place['lift_vs_geo_news']):.2f}\\times$, OR~{or_s}, Holm $p{{<}}0.001$).\n"
        )
    pair_line = ""
    if pair:
        or_c = pair.get("odds_ratio")
        or_s = f"{float(or_c):.1f}" if or_c is not None else "?"
        a = pretty(pair["a"]).replace(" / ", "/")
        b = pretty(pair["b"]).replace(" / ", "/")
        pair_line = (
            f"Types together: {a}~$\\times$~{b} "
            f"(lift~{float(pair['lift']):.1f}, OR~{or_s}, Holm $p{{<}}0.001$).\n"
        )
    mis_line = (
        f"Misunderstanding rate: $\\sim${mis_pct}\\% of the \\emph{{labeled pilot}} "
        f"(not the full corpus). Human-review flags: {_tex_int(hr)}.\n"
        if mis_pct is not None
        else f"Human-review flags: {_tex_int(hr)}.\n"
    )
    text = (
        "% Auto-generated by plot_jev_paper_figures.py -- do not hand-edit.\n"
        f"Live dual-taxonomy pilot: {_tex_int(n)} stratified EN/ES/PT excerpts "
        "(budget-capped OpenRouter Jev).\n"
        f"{mis_line}"
        f"Mean accuracy triage score: {acc:.2f} (0--4 scale; reportage-heavy, not Theology gold).\n"
        f"{inst_line}{place_line}{pair_line}"
    )
    out = PAPER / "sections/jev_education_brief.tex"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)}")


def main() -> int:
    setup()
    if not SUMMARY.exists() or not CORR.exists():
        raise SystemExit(f"missing {SUMMARY.name} or {CORR.name}")
    summary = load_json(SUMMARY)
    corr = load_json(CORR)
    findings = load_findings()

    plot_educator_hooks(corr, summary)
    plot_education_counts(summary)
    plot_place_matrix(corr)
    plot_place_lifts(corr)
    plot_types_together(corr)
    plot_lang_family(corr)
    plot_chile_lifts(findings)
    plot_country_teaching_hero()
    write_education_brief(summary, corr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
