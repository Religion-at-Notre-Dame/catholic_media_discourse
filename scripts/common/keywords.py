"""Collection keyword lexicons + versioning helpers.

When the keyword list grows, collectors should:
  1. Persist the keyword set used on each run (checkpoint / snapshot).
  2. Resume without re-grabbing URLs/clips already on disk.
  3. Optionally gap-fill *past* days/tasks for *new* keywords only.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from common.cst_papal_documents import cst_keywords_en, cst_keywords_es, cst_keywords_pt
from common.evangelization_themes import (
    EVANGELIZATION_KEYWORDS_EN,
    EVANGELIZATION_KEYWORDS_ES,
    EVANGELIZATION_KEYWORDS_PT,
)
from common.papal_names import papal_keywords_en, papal_keywords_es, papal_keywords_pt
from common.text_normalize import expand_collection_keywords

# English search keywords — CST papal titles + popes + evangelization terms.
# Spelling/accent/apostrophe variants are expanded in get_*_keywords().
KEYWORDS = [
    "catholic",
    "Catholic Church",
    "Vatican",
    "Roman Catholic",
    "Archdiocese",
    "Catholic bishops",
    "Eucharist",
    "Catholic media",
    "Our Lady of Guadalupe",
    "Virgin of Guadalupe",
    *papal_keywords_en(),
    *cst_keywords_en(),
    *EVANGELIZATION_KEYWORDS_EN,
]

# Spanish search keywords — same CST titles + papal names + Spanish forms.
# Gender stays (católico ≠ católica). Number does not: substring match
# picks up católicos / católicas from the singulars.
SPANISH_KEYWORDS = [
    "católico",
    "católica",
    "Iglesia Católica",
    "Vaticano",
    "arquidiócesis",
    "obispos católicos",
    "obispo católico",
    "Eucaristía",
    "Virgen de Guadalupe",
    *papal_keywords_es(),
    *cst_keywords_es(),
    *EVANGELIZATION_KEYWORDS_ES,
]

# Portuguese search keywords — Brazil / Lusophone CST + papal names + mission terms.
PORTUGUESE_KEYWORDS = [
    "católico",
    "católica",
    "Igreja Católica",
    "Vaticano",
    "arquidiocese",
    "bispos católicos",
    "bispo católico",
    "Eucaristia",
    "Nossa Senhora de Aparecida",
    *papal_keywords_pt(),
    *cst_keywords_pt(),
    *EVANGELIZATION_KEYWORDS_PT,
]


def get_keywords(language: str = "english") -> List[str]:
    lang = (language or "english").lower()
    if lang in ("spanish", "es"):
        return expand_collection_keywords(SPANISH_KEYWORDS)
    if lang in ("portuguese", "pt"):
        return expand_collection_keywords(PORTUGUESE_KEYWORDS)
    return expand_collection_keywords(KEYWORDS)


def get_all_keywords() -> List[str]:
    return expand_collection_keywords(
        list(KEYWORDS) + list(SPANISH_KEYWORDS) + list(PORTUGUESE_KEYWORDS)
    )


def get_canonical_keywords(language: str = "english") -> List[str]:
    """Unexpanded base list (for docs / fingerprints of intentional terms)."""
    lang = (language or "english").lower()
    if lang in ("spanish", "es"):
        return normalize_keyword_list(SPANISH_KEYWORDS)
    if lang in ("portuguese", "pt"):
        return normalize_keyword_list(PORTUGUESE_KEYWORDS)
    return normalize_keyword_list(KEYWORDS)


def normalize_keyword_list(keywords: Iterable[str]) -> List[str]:
    """Stable unique list: trim, drop empties, preserve first-seen order (case-insensitive)."""
    out: List[str] = []
    seen: Set[str] = set()
    for raw in keywords:
        if not isinstance(raw, str):
            continue
        term = raw.strip()
        if not term:
            continue
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(term)
    return out


def keyword_fingerprint(keywords: Iterable[str]) -> str:
    """Short stable hash of the normalized keyword set (order-independent)."""
    norms = sorted({k.casefold() for k in normalize_keyword_list(keywords)})
    blob = "\n".join(norms).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def keyword_diff(
    previous: Iterable[str],
    current: Optional[Iterable[str]] = None,
) -> Dict[str, List[str]]:
    """Return added / removed / unchanged vs a prior keyword set."""
    prev = {k.casefold(): k for k in normalize_keyword_list(previous)}
    curr_list = normalize_keyword_list(current if current is not None else get_all_keywords())
    curr = {k.casefold(): k for k in curr_list}
    added = [curr[k] for k in sorted(curr.keys() - prev.keys())]
    removed = [prev[k] for k in sorted(prev.keys() - curr.keys())]
    unchanged = [curr[k] for k in sorted(curr.keys() & prev.keys())]
    return {"added": added, "removed": removed, "unchanged": unchanged}


def keyword_snapshot_payload(
    keywords: Optional[Iterable[str]] = None,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    kws = normalize_keyword_list(keywords if keywords is not None else get_all_keywords())
    payload: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": keyword_fingerprint(kws),
        "count": len(kws),
        "keywords": kws,
        "english": normalize_keyword_list(KEYWORDS),
        "spanish": normalize_keyword_list(SPANISH_KEYWORDS),
        "portuguese": normalize_keyword_list(PORTUGUESE_KEYWORDS),
    }
    if extra:
        payload.update(extra)
    return payload


def write_keyword_snapshot(path: str, keywords: Optional[Iterable[str]] = None, **extra: Any) -> Dict[str, Any]:
    payload = keyword_snapshot_payload(keywords, extra=extra or None)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return payload


def load_keyword_snapshot(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def keywords_from_checkpoint(ckpt: Dict[str, Any]) -> List[str]:
    raw = ckpt.get("keywords") or ckpt.get("keyword_list") or []
    if isinstance(raw, list):
        return normalize_keyword_list(raw)
    return []


def describe_keyword_changes(
    previous: Iterable[str],
    current: Optional[Iterable[str]] = None,
) -> str:
    diff = keyword_diff(previous, current)
    parts = [
        f"keywords now {len(diff['unchanged']) + len(diff['added'])} "
        f"(+{len(diff['added'])} new, -{len(diff['removed'])} removed)"
    ]
    if diff["added"]:
        preview = ", ".join(diff["added"][:8])
        more = f" (+{len(diff['added']) - 8} more)" if len(diff["added"]) > 8 else ""
        parts.append(f"new: {preview}{more}")
    if diff["removed"]:
        preview = ", ".join(diff["removed"][:6])
        parts.append(f"removed: {preview}")
    return "; ".join(parts)


def keyword_run_key(keyword: str, language: str = "") -> str:
    """Stable key for per-keyword resume (language + term)."""
    lang = (language or "").strip().lower()
    term = (keyword or "").strip().casefold()
    return f"{lang}:{term}" if lang else term


def load_completed_keyword_keys(ckpt: Dict[str, Any]) -> Set[str]:
    raw = ckpt.get("completed_keyword_keys") or ckpt.get("completed_keywords") or []
    if not isinstance(raw, list):
        return set()
    return {str(x).strip() for x in raw if str(x).strip()}


def select_keyword_batches_for_resume(
    batches: Sequence[Tuple[str, str]],
    *,
    prior_keywords: Sequence[str],
    completed_keys: Set[str],
    fill_new_only: bool = True,
) -> Tuple[List[Tuple[str, str]], Dict[str, Any]]:
    """Pick keyword/language batches to run.

    - Always skip keys already in completed_keys (quota-friendly resume).
    - If fill_new_only and prior_keywords exist, also skip terms already in prior
      that were never marked complete (treat prior lexicon as done).
    """
    prior_cf = {k.casefold() for k in normalize_keyword_list(prior_keywords)}
    selected: List[Tuple[str, str]] = []
    skipped_done = 0
    skipped_prior = 0
    for kw, lang in batches:
        key = keyword_run_key(kw, lang)
        if key in completed_keys:
            skipped_done += 1
            continue
        if fill_new_only and prior_cf and kw.casefold() in prior_cf:
            # Prior run already covered this term; don't re-query for quota.
            skipped_prior += 1
            continue
        selected.append((kw, lang))
    meta = {
        "selected": len(selected),
        "skipped_completed": skipped_done,
        "skipped_prior_lexicon": skipped_prior,
        "total": len(batches),
    }
    return selected, meta


def save_keyword_checkpoint(
    path: str,
    *,
    keywords: Iterable[str],
    completed_keys: Iterable[str],
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    kws = normalize_keyword_list(keywords)
    payload: Dict[str, Any] = {
        "keywords": kws,
        "keyword_fingerprint": keyword_fingerprint(kws),
        "keyword_count": len(kws),
        "completed_keyword_keys": sorted(set(completed_keys)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
