"""Canonical GDELT news paths — research repo prefers anonymized shards."""

from __future__ import annotations

from pathlib import Path
from typing import List

US_CORPUS_NAME = "gdelt_us_paragraphs_20150101_20260630.jsonl"
AM_CORPUS_NAME = "gdelt_americas_paragraphs_20150101_20260630.jsonl"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def us_news_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "data/us/news"


def americas_news_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "data/americas/news"


def _anon_parts(base: Path) -> List[Path]:
    return sorted(base.glob("anonymized/anonymized_part_*.jsonl"))


def us_anonymized_paths(root: Path | None = None) -> List[Path]:
    return _anon_parts(us_news_dir(root))


def americas_anonymized_paths(root: Path | None = None) -> List[Path]:
    return _anon_parts(americas_news_dir(root))


def us_corpus_path(root: Path | None = None) -> Path | None:
    """Single U.S. paragraph merge if present (pipeline); else None."""
    p = us_news_dir(root) / US_CORPUS_NAME
    return p if p.exists() else None


def americas_corpus_path(root: Path | None = None) -> Path | None:
    p = americas_news_dir(root) / AM_CORPUS_NAME
    return p if p.exists() else None


def us_corpus_inputs(root: Path | None = None) -> List[Path]:
    anon = us_anonymized_paths(root)
    if anon:
        return anon
    us = us_corpus_path(root)
    return [us] if us else []


def americas_corpus_inputs(root: Path | None = None) -> List[Path]:
    anon = americas_anonymized_paths(root)
    if anon:
        return anon
    am = americas_corpus_path(root)
    return [am] if am else []


def paragraph_scan_paths(root: Path | None = None) -> List[Path]:
    """News JSONL for geo/theme scans — anonymized parts in research repo."""
    root = root or project_root()
    out: List[Path] = []
    for p in us_corpus_inputs(root):
        if p not in out:
            out.append(p)
    for p in americas_corpus_inputs(root):
        if p not in out:
            out.append(p)
    return out


def classify_input_paths(root: Path | None = None) -> List[tuple[str, Path, str]]:
    """Not used in research repo (no raw classify step)."""
    return []
