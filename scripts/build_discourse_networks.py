#!/usr/bin/env python3
"""Build six discourse networks from the Catholic media corpus.

  1. country_teaching     — ActionGeo country × CST / evangelization theme
  2. theme_cooccurrence   — themes that fire in the same record
  3. outlet_similarity    — outlets/stations/channels with similar theme vectors
  4. diffusion_cascade    — directed country-to-country first-mention lags
  5. gdelt_actors         — GDELT Actor1 → Actor2 (CAMEO / Goldstein)
  6. language_bridge      — EN/ES/PT term pairs (gospel–evangelio–evangelho, …)

One pass over analysis_source_paths(). Writes JSONL + GraphML under data/network/.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

_SCRIPTS = Path(__file__).resolve().parent
ROOT = _SCRIPTS.parent
ANALYSIS = ROOT / "papers" / "rise_education_2026" / "analysis"
for path in (_SCRIPTS, str(ANALYSIS)):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)

from analyze_diffusion import (  # noqa: E402
    CORPUS_START,
    FOCUS_LABELS,
    PROMULGATION,
    load_sidecar_paragraphs,
    news_scan_text,
    record_action_fips,
    record_date,
)
from common.analysis_paths import (  # noqa: E402
    SOURCE_FAMILY,
    americas_fetch_shard_jsonls,
    analysis_source_paths,
    iter_source,
    source_path_list,
)
from common.api_record import domain_from_url  # noqa: E402
from common.evangelization_themes import (  # noqa: E402
    PAPAL_DOCUMENT_LABELS,
    THEME_TO_ACCENTS,
    combined_text,
    infer_record_language,
    match_theme_labels,
    theme_group,
)
from common.gdelt_events import GENERIC_ACTORS, extract_gdelt_event  # noqa: E402
from common.geography import (  # noqa: E402
    collection_region_from_fips,
    fips_country_name,
    un_wesp_development_group,
)
from common.graph_io import write_graph  # noqa: E402
from common.progress import section, write  # noqa: E402
from common.text_normalize import fold_for_match  # noqa: E402

TEXT_CAP = 12_000

TEACHING_FOCUS = frozenset(
    {
        "guadalupe",
        "oscar_romero",
        "aparecida_celam",
        "querida_amazonia",
        "liberation_theology",
        "preferential_option",
        "catholic_social_teaching",
        "base_communities",
        "laudato_si",
        "evangelii_gaudium",
        "fratelli_tutti",
        "evangelio",
        "gospel",
        "mision",
        "mission",
        "immigration",
        "indigenous",
        "eucharist",
        "synod",
        "marian_devotion",
        "inculturation",
        "kerygma",
    }
)

# Secular/diplomatic "mission" swamps small-country rates; keep in the full
# graph but do not use it to rank the distinctive-teaching focus.
GENERIC_TEACHING = frozenset({"mission", "pastoral", "youth", "synod"})

GRAPH_NAMES = (
    "country_teaching",
    "theme_cooccurrence",
    "outlet_similarity",
    "diffusion_cascade",
    "gdelt_actors",
    "language_bridge",
)

# concept → (term_id, language, folded regex)
_BRIDGE_SPEC: Tuple[Tuple[str, Tuple[Tuple[str, str, str], ...]], ...] = (
    (
        "gospel",
        (
            ("gospel", "english", r"\bgospel\b"),
            ("evangelio", "spanish", r"\bevangelio\b"),
            ("evangelho", "portuguese", r"\bevangelho\b"),
        ),
    ),
    (
        "mission",
        (
            ("mission", "english", r"\bmission(?:ary|s)?\b"),
            ("mision", "spanish", r"\bmision(?:ero|es)?\b"),
            ("missao", "portuguese", r"\bmissao\b"),
        ),
    ),
    (
        "eucharist",
        (
            ("eucharist", "english", r"\beucharist\w*\b|\bholy communion\b"),
            ("eucaristia", "spanish", r"\beucaristia\b|\bsanta comunion\b"),
            ("santa_comunhao", "portuguese", r"\bsanta comunhao\b"),
        ),
    ),
    (
        "cst",
        (
            ("catholic_social_teaching", "english", r"\bcatholic social (?:teaching|doctrine)\b"),
            ("doctrina_social", "spanish", r"\bdoctrina social\b"),
            ("doutrina_social", "portuguese", r"\bdoutrina social\b"),
        ),
    ),
    (
        "preferential_option",
        (
            ("preferential_option", "english", r"\bpreferential option\b|\boption for the poor\b"),
            ("opcion_preferencial", "spanish", r"\bopcion preferencial\b|\bopcion por los pobres\b"),
            ("opcao_preferencial", "portuguese", r"\bopcao preferencial\b|\bopcao pelos pobres\b"),
        ),
    ),
    (
        "liberation_theology",
        (
            ("liberation_theology", "english", r"\bliberation theology\b|\btheology of liberation\b"),
            ("teologia_liberacion", "spanish", r"\bteologia de la liberacion\b"),
            ("teologia_libertacao", "portuguese", r"\bteologia da libertacao\b"),
        ),
    ),
    (
        "guadalupe",
        (
            ("our_lady_of_guadalupe", "english", r"\bour lady of guadalupe\b"),
            ("virgen_de_guadalupe", "spanish", r"\bvirgen de guadalupe\b|\bnuestra senora de guadalupe\b"),
            ("nossa_senhora_de_guadalupe", "portuguese", r"\bnossa senhora de guadalupe\b"),
        ),
    ),
    (
        "new_evangelization",
        (
            ("new_evangelization", "english", r"\bnew evangelization\b"),
            ("nueva_evangelizacion", "spanish", r"\bnueva evangelizacion\b"),
            ("nova_evangelizacao", "portuguese", r"\bnova evangelizacao\b"),
        ),
    ),
    (
        "laudato_si",
        (
            ("laudato_si_latin", "latin", r"\blaudato\s+si\b"),
            ("care_for_common_home", "english", r"\bcare for (?:our |the )?common home\b"),
            ("cuidado_casa_comun", "spanish", r"\bcuidado de la casa comun\b"),
            ("cuidado_casa_comum", "portuguese", r"\bcuidado da casa comum\b"),
        ),
    ),
    (
        "evangelii_gaudium",
        (
            ("evangelii_gaudium_latin", "latin", r"\bevangelii gaudium\b"),
            ("joy_of_the_gospel", "english", r"\bjoy of the gospel\b"),
            ("alegria_del_evangelio", "spanish", r"\balegria del evangelio\b"),
            ("alegria_do_evangelho", "portuguese", r"\balegria do evangelho\b"),
        ),
    ),
    (
        "fratelli_tutti",
        (
            ("fratelli_tutti_latin", "latin", r"\bfratelli tutti\b"),
            ("brothers_and_sisters_all", "english", r"\bbrothers and sisters all\b"),
            ("todos_hermanos", "spanish", r"\btodos hermanos\b|\btodos somos hermanos\b"),
            ("todos_irmaos", "portuguese", r"\btodos irmaos\b"),
        ),
    ),
    (
        "catechesis",
        (
            ("catechesis", "english", r"\bcatechesis\b"),
            ("catequesis", "spanish", r"\bcatequesis\b"),
            ("catequese", "portuguese", r"\bcatequese\b"),
        ),
    ),
)


def _compile_bridges() -> List[Tuple[str, str, str, re.Pattern[str]]]:
    out: List[Tuple[str, str, str, re.Pattern[str]]] = []
    for concept, terms in _BRIDGE_SPEC:
        for term_id, lang, pattern in terms:
            out.append((concept, term_id, lang, re.compile(pattern, re.I)))
    return out


BRIDGE_PATTERNS = _compile_bridges()
TERM_CONCEPT = {term_id: concept for concept, term_id, _lang, _pat in BRIDGE_PATTERNS}
TERM_LANG = {term_id: lang for _c, term_id, lang, _pat in BRIDGE_PATTERNS}


def per_1k(n: int, denom: int) -> float:
    return round(1000.0 * n / denom, 2) if denom else 0.0


def smoothed_per_1k(hits: int, n: int, *, prior_hits: float = 0.5, prior_n: float = 80.0) -> float:
    """Shrink noisy small-n rates toward a weak prior."""
    return round(1000.0 * (hits + prior_hits) / (n + prior_n), 2) if n or prior_n else 0.0


def after_promulgation(label: str, when: Optional[date]) -> bool:
    """Drop encyclical hits dated before the document existed (e.g. Fratelli Tutti 2015)."""
    prom = PROMULGATION.get(label)
    if not prom or prom < CORPUS_START:
        return True
    if when is None:
        return True
    return when >= prom


def title_case_actor(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split())


def match_themes_ungated(text: str) -> Set[str]:
    """Union of EN + ES pattern sets so bilingual articles keep both vocabularies."""
    if not text.strip():
        return set()
    return match_theme_labels(text, "english") | match_theme_labels(text, "spanish")


def match_bridge_terms(folded: str) -> Set[str]:
    hits: Set[str] = set()
    for _concept, term_id, _lang, pat in BRIDGE_PATTERNS:
        if pat.search(folded):
            hits.add(term_id)
    return hits


def outlet_from_record(rec: dict, family: str) -> Optional[Tuple[str, str, str]]:
    """Return (item_type, record_id, label) or None."""
    if family == "news":
        domain = domain_from_url(str(rec.get("url") or ""))
        if domain:
            return ("outlet", domain, domain)
        return None
    if family == "tv":
        station = str(rec.get("station") or rec.get("station_id") or "").strip()
        if station:
            return ("station", station, station)
        return None
    if family == "radio":
        station = str(rec.get("station") or "").strip()
        if station:
            return ("station", station, station)
        return None
    if family == "youtube":
        channel_id = str(rec.get("channel_id") or "").strip()
        title = str(rec.get("channel_title") or channel_id).strip()
        if channel_id:
            return ("channel", channel_id, title or channel_id)
    return None


def nid(kind: str, record_id: str) -> str:
    return f"{kind}:{record_id}"


def top_pairs(counter: Counter, n: int = 15) -> List[Dict[str, Any]]:
    rows = []
    for (a, b), w in counter.most_common(n):
        rows.append({"source": a, "target": b, "weight": int(w)})
    return rows


def emit_country_teaching(
    country_n: Counter,
    country_theme: Dict[str, Counter],
    country_lang: Dict[str, Counter],
    *,
    min_country_n: int,
    min_hits: int,
) -> Tuple[List[dict], List[dict], dict]:
    nodes: List[dict] = []
    edges: List[dict] = []
    countries = [f for f, n in country_n.most_common() if n >= min_country_n]
    theme_hits: Counter = Counter()
    for fips in countries:
        for theme, c in country_theme[fips].items():
            if theme in TEACHING_FOCUS:
                theme_hits[theme] += c
    themes = [t for t, c in theme_hits.most_common() if c >= min_hits]
    us_n = int(country_n.get("US") or 0)
    us_rate = {
        theme: per_1k(int(country_theme["US"].get(theme) or 0), us_n) if us_n else 0.0
        for theme in themes
    }
    for fips in countries:
        lang = country_lang.get(fips) or Counter()
        nodes.append(
            {
                "id": nid("country", fips),
                "item_type": "country",
                "label": fips_country_name(fips),
                "fips": fips,
                "region": collection_region_from_fips(fips) or "",
                "un_wesp": un_wesp_development_group(fips),
                "n": int(country_n[fips]),
                "lang_en": int(lang.get("english") or 0),
                "lang_es": int(lang.get("spanish") or 0),
                "lang_pt": int(lang.get("portuguese") or 0),
            }
        )
    for theme in themes:
        nodes.append(
            {
                "id": nid("theme", theme),
                "item_type": "theme",
                "label": theme.replace("_", " "),
                "group": theme_group(theme),
                "papal": theme in PAPAL_DOCUMENT_LABELS,
                "generic": theme in GENERIC_TEACHING,
                "accents": ", ".join(sorted(THEME_TO_ACCENTS.get(theme, ()))),
                "n": int(theme_hits[theme]),
                "us_rate_per_1k": us_rate.get(theme, 0.0),
            }
        )
    for fips in countries:
        n = country_n[fips]
        for theme in themes:
            hits = int(country_theme[fips].get(theme) or 0)
            if hits < min_hits:
                continue
            rate = per_1k(hits, n)
            smooth = smoothed_per_1k(hits, n)
            baseline = us_rate.get(theme) or 0.0
            lift = round(rate / baseline, 2) if baseline else None
            distinctive = (
                theme not in GENERIC_TEACHING
                and n >= 150
                and hits >= 8
                and lift is not None
                and lift >= 2.0
            )
            edges.append(
                {
                    "source": nid("country", fips),
                    "target": nid("theme", theme),
                    "type": "teaches",
                    "weight": hits,
                    "rate_per_1k": rate,
                    "smoothed_per_1k": smooth,
                    "us_rate_per_1k": baseline,
                    "lift_vs_us": lift if lift is not None else 0.0,
                    "distinctive": distinctive,
                }
            )
    edges.sort(
        key=lambda e: (
            0 if e.get("distinctive") else 1,
            -(float(e.get("lift_vs_us") or 0)),
            -int(e["weight"]),
        )
    )

    def _row(edge: dict) -> dict:
        return {
            "country": fips_country_name(edge["source"].split(":", 1)[1]),
            "theme": edge["target"].split(":", 1)[1],
            "rate_per_1k": edge["rate_per_1k"],
            "smoothed_per_1k": edge["smoothed_per_1k"],
            "lift_vs_us": edge["lift_vs_us"],
            "hits": edge["weight"],
        }

    distinctive = [e for e in edges if e.get("distinctive")]
    summary = {
        "description": (
            "Bipartite ActionGeo country × teaching theme. Rank by lift vs U.S. "
            "rate (not raw /1k, which overweights Haiti 'mission'). "
            "distinctive = non-generic theme, n≥150, hits≥8, lift≥2."
        ),
        "min_country_n": min_country_n,
        "min_hits": min_hits,
        "top_lift_vs_us": [_row(e) for e in distinctive[:20]],
        "top_rate_edges": [
            _row(e)
            for e in sorted(edges, key=lambda x: -float(x["rate_per_1k"]))[:12]
        ],
    }
    return nodes, edges, summary


def emit_theme_cooccurrence(
    theme_n: Counter,
    cooccur: Counter,
    cooccur_lang: Dict[str, Counter],
    n_with_themes: int,
    *,
    min_count: int,
    max_edges: int,
    min_lift: float = 1.25,
) -> Tuple[List[dict], List[dict], dict]:
    scored: List[Tuple[float, str, str, int]] = []
    for (a, b), w in cooccur.items():
        if w < min_count:
            continue
        na, nb = theme_n[a], theme_n[b]
        lift = (w * n_with_themes) / (na * nb) if na and nb and n_with_themes else 0.0
        scored.append((lift, a, b, int(w)))
    scored.sort(key=lambda row: (-row[0], -row[3]))
    by_lift = [row for row in scored if row[0] >= min_lift][:max_edges]
    if not by_lift:
        by_lift = scored[: max(50, max_edges // 4)]
    used = {a for _l, a, b, _w in by_lift} | {b for _l, a, b, _w in by_lift}
    nodes = []
    for theme in sorted(used):
        nodes.append(
            {
                "id": nid("theme", theme),
                "item_type": "theme",
                "label": theme.replace("_", " "),
                "group": theme_group(theme),
                "papal": theme in PAPAL_DOCUMENT_LABELS,
                "accents": ", ".join(sorted(THEME_TO_ACCENTS.get(theme, ()))),
                "n": int(theme_n[theme]),
            }
        )
    edges = []
    for lift, a, b, w in by_lift:
        edges.append(
            {
                "source": nid("theme", a),
                "target": nid("theme", b),
                "type": "cooccurs",
                "weight": w,
                "lift": round(lift, 3),
                "n_en": int(cooccur_lang["english"].get((a, b), 0)),
                "n_es": int(cooccur_lang["spanish"].get((a, b), 0)),
                "n_pt": int(cooccur_lang["portuguese"].get((a, b), 0)),
            }
        )
    papal_pairs = [
        {
            "source": a,
            "target": b,
            "weight": w,
            "lift": round(lift, 3),
        }
        for lift, a, b, w in scored
        if a in PAPAL_DOCUMENT_LABELS and b in PAPAL_DOCUMENT_LABELS
    ]
    papal_pairs.sort(key=lambda r: (-r["lift"], -r["weight"]))
    summary = {
        "description": (
            "Undirected theme co-occurrence. Edges kept when lift ≥ "
            f"{min_lift} (P(a,b)/(P(a)P(b))); rank by lift, not raw count."
        ),
        "n_records_with_theme": n_with_themes,
        "min_count": min_count,
        "min_lift": min_lift,
        "top_by_lift": [
            {"source": a, "target": b, "weight": w, "lift": round(lift, 3)}
            for lift, a, b, w in by_lift[:15]
        ],
        "top_by_count": [
            {"source": a, "target": b, "weight": w, "lift": round(lift, 3)}
            for lift, a, b, w in sorted(scored, key=lambda r: -r[3])[:10]
        ],
        "top_papal_pairs": papal_pairs[:12],
    }
    return nodes, edges, summary


def emit_outlet_similarity(
    outlet_n: Counter,
    outlet_theme: Dict[str, Counter],
    outlet_meta: Dict[str, dict],
    outlet_lang: Dict[str, Counter],
    themes: Sequence[str],
    *,
    min_articles: int,
    min_sim: float,
    max_k: int,
    min_themes: int = 4,
) -> Tuple[List[dict], List[dict], dict]:
    ids = [
        oid
        for oid, n in outlet_n.most_common()
        if n >= min_articles and len(outlet_theme.get(oid) or {}) >= min_themes
    ]
    if len(ids) < 2 or not themes:
        return [], [], {"description": "Too few outlets after filters.", "n_outlets": len(ids)}
    index = {t: i for i, t in enumerate(themes)}
    mat = np.zeros((len(ids), len(themes)), dtype=np.float64)
    for row, oid in enumerate(ids):
        n = max(outlet_n[oid], 1)
        for theme, c in outlet_theme[oid].items():
            col = index.get(theme)
            if col is not None:
                mat[row, col] = c / n
    df = (mat > 0).sum(axis=0)
    idf = np.log((len(ids) + 1.0) / (df + 1.0)) + 1.0
    tfidf = mat * idf
    norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    sim = (tfidf / norms) @ (tfidf / norms).T
    nodes = []
    for oid in ids:
        meta = outlet_meta[oid]
        lang = outlet_lang.get(oid) or Counter()
        nodes.append(
            {
                "id": oid,
                "item_type": meta.get("item_type") or "outlet",
                "label": meta.get("label") or oid,
                "family": meta.get("family") or "",
                "n": int(outlet_n[oid]),
                "n_themes": len(outlet_theme[oid]),
                "lang_en": int(lang.get("english") or 0),
                "lang_es": int(lang.get("spanish") or 0),
                "lang_pt": int(lang.get("portuguese") or 0),
            }
        )
    edges: List[dict] = []
    seen_pairs: Set[Tuple[int, int]] = set()
    n = len(ids)
    for i in range(n):
        row = sim[i]
        order = np.argsort(row)[::-1]
        kept = 0
        fam_i = outlet_meta[ids[i]].get("family")
        for j in order:
            if i == j:
                continue
            score = float(row[j])
            fam_j = outlet_meta[ids[j]].get("family")
            if fam_i and fam_j and fam_i != fam_j:
                score *= 0.85
            if score < min_sim:
                if fam_i == fam_j:
                    break
                continue
            pair = (i, j) if i < j else (j, i)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                overlap = np.minimum(tfidf[pair[0]], tfidf[pair[1]])
                top_idx = np.argsort(overlap)[::-1][:3]
                shared = [themes[k] for k in top_idx if overlap[k] > 0]
                edges.append(
                    {
                        "source": ids[pair[0]],
                        "target": ids[pair[1]],
                        "type": "similar_themes",
                        "weight": round(float(sim[pair[0], pair[1]]), 4),
                        "same_family": fam_i == fam_j,
                        "shared_themes": ", ".join(shared),
                    }
                )
            kept += 1
            if kept >= max_k:
                break
    edges.sort(key=lambda e: -float(e["weight"]))
    summary = {
        "description": (
            "TF-IDF cosine of theme-rate vectors (ubiquitous 'mission' is "
            "downweighted). Outlets need ≥"
            f"{min_themes} distinct themes; cross-modality pairs are penalized."
        ),
        "min_articles": min_articles,
        "min_themes": min_themes,
        "min_sim": min_sim,
        "max_neighbors": max_k,
        "n_outlets": len(ids),
        "top_edges": [
            {
                "source": outlet_meta.get(e["source"], {}).get("label") or e["source"],
                "target": outlet_meta.get(e["target"], {}).get("label") or e["target"],
                "weight": e["weight"],
                "shared_themes": e.get("shared_themes"),
                "same_family": e.get("same_family"),
            }
            for e in edges[:15]
        ],
    }
    return nodes, edges, summary


def emit_diffusion_cascade(
    first_country: Dict[str, Dict[str, date]],
    hits_country: Dict[str, Counter],
    *,
    min_hits: int,
    max_lag_days: int,
) -> Tuple[List[dict], List[dict], dict]:
    country_topics: Dict[str, Set[str]] = defaultdict(set)
    edges: List[dict] = []
    examples: List[dict] = []
    for topic in sorted(FOCUS_LABELS):
        by_c = first_country.get(topic) or {}
        ranked = []
        for fips, when in by_c.items():
            hits = int(hits_country[topic].get(fips) or 0)
            if hits < min_hits:
                continue
            ranked.append((when, fips, hits))
        ranked.sort(key=lambda row: (row[0], -row[2]))
        if len(ranked) < 2:
            continue
        for when, fips, _hits in ranked:
            country_topics[fips].add(topic)
        origin_when, origin, origin_hits = ranked[0]
        prom = PROMULGATION.get(topic)
        left_censored = bool(prom and prom < CORPUS_START)
        days_after = (origin_when - prom).days if prom and not left_censored else None
        for prev, nxt in zip(ranked, ranked[1:]):
            lag = (nxt[0] - prev[0]).days
            if lag > max_lag_days:
                continue
            edges.append(
                {
                    "source": nid("country", prev[1]),
                    "target": nid("country", nxt[1]),
                    "type": "followed_by",
                    "topic": topic,
                    "weight": max(1, max_lag_days - lag),
                    "lag_days": lag,
                    "source_date": prev[0].isoformat(),
                    "target_date": nxt[0].isoformat(),
                }
            )
        for when, fips, hits in ranked[1:]:
            lag = (when - origin_when).days
            if lag > max_lag_days:
                continue
            edges.append(
                {
                    "source": nid("country", origin),
                    "target": nid("country", fips),
                    "type": "diffuses_from",
                    "topic": topic,
                    "weight": max(1, max_lag_days - lag),
                    "lag_days": lag,
                    "source_date": origin_when.isoformat(),
                    "target_date": when.isoformat(),
                    "origin_hits": origin_hits,
                    "target_hits": hits,
                }
            )
        if topic in {
            "laudato_si",
            "guadalupe",
            "aparecida_celam",
            "oscar_romero",
            "evangelii_gaudium",
            "fratelli_tutti",
        }:
            examples.append(
                {
                    "topic": topic,
                    "origin": fips_country_name(origin),
                    "origin_date": origin_when.isoformat(),
                    "promulgation": prom.isoformat() if prom else None,
                    "days_after_promulgation": days_after,
                    "left_censored": left_censored,
                    "followers": [
                        {
                            "country": fips_country_name(f),
                            "date": d.isoformat(),
                            "lag_days": (d - origin_when).days,
                            "hits": h,
                        }
                        for d, f, h in ranked[1:8]
                    ],
                }
            )
    nodes = []
    for fips, topics in sorted(country_topics.items(), key=lambda kv: -len(kv[1])):
        nodes.append(
            {
                "id": nid("country", fips),
                "item_type": "country",
                "label": fips_country_name(fips),
                "fips": fips,
                "region": collection_region_from_fips(fips) or "",
                "un_wesp": un_wesp_development_group(fips),
                "n_topics": len(topics),
                "topics": ", ".join(sorted(topics)[:12]),
            }
        )
    summary = {
        "description": (
            "Directed first-mention cascade after each document's promulgation "
            "(pre-promulgation lexicon hits are dropped). Chain (followed_by) plus "
            "star from the earliest country (diffuses_from). Weight = max_lag − lag_days."
        ),
        "min_hits": min_hits,
        "max_lag_days": max_lag_days,
        "n_topics": len({e["topic"] for e in edges}),
        "examples": examples,
    }
    return nodes, edges, summary


def emit_gdelt_actors(
    pair_n: Counter,
    pair_goldstein: Dict[Tuple[str, str], float],
    pair_quad: Dict[Tuple[str, str], Counter],
    pair_root: Dict[Tuple[str, str], Counter],
    actor_meta: Dict[str, dict],
    actor_count: Counter,
    *,
    min_weight: int,
    max_edges: int,
) -> Tuple[List[dict], List[dict], dict]:
    kept = [(pair, w) for pair, w in pair_n.most_common() if w >= min_weight][:max_edges]
    used = {a for (a, b), _ in kept} | {b for (a, b), _ in kept}
    nodes = []
    for name in sorted(used, key=lambda x: -actor_count[x]):
        meta = actor_meta.get(name) or {}
        nodes.append(
            {
                "id": nid("actor", name.lower().replace(" ", "_")),
                "item_type": "actor",
                "label": title_case_actor(name),
                "gdelt_name": name,
                "n": int(actor_count[name]),
                "country": meta.get("country") or "",
                "code": meta.get("code") or "",
                "generic": name in GENERIC_ACTORS,
            }
        )
    id_of = {name: nid("actor", name.lower().replace(" ", "_")) for name in used}
    edges = []
    mean_g = []
    for (a, b), w in kept:
        g_sum = pair_goldstein.get((a, b), 0.0)
        mean = g_sum / w if w else 0.0
        mean_g.append(mean)
        quad = pair_quad[(a, b)]
        root = pair_root[(a, b)]
        top_quad, _ = quad.most_common(1)[0] if quad else ("", 0)
        top_root, _ = root.most_common(1)[0] if root else ("", 0)
        polarity = "cooperation" if mean > 0.15 else ("conflict" if mean < -0.15 else "neutral")
        edges.append(
            {
                "source": id_of[a],
                "target": id_of[b],
                "type": "cameo_event",
                "weight": int(w),
                "mean_goldstein": round(mean, 3),
                "signed_weight": round(mean * math.log1p(w), 3),
                "polarity": polarity,
                "color": "#16A34A" if polarity == "cooperation" else ("#DC2626" if polarity == "conflict" else "#9CA3AF"),
                "top_quad": str(top_quad),
                "top_root": str(top_root),
                "generic_endpoint": a in GENERIC_ACTORS or b in GENERIC_ACTORS,
            }
        )
    coop = sum(1 for e in edges if float(e["mean_goldstein"]) > 0)
    conflict = sum(1 for e in edges if float(e["mean_goldstein"]) < 0)
    named = [(pair, w) for pair, w in kept if pair[0] not in GENERIC_ACTORS and pair[1] not in GENERIC_ACTORS]
    summary = {
        "description": (
            "Directed GDELT Actor1→Actor2 on the Catholic-keyword event slice. "
            "Pope/Vatican aliases merged. mean_goldstein > 0 is cooperation (green); "
            "< 0 is conflict (red). Focus graph drops generic hubs (Catholic, School, …)."
        ),
        "min_weight": min_weight,
        "n_actor_mentions": int(sum(actor_count.values())),
        "n_directed_pairs_raw": len(pair_n),
        "cooperative_edges": coop,
        "conflict_edges": conflict,
        "mean_goldstein_kept": round(float(np.mean(mean_g)), 3) if mean_g else 0.0,
        "top_edges": [
            {
                "source": title_case_actor(a),
                "target": title_case_actor(b),
                "weight": int(w),
                "mean_goldstein": round(pair_goldstein[(a, b)] / w, 3) if w else 0.0,
            }
            for (a, b), w in kept[:12]
        ],
        "top_named_edges": [
            {
                "source": title_case_actor(a),
                "target": title_case_actor(b),
                "weight": int(w),
                "mean_goldstein": round(pair_goldstein[(a, b)] / w, 3) if w else 0.0,
            }
            for (a, b), w in named[:12]
        ],
    }
    return nodes, edges, summary


def emit_language_bridge(
    term_n: Counter,
    cooccur: Counter,
    translation: Counter,
    term_country: Dict[str, Counter],
    concept_country_term: Dict[str, Dict[str, Counter]],
    *,
    min_count: int,
) -> Tuple[List[dict], List[dict], dict]:
    used = {t for t, c in term_n.items() if c > 0}
    nodes = []
    concepts = sorted({TERM_CONCEPT[t] for t in used if t in TERM_CONCEPT})
    for concept in concepts:
        nodes.append(
            {
                "id": nid("concept", concept),
                "item_type": "concept",
                "label": concept.replace("_", " "),
                "n": int(sum(term_n[t] for t in used if TERM_CONCEPT.get(t) == concept)),
            }
        )
    for term_id in sorted(used):
        countries = term_country.get(term_id) or Counter()
        top_c = countries.most_common(3)
        nodes.append(
            {
                "id": nid("term", term_id),
                "item_type": "term",
                "label": term_id.replace("_", " "),
                "concept": TERM_CONCEPT.get(term_id, ""),
                "language": TERM_LANG.get(term_id, ""),
                "n": int(term_n[term_id]),
                "top_countries": ", ".join(fips_country_name(f) for f, _ in top_c),
            }
        )
    edges = []
    for term_id in used:
        concept = TERM_CONCEPT.get(term_id)
        if not concept:
            continue
        edges.append(
            {
                "source": nid("concept", concept),
                "target": nid("term", term_id),
                "type": "realized_as",
                "weight": int(term_n[term_id]),
                "language": TERM_LANG.get(term_id, ""),
            }
        )
    for (a, b), w in translation.most_common():
        if w < min_count or a not in used or b not in used:
            continue
        edges.append(
            {
                "source": nid("term", a),
                "target": nid("term", b),
                "type": "translation_bridge",
                "weight": int(w),
                "concept": TERM_CONCEPT.get(a) or TERM_CONCEPT.get(b) or "",
            }
        )
    for (a, b), w in cooccur.most_common():
        if w < min_count or a not in used or b not in used:
            continue
        if TERM_CONCEPT.get(a) == TERM_CONCEPT.get(b):
            continue
        edges.append(
            {
                "source": nid("term", a),
                "target": nid("term", b),
                "type": "cooccur",
                "weight": int(w),
            }
        )
    country_n: Counter = Counter()
    for term_id, counts in term_country.items():
        country_n.update(counts)
    prefers_rows: List[dict] = []
    for fips, n in country_n.most_common(30):
        nodes.append(
            {
                "id": nid("country", fips),
                "item_type": "country",
                "label": fips_country_name(fips),
                "fips": fips,
                "n": int(n),
                "region": collection_region_from_fips(fips) or "",
                "un_wesp": un_wesp_development_group(fips),
            }
        )
        for concept, by_country in concept_country_term.items():
            counts = by_country.get(fips) or Counter()
            if not counts:
                continue
            # One prefers edge per language, not only the global argmax
            # (English wire would otherwise hide misión / evangelio).
            by_lang: dict[str, tuple[str, int]] = {}
            for term_id, w in counts.items():
                lang = TERM_LANG.get(term_id) or "other"
                prev = by_lang.get(lang)
                if prev is None or w > prev[1]:
                    by_lang[lang] = (term_id, int(w))
            total = int(sum(counts.values()))
            for lang, (term_id, w) in by_lang.items():
                if w < min_count:
                    continue
                share = round(w / total, 3) if total else 0.0
                edges.append(
                    {
                        "source": nid("country", fips),
                        "target": nid("term", term_id),
                        "type": "prefers",
                        "weight": int(w),
                        "share": share,
                        "concept": concept,
                        "language": lang,
                    }
                )
                if lang in {"spanish", "portuguese"} or (
                    lang == "english" and share >= 0.7 and fips in {"US", "CA"}
                ):
                    prefers_rows.append(
                        {
                            "country": fips_country_name(fips),
                            "concept": concept,
                            "term": term_id,
                            "language": lang,
                            "share": share,
                            "n": int(w),
                        }
                    )
        for term_id, counts in term_country.items():
            w = int(counts.get(fips) or 0)
            if w < max(min_count, 5):
                continue
            edges.append(
                {
                    "source": nid("term", term_id),
                    "target": nid("country", fips),
                    "type": "used_in",
                    "weight": w,
                }
            )
    prefers_rows.sort(key=lambda r: (-r["share"], -r["n"]))
    summary = {
        "description": (
            "Concept nodes tie EN/ES/PT terms even when they never co-occur. "
            "prefers = a country's dominant wording for a concept (the register graph). "
            "translation_bridge = same article, two languages."
        ),
        "min_count": min_count,
        "term_counts": dict(term_n.most_common()),
        "top_translation_bridges": top_pairs(translation, 15),
        "country_prefers": prefers_rows[:20],
        "top_cross_concept": top_pairs(cooccur, 8),
    }
    return nodes, edges, summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build six discourse networks from the corpus.")
    p.add_argument(
        "--output-dir",
        "-o",
        default=str(ROOT / "data" / "network"),
        help="Root directory for the six graph folders.",
    )
    p.add_argument(
        "--graphs",
        nargs="*",
        default=list(GRAPH_NAMES),
        help="Subset of graphs to write (default: all six).",
    )
    p.add_argument("--max-records", type=int, default=0, help="Stop after N records (0 = all).")
    p.add_argument("--skip-sidecar", action="store_true", help="Do not join Americas fetch-shard paragraphs.")
    p.add_argument("--min-country-n", type=int, default=80)
    p.add_argument("--min-theme-hits", type=int, default=2)
    p.add_argument("--min-cooccur", type=int, default=8)
    p.add_argument("--min-lift", type=float, default=1.25)
    p.add_argument("--max-cooccur-edges", type=int, default=1500)
    p.add_argument("--min-outlet-articles", type=int, default=20)
    p.add_argument("--min-outlet-themes", type=int, default=4)
    p.add_argument("--min-outlet-sim", type=float, default=0.32)
    p.add_argument("--outlet-neighbors", type=int, default=8)
    p.add_argument("--diffusion-min-hits", type=int, default=2)
    p.add_argument("--diffusion-max-lag", type=int, default=365)
    p.add_argument("--actor-min-weight", type=int, default=5)
    p.add_argument("--actor-max-edges", type=int, default=4000)
    p.add_argument("--bridge-min-count", type=int, default=2)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    wanted = set(args.graphs or GRAPH_NAMES)
    unknown = wanted - set(GRAPH_NAMES)
    if unknown:
        raise SystemExit(f"Unknown --graphs: {sorted(unknown)}")

    section("Discourse networks")
    paths = analysis_source_paths(ROOT)
    sidecar: Dict[str, str] = {}
    if not args.skip_sidecar:
        sidecar = load_sidecar_paragraphs(americas_fetch_shard_jsonls(ROOT))

    country_n: Counter = Counter()
    country_theme: Dict[str, Counter] = defaultdict(Counter)
    country_lang: Dict[str, Counter] = defaultdict(Counter)
    theme_n: Counter = Counter()
    cooccur: Counter = Counter()
    cooccur_lang: Dict[str, Counter] = defaultdict(Counter)
    outlet_n: Counter = Counter()
    outlet_theme: Dict[str, Counter] = defaultdict(Counter)
    outlet_meta: Dict[str, dict] = {}
    outlet_lang: Dict[str, Counter] = defaultdict(Counter)
    first_country: Dict[str, Dict[str, date]] = defaultdict(dict)
    hits_country: Dict[str, Counter] = defaultdict(Counter)
    pair_n: Counter = Counter()
    pair_goldstein: Dict[Tuple[str, str], float] = defaultdict(float)
    pair_quad: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    pair_root: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    actor_meta: Dict[str, dict] = {}
    actor_count: Counter = Counter()
    term_n: Counter = Counter()
    bridge_cooccur: Counter = Counter()
    bridge_translation: Counter = Counter()
    term_country: Dict[str, Counter] = defaultdict(Counter)
    concept_country_term: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))

    n_scanned = n_text = n_geo = n_theme_rows = n_actors = n_bridges = 0
    seen_news: Set[str] = set()
    cap = args.max_records or None

    news_keys = [k for k, fam in SOURCE_FAMILY.items() if fam == "news"]
    other_keys = [k for k, fam in SOURCE_FAMILY.items() if fam != "news"]
    stop = False
    for key in news_keys + other_keys:
        if stop:
            break
        path_val = paths.get(key)
        if not path_val or not source_path_list(path_val):
            continue
        family = SOURCE_FAMILY[key]
        is_news = family == "news"
        for rec in iter_source(path_val, desc=f"Networks {key}"):
            if cap is not None and n_scanned >= cap:
                stop = True
                break
            n_scanned += 1

            if is_news:
                ev = extract_gdelt_event(rec.get("api_raw"))
                if ev:
                    n_actors += 1
                    a1, a2 = ev["actor1_name"], ev["actor2_name"]
                    if a1:
                        actor_count[a1] += 1
                        actor_meta.setdefault(a1, {"country": ev["actor1_country"], "code": ev["actor1_code"]})
                    if a2:
                        actor_count[a2] += 1
                        actor_meta.setdefault(a2, {"country": ev["actor2_country"], "code": ev["actor2_code"]})
                    if a1 and a2 and a1 != a2:
                        pair = (a1, a2)
                        pair_n[pair] += 1
                        if ev["goldstein"] is not None:
                            pair_goldstein[pair] += ev["goldstein"]
                        if ev["quad_label"]:
                            pair_quad[pair][ev["quad_label"]] += 1
                        if ev["event_root_label"]:
                            pair_root[pair][ev["event_root_label"]] += 1

            url = str(rec.get("url") or rec.get("record_id") or "")
            if is_news and url:
                if url in seen_news:
                    continue
                seen_news.add(url)
                if not rec.get("paragraph_text"):
                    extra = sidecar.get(url)
                    if extra:
                        rec = dict(rec)
                        rec["paragraph_text"] = extra

            text = (news_scan_text(rec) if is_news else (combined_text(rec) or ""))[:TEXT_CAP]
            if not text.strip():
                continue
            n_text += 1
            lang = infer_record_language(rec, source_hint=key)
            fips = record_action_fips(rec, source_hint=key) if is_news else ""
            when = record_date(rec) if is_news else None
            if fips:
                n_geo += 1
                country_n[fips] += 1
                country_lang[fips][lang] += 1

            themes = match_themes_ungated(text)
            if when:
                themes = {
                    t
                    for t in themes
                    if t not in PAPAL_DOCUMENT_LABELS or after_promulgation(t, when)
                }
            if themes:
                n_theme_rows += 1
                theme_n.update(themes)
                for a, b in combinations(sorted(themes), 2):
                    cooccur[(a, b)] += 1
                    cooccur_lang[lang][(a, b)] += 1
                if fips:
                    for label in themes:
                        if label in TEACHING_FOCUS or label in FOCUS_LABELS:
                            country_theme[fips][label] += 1
                            hits_country[label][fips] += 1
                            if when:
                                prev = first_country[label].get(fips)
                                if prev is None or when < prev:
                                    first_country[label][fips] = when

            outlet = outlet_from_record(rec, family)
            if outlet and themes:
                item_type, record_id, label = outlet
                oid = nid(item_type, record_id)
                outlet_n[oid] += 1
                outlet_theme[oid].update(themes)
                outlet_lang[oid][lang] += 1
                outlet_meta.setdefault(
                    oid,
                    {"item_type": item_type, "label": label, "family": family},
                )

            folded = fold_for_match(text)
            terms = match_bridge_terms(folded)
            if terms:
                n_bridges += 1
                term_n.update(terms)
                if fips:
                    for t in terms:
                        term_country[t][fips] += 1
                        concept = TERM_CONCEPT.get(t)
                        if concept:
                            concept_country_term[concept][fips][t] += 1
                for a, b in combinations(sorted(terms), 2):
                    bridge_cooccur[(a, b)] += 1
                    if TERM_CONCEPT.get(a) and TERM_CONCEPT.get(a) == TERM_CONCEPT.get(b):
                        if TERM_LANG.get(a) != TERM_LANG.get(b):
                            bridge_translation[(a, b)] += 1
        if cap is not None and n_scanned >= cap:
            break

    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    written: Dict[str, dict] = {}

    if "country_teaching" in wanted:
        nodes, edges, summary = emit_country_teaching(
            country_n,
            country_theme,
            country_lang,
            min_country_n=args.min_country_n,
            min_hits=args.min_theme_hits,
        )
        written["country_teaching"] = write_graph(
            out_root / "country_teaching",
            nodes=nodes,
            edges=edges,
            summary=summary,
            focus_key="lift_vs_us",
            focus_n=36,
            focus_edge_types=["teaches"],
            focus_exclude_ids={nid("theme", t) for t in GENERIC_TEACHING},
            layout="bipartite",
        )
        write(f"country_teaching: {len(nodes):,} nodes / {len(edges):,} edges")

    if "theme_cooccurrence" in wanted:
        nodes, edges, summary = emit_theme_cooccurrence(
            theme_n,
            cooccur,
            cooccur_lang,
            n_theme_rows,
            min_count=args.min_cooccur,
            max_edges=args.max_cooccur_edges,
            min_lift=args.min_lift,
        )
        written["theme_cooccurrence"] = write_graph(
            out_root / "theme_cooccurrence",
            nodes=nodes,
            edges=edges,
            summary=summary,
            focus_key="lift",
            focus_n=40,
        )
        write(f"theme_cooccurrence: {len(nodes):,} nodes / {len(edges):,} edges")

    if "outlet_similarity" in wanted:
        theme_axis = [t for t, _c in theme_n.most_common(80)]
        nodes, edges, summary = emit_outlet_similarity(
            outlet_n,
            outlet_theme,
            outlet_meta,
            outlet_lang,
            theme_axis,
            min_articles=args.min_outlet_articles,
            min_sim=args.min_outlet_sim,
            max_k=args.outlet_neighbors,
            min_themes=args.min_outlet_themes,
        )
        written["outlet_similarity"] = write_graph(
            out_root / "outlet_similarity",
            nodes=nodes,
            edges=edges,
            summary=summary,
            focus_n=40,
        )
        write(f"outlet_similarity: {len(nodes):,} nodes / {len(edges):,} edges")

    if "diffusion_cascade" in wanted:
        nodes, edges, summary = emit_diffusion_cascade(
            first_country,
            hits_country,
            min_hits=args.diffusion_min_hits,
            max_lag_days=args.diffusion_max_lag,
        )
        written["diffusion_cascade"] = write_graph(
            out_root / "diffusion_cascade",
            nodes=nodes,
            edges=edges,
            summary=summary,
            directed=True,
            focus_key="weight",
            focus_n=50,
            focus_edge_types=["diffuses_from"],
        )
        write(f"diffusion_cascade: {len(nodes):,} nodes / {len(edges):,} edges")

    if "gdelt_actors" in wanted:
        nodes, edges, summary = emit_gdelt_actors(
            pair_n,
            pair_goldstein,
            pair_quad,
            pair_root,
            actor_meta,
            actor_count,
            min_weight=args.actor_min_weight,
            max_edges=args.actor_max_edges,
        )
        written["gdelt_actors"] = write_graph(
            out_root / "gdelt_actors",
            nodes=nodes,
            edges=edges,
            summary=summary,
            directed=True,
            focus_key="weight",
            focus_n=40,
            focus_exclude_ids={
                nid("actor", name.lower().replace(" ", "_"))
                for name in GENERIC_ACTORS
            },
        )
        write(f"gdelt_actors: {len(nodes):,} nodes / {len(edges):,} edges")

    if "language_bridge" in wanted:
        nodes, edges, summary = emit_language_bridge(
            term_n,
            bridge_cooccur,
            bridge_translation,
            term_country,
            concept_country_term,
            min_count=args.bridge_min_count,
        )
        written["language_bridge"] = write_graph(
            out_root / "language_bridge",
            nodes=nodes,
            edges=edges,
            summary=summary,
            focus_key="share",
            focus_n=40,
            focus_edge_types=["prefers", "realized_as", "translation_bridge"],
        )
        write(f"language_bridge: {len(nodes):,} nodes / {len(edges):,} edges")

    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_scanned": n_scanned,
        "records_with_text": n_text,
        "news_with_actiongeo": n_geo,
        "records_with_theme": n_theme_rows,
        "gdelt_events_with_actor": n_actors,
        "records_with_bridge_term": n_bridges,
        "max_records": args.max_records or None,
        "graphs": {name: {"nodes": g["node_count"], "edges": g["edge_count"]} for name, g in written.items()},
        "output_dir": str(out_root),
    }
    (out_root / "summary.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write(
        f"Wrote {len(written)} graph(s) under {out_root}  "
        f"scanned={n_scanned:,}  text={n_text:,}  geo={n_geo:,}  actors={n_actors:,}"
    )


if __name__ == "__main__":
    main()
