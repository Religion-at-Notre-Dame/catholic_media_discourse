"""Resolve live Jev judgment stem paths (shared by viz + paper scripts)."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

REPO = Path(__file__).resolve().parents[2]
JEV_DIR = REPO / "papers/rise_education_2026/analysis/jev_judgments"
# Preferred stem when multiple runs exist (budget-capped dual taxonomy pilot).
PREFERRED_STEM = "jev_dual_20261012T080844Z"


class JevPaths(TypedDict):
    stem: str
    dir: Path
    jsonl: Path
    summary: Path
    correlations: Path
    networks: Path
    fixture_summary: Path


def jev_dir() -> Path:
    return JEV_DIR


def resolve_jev_stem(preferred: str | None = PREFERRED_STEM) -> str:
    """Return stem with summary + correlations present; prefer PREFERRED_STEM."""
    d = JEV_DIR
    if preferred:
        if (d / f"{preferred}.summary.json").exists() and (
            d / f"{preferred}_correlations.json"
        ).exists():
            return preferred
    # Newest dual-taxonomy summary that has a correlations sibling
    cands = sorted(d.glob("jev_dual_*.summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in cands:
        stem = p.name.replace(".summary.json", "")
        if (d / f"{stem}_correlations.json").exists():
            return stem
    return preferred or "jev_dual_unknown"


def jev_paths(stem: str | None = None) -> JevPaths:
    s = stem or resolve_jev_stem()
    d = JEV_DIR
    return {
        "stem": s,
        "dir": d,
        "jsonl": d / f"{s}.jsonl",
        "summary": d / f"{s}.summary.json",
        "correlations": d / f"{s}_correlations.json",
        "networks": d / f"{s}_networks.json",
        "fixture_summary": d / "fixtures/demo_summary.json",
    }
