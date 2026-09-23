"""Pull CAMEO actors / Goldstein fields out of stored GDELT EVENTS rows.

Daily exports are 58 columns; some 2.1 files are 61+ (ADM2 inserted before
ActionGeo). Actor and event-code positions are the same in both layouts.
Collectors store every cell as ``col_N`` plus a few named convenience keys.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# 0-based GDELT EVENTS indices (Leetaru & Schrodt 2013; GDELT 2.0 codebook).
_COL = {
    "actor1_code": 5,
    "actor1_name": 6,
    "actor1_country": 7,
    "actor2_code": 15,
    "actor2_name": 16,
    "actor2_country": 17,
    "event_code": 26,
    "event_base_code": 27,
    "event_root_code": 28,
    "quad_class": 29,
    "goldstein": 30,
    "num_mentions": 31,
}

_NAMED = {
    "actor1_code": ("Actor1Code",),
    "actor1_name": ("Actor1Name",),
    "actor1_country": ("Actor1CountryCode",),
    "actor2_code": ("Actor2Code",),
    "actor2_name": ("Actor2Name",),
    "actor2_country": ("Actor2CountryCode",),
    "event_code": ("EventCode",),
    "event_base_code": ("EventBaseCode",),
    "event_root_code": ("EventRootCode",),
    "quad_class": ("QuadClass",),
    "goldstein": ("GoldsteinScale",),
    "num_mentions": ("NumMentions",),
}

QUAD_LABEL = {
    1: "verbal_cooperation",
    2: "material_cooperation",
    3: "verbal_conflict",
    4: "material_conflict",
}

# CAMEO event root codes (first two digits / EventRootCode).
ROOT_LABEL = {
    "01": "make_public_statement",
    "02": "appeal",
    "03": "express_intent_to_cooperate",
    "04": "consult",
    "05": "diplomatic_cooperation",
    "06": "material_cooperation",
    "07": "provide_aid",
    "08": "yield",
    "09": "investigate",
    "10": "demand",
    "11": "disapprove",
    "12": "reject",
    "13": "threaten",
    "14": "protest",
    "15": "exhibit_force",
    "16": "reduce_relations",
    "17": "coerce",
    "18": "assault",
    "19": "fight",
    "20": "mass_violence",
}


def _cell(api: Dict[str, Any], key: str) -> str:
    for name in _NAMED.get(key, ()):
        raw = api.get(name)
        if raw not in (None, ""):
            text = str(raw).strip()
            if text.lower() not in {"none", "nan", "null"}:
                return text
    idx = _COL[key]
    raw = api.get(f"col_{idx}")
    if raw in (None, ""):
        return ""
    text = str(raw).strip()
    if text.lower() in {"none", "nan", "null"}:
        return ""
    return text


_ACTOR_ALIAS = {
    "THE POPE": "POPE",
    "POPE FRANCIS": "POPE",
    "POPE BENEDICT": "POPE",
    "POPE JOHN PAUL": "POPE",
    "FRANCIS": "POPE",
    "HOLY SEE": "VATICAN",
    "HOLYSEE": "VATICAN",
    "VATICAN CITY": "VATICAN",
    "ROMAN CATHOLIC": "CATHOLIC",
    "CATHOLIC CHURCH": "CATHOLIC",
    "CATHOLICISM": "CATHOLIC",
    "UNITED STATES OF AMERICA": "UNITED STATES",
    "USA": "UNITED STATES",
    "U.S.": "UNITED STATES",
    "AMERICA": "UNITED STATES",
}

# Too generic to be interesting hubs in the classroom focus graph.
GENERIC_ACTORS = frozenset(
    {
        "CATHOLIC",
        "SCHOOL",
        "STUDENT",
        "EDUCATION",
        "POLICE",
        "GOVERNMENT",
        "MEDIA",
        "COMMUNITY",
        "PEOPLE",
        "CITY",
        "COUNTY",
        "STATE",
        "COMPANY",
        "CHURCH",
        "RELIGIOUS",
        "CHRISTIAN",
        "SERVER",
        "WORKER",
        "MAN",
        "WOMAN",
        "CHILD",
        "PARENT",
        "FAMILY",
        "HOSPITAL",
        "AUTHORITY",
        "OFFICIAL",
        "MINISTER",
        "PRESIDENT",
        "GOVERNOR",
        "MAYOR",
    }
)


def _norm_actor(name: str) -> str:
    text = " ".join(str(name or "").split()).upper()
    if len(text) < 2:
        return ""
    if text.isdigit():
        return ""
    text = _ACTOR_ALIAS.get(text, text)
    return text[:80]


def _to_int(raw: str) -> Optional[int]:
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _to_float(raw: str) -> Optional[float]:
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def extract_gdelt_event(api_raw: Any) -> Optional[Dict[str, Any]]:
    """Return actor/event fields, or None if this is not a GDELT EVENTS payload."""
    if not isinstance(api_raw, dict):
        return None
    has_cols = any(k.startswith("col_") for k in api_raw)
    if not has_cols and "Actor1Name" not in api_raw and "col_6" not in api_raw:
        return None
    actor1 = _norm_actor(_cell(api_raw, "actor1_name"))
    actor2 = _norm_actor(_cell(api_raw, "actor2_name"))
    if not actor1 and not actor2:
        return None
    root = _cell(api_raw, "event_root_code") or (_cell(api_raw, "event_code")[:2])
    if len(root) == 1:
        root = root.zfill(2)
    quad = _to_int(_cell(api_raw, "quad_class"))
    return {
        "actor1_name": actor1,
        "actor1_code": _cell(api_raw, "actor1_code"),
        "actor1_country": _cell(api_raw, "actor1_country").upper()[:3],
        "actor2_name": actor2,
        "actor2_code": _cell(api_raw, "actor2_code"),
        "actor2_country": _cell(api_raw, "actor2_country").upper()[:3],
        "event_code": _cell(api_raw, "event_code"),
        "event_root_code": root[:2],
        "event_root_label": ROOT_LABEL.get(root[:2], ""),
        "quad_class": quad,
        "quad_label": QUAD_LABEL.get(quad or 0, ""),
        "goldstein": _to_float(_cell(api_raw, "goldstein")),
        "num_mentions": _to_int(_cell(api_raw, "num_mentions")),
    }
