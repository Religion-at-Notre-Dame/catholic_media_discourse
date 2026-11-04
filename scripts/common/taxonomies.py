"""Dual taxonomies for Education-track judging: content + discourse."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
TAX_DIR = ROOT / "papers" / "rise_education_2026" / "taxonomy"

CONTENT_PATH = TAX_DIR / "informal_learning_v0.yaml"
DISCOURSE_PATH = TAX_DIR / "discourse_acts_v0.yaml"


@lru_cache(maxsize=8)
def load_taxonomy(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Taxonomy not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not data or "labels" not in data:
        raise ValueError(f"Invalid taxonomy file: {p}")
    ids = [str(x.get("id") or "") for x in data["labels"]]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError(f"Taxonomy labels must have unique non-empty ids: {p}")
    for lid in ids:
        if not lid.replace("_", "").isalnum():
            raise ValueError(f"Label id must be alphanumeric/underscore: {lid!r} in {p}")
    return data


def load_content_taxonomy() -> dict[str, Any]:
    return load_taxonomy(str(CONTENT_PATH))


def load_discourse_taxonomy() -> dict[str, Any]:
    return load_taxonomy(str(DISCOURSE_PATH))


def label_ids(tax: dict[str, Any]) -> list[str]:
    return [str(x["id"]) for x in tax["labels"]]


def label_criteria(tax: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for lab in tax["labels"]:
        name = lab.get("name") or lab["id"]
        desc = (lab.get("description") or "").strip().replace("\n", " ")
        out[str(lab["id"])] = f"{name}: {desc}"
    return out


def accuracy_legend(tax: dict[str, Any]) -> list[str]:
    levels = (tax.get("accuracy_scale") or {}).get("levels") or []
    return [f"{lv.get('label')}: {lv.get('criteria')}" for lv in levels]


def include_threshold(tax: dict[str, Any], default: float = 0.55) -> float:
    return float((tax.get("jev_thresholds") or {}).get("include_at") or default)


def human_review_confidence_below(tax: dict[str, Any], default: float = 0.45) -> float:
    return float(
        (tax.get("jev_thresholds") or {}).get("human_review_if_accuracy_confidence_below")
        or default
    )


def validate_taxonomy_schema(
    tax: dict[str, Any],
    *,
    require_examples: bool = False,
) -> list[str]:
    """Return human-readable schema problems (empty = OK)."""
    errs: list[str] = []
    if not tax.get("version"):
        errs.append("missing version")
    labels = tax.get("labels") or []
    if len(labels) < 2:
        errs.append("need ≥2 labels")
    seen: set[str] = set()
    for lab in labels:
        lid = str(lab.get("id") or "")
        if not lid:
            errs.append("empty label id")
            continue
        if lid in seen:
            errs.append(f"duplicate id {lid}")
        seen.add(lid)
        if not lab.get("name") or not lab.get("description"):
            errs.append(f"{lid}: missing name/description")
        if require_examples:
            has_ex = any(
                lab.get(k) for k in ("examples_en", "examples_es", "examples_pt", "examples")
            )
            if not has_ex:
                errs.append(f"{lid}: no examples_*")
    scale = tax.get("accuracy_scale")
    if scale:
        levels = scale.get("levels") or []
        idxs = [lv.get("index") for lv in levels]
        if idxs != list(range(len(idxs))):
            errs.append("accuracy_scale levels should be contiguous indices from 0")
    return errs


def taxonomy_bundle(
    *,
    content: bool = True,
    discourse: bool = True,
) -> dict[str, Any]:
    """Load selected taxonomies for the judge runner."""
    if not content and not discourse:
        raise ValueError("Select at least one of content / discourse")
    out: dict[str, Any] = {
        "content": load_content_taxonomy() if content else None,
        "discourse": load_discourse_taxonomy() if discourse else None,
        "content_path": str(CONTENT_PATH) if content else None,
        "discourse_path": str(DISCOURSE_PATH) if discourse else None,
    }
    return out
