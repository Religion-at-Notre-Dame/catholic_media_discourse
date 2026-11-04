#!/usr/bin/env python3
"""Render a publication-ready chart from the saved experiment summary."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/catholic-media-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator


HERE = Path(__file__).resolve().parent
SUMMARY_PATH = HERE / "preliminary_summary.json"
OUTPUT_PATH = HERE / "preliminary_category_frequencies_improved.png"

NAVY = "#0C2340"
GOLD = "#AE9142"
GRAY = "#8A8D8F"
TEXT = "#202124"
GRID = "#D9D9D6"

DISPLAY_LABELS = {
    "question": "Question",
    "reporting": "Reporting",
    "opinion": "Opinion",
    "advocacy": "Advocacy",
    "devotional": "Devotional",
    "factish_markers": "Factish markers*",
    "unmatched": "Unmatched",
}


def load_results() -> tuple[int, dict[str, int], dict[str, float]]:
    with SUMMARY_PATH.open(encoding="utf-8") as handle:
        summary = json.load(handle)

    sample_size = int(summary["sample_size"])
    counts = {
        category: int(count)
        for category, count in summary["category_counts"].items()
    }
    percentages = {
        category: float(value)
        for category, value in summary["category_percentages"].items()
    }
    if counts["unmatched"] + sum(
        count for category, count in counts.items() if category != "unmatched"
    ) < sample_size:
        raise ValueError("Saved category totals are inconsistent with sample size.")
    return sample_size, counts, percentages


def render() -> None:
    sample_size, counts, percentages = load_results()
    speech_categories = sorted(
        (category for category in counts if category != "unmatched"),
        key=counts.get,
        reverse=True,
    )
    categories = [*speech_categories, "unmatched"]

    # Leave a deliberate gap before Unmatched to separate it conceptually.
    y_positions = list(range(len(speech_categories) + 1, 1, -1)) + [0]
    colors = [
        GOLD if category == "factish_markers" else NAVY
        for category in speech_categories
    ] + [GRAY]
    widths = [percentages[category] for category in categories]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10.5,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axis = plt.subplots(figsize=(12, 7.2))
    fig.subplots_adjust(left=0.22, right=0.93, top=0.78, bottom=0.23)

    bars = axis.barh(y_positions, widths, height=0.63, color=colors)
    axis.set_yticks(
        y_positions,
        [DISPLAY_LABELS[category] for category in categories],
    )
    axis.set_xlim(0, 50)
    axis.set_ylim(-0.75, max(y_positions) + 0.75)
    axis.xaxis.set_major_locator(MultipleLocator(10))
    axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}%"))
    axis.set_xlabel("Percentage of sampled paragraphs", labelpad=12, color=TEXT)
    axis.tick_params(axis="both", colors=TEXT, length=0)
    axis.grid(axis="x", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    for spine in axis.spines.values():
        spine.set_visible(False)

    for bar, category in zip(bars, categories):
        percentage = percentages[category]
        count = counts[category]
        axis.text(
            percentage + 0.7,
            bar.get_y() + bar.get_height() / 2,
            f"{percentage:.1f}%  ({count:,})",
            va="center",
            ha="left",
            fontsize=10.5,
            fontweight="semibold",
            color=TEXT,
        )

    # The separator makes clear that Unmatched is not another speech act.
    axis.axhline(1, color=GRID, linewidth=1.1)
    axis.text(
        0,
        0.78,
        "NO RULE MATCHED",
        fontsize=8.5,
        fontweight="bold",
        color=GRAY,
        va="bottom",
    )

    fig.suptitle(
        "Preliminary Classification of Catholic Media News Paragraphs",
        x=0.08,
        y=0.955,
        ha="left",
        fontsize=19,
        fontweight="bold",
        color=NAVY,
    )
    fig.text(
        0.08,
        0.895,
        f"{sample_size:,} language-enriched news paragraphs | "
        "Rule-based speech-act detection",
        ha="left",
        fontsize=11.5,
        color="#4B4F54",
    )
    fig.text(
        0.08,
        0.105,
        "* Factish markers are numeric or report-like surface cues—not verified "
        "factual claims.",
        ha="left",
        fontsize=9.2,
        color=GOLD,
        fontweight="semibold",
    )
    fig.text(
        0.08,
        0.055,
        "Methodology: Categories overlap; labels are not human-validated; "
        "percentages are not representative of the full corpus.",
        ha="left",
        fontsize=9.2,
        color="#55565A",
    )

    fig.savefig(
        OUTPUT_PATH,
        dpi=300,
        facecolor="white",
        metadata={
            "Title": "Preliminary Classification of Catholic Media News Paragraphs",
            "Description": "Rule-based, multi-label preliminary classification.",
        },
    )
    plt.close(fig)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    render()
