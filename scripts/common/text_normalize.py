"""Accent folding + encyclical / keyword spelling variants for collection & matching."""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Sequence, Set

from common.cst_papal_documents import cst_document_titles

# Apostrophe / acute forms often seen with Laudato Si'
_APOSTROPHES = ("'", "\u2019", "\u2018", "\u00B4", "`")


def fold_accents(text: str) -> str:
    """NFKD + strip combining marks (é→e, ñ→n, Sí→Si). Case unchanged."""
    if not text:
        return ""
    nk = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in nk if not unicodedata.combining(ch))


def fold_for_match(text: str) -> str:
    """Accent-fold + casefold for stable matching."""
    return fold_accents(text).casefold()


# Canonical Latin titles → extra query spellings (apostrophes, accents, vernacular).
# Keep queries distinctive enough for GDELT/YouTube (no 1–2 letter abbreviations).
_ENCYCLICAL_EXTRA: Dict[str, List[str]] = {
    "Rerum Novarum": [
        "Rerum Novarum",
        "of new things",
        "sobre la condición de los obreros",
        "sobre la condicion de los obreros",
        "sobre a condição dos operários",
        "sobre a condicao dos operarios",
    ],
    "Quadragesimo Anno": [
        "Quadragesimo Anno",
        "fortieth year",
        "en el cuadragésimo año",
        "en el cuadragesimo ano",
        "no quadragésimo ano",
        "no quadragesimo ano",
    ],
    "Divini Redemptoris": [
        "Divini Redemptoris",
    ],
    "Mater et Magistra": [
        "Mater et Magistra",
        "Mother and Teacher",
        "madre y maestra",
        "mãe e mestra",
        "mae e mestra",
    ],
    "Pacem in Terris": [
        "Pacem in Terris",
        "Peace on Earth",
        "paz en la tierra",
        "paz na terra",
    ],
    "Populorum Progressio": [
        "Populorum Progressio",
        "On the Development of Peoples",
        "el desarrollo de los pueblos",
        "o desenvolvimento dos povos",
    ],
    "Octogesima Adveniens": [
        "Octogesima Adveniens",
        "A Call to Action",
    ],
    "Evangelii Nuntiandi": [
        "Evangelii Nuntiandi",
        "Evangelization in the Modern World",
    ],
    "Laborem Exercens": [
        "Laborem Exercens",
        "On Human Work",
        "sobre el trabajo humano",
        "sobre o trabalho humano",
    ],
    "Familiaris Consortio": [
        "Familiaris Consortio",
        "On the Role of the Christian Family",
        "la familia cristiana",
    ],
    "Sollicitudo Rei Socialis": [
        "Sollicitudo Rei Socialis",
        "On Social Concern",
        "la preocupación social",
        "la preocupacion social",
    ],
    "Christifideles Laici": [
        "Christifideles Laici",
        "Christifideles laici",
        "vocation of the lay faithful",
    ],
    "Redemptoris Missio": [
        "Redemptoris Missio",
        "Mission of the Redeemer",
    ],
    "Centesimus Annus": [
        "Centesimus Annus",
        "hundredth year",
        "centenario de Rerum Novarum",
    ],
    "Evangelium Vitae": [
        "Evangelium Vitae",
        "Gospel of Life",
        "evangelio de la vida",
        "evangelho da vida",
    ],
    "Fides et Ratio": [
        "Fides et Ratio",
        "Faith and Reason",
        "fe y razón",
        "fe y razon",
        "fé e razão",
        "fe e razao",
    ],
    "Deus Caritas Est": [
        "Deus Caritas Est",
        "God is Love",
        "Dios es amor",
        "Deus é amor",
        "Deus e amor",
    ],
    "Spe Salvi": [
        "Spe Salvi",
        "Saved in Hope",
        "salvados en esperanza",
        "salvos na esperança",
        "salvos na esperanca",
    ],
    "Caritas in Veritate": [
        "Caritas in Veritate",
        "Charity in Truth",
        "caridad en la verdad",
        "caridade na verdade",
    ],
    "Lumen Fidei": [
        "Lumen Fidei",
        "Light of Faith",
        "luz de la fe",
        "luz da fé",
        "luz da fe",
    ],
    "Evangelii Gaudium": [
        "Evangelii Gaudium",
        "Joy of the Gospel",
        "alegría del evangelio",
        "alegria del evangelio",
        "alegria do Evangelho",
        "alegria do evangelho",
    ],
    "Laudato Si": [
        "Laudato Si",
        "Laudato Si'",
        "Laudato Si’",
        "Laudato Sí",
        "Laudato Sí'",
        "Laudato Si´",
        "Laudato Si`",
        "care for our common home",
        "cuidado de la casa común",
        "cuidado de la casa comun",
        "cuidado da casa comum",
    ],
    "Amoris Laetitia": [
        "Amoris Laetitia",
        "Joy of Love",
        "alegría del amor",
        "alegria del amor",
        "alegria do amor",
    ],
    "Gaudete et Exsultate": [
        "Gaudete et Exsultate",
        "Rejoice and Be Glad",
        "alegraos y regocijaos",
        "alegraos y exultad",
    ],
    "Christus Vivit": [
        "Christus Vivit",
        "Christ is Alive",
        "Cristo vive",
    ],
    "Querida Amazonia": [
        "Querida Amazonia",
        "Beloved Amazon",
        "Querida Amazonía",
    ],
    "Fratelli Tutti": [
        "Fratelli Tutti",
        "Fratelli tutti",
        "todos hermanos",
        "todos somos hermanos",
        "todos irmãos",
        "todos irmaos",
        "brothers and sisters all",
    ],
    "Laudate Deum": [
        "Laudate Deum",
        "Praise God",
        "alabad a Dios",
        "louvai a Deus",
    ],
    "Dilexit Nos": [
        "Dilexit Nos",
        "He Loved Us",
        "nos amó",
        "nos amo",
        "ele nos amou",
    ],
    "Magnifica Humanitas": [
        "Magnifica Humanitas",
        "Magnificent Humanity",
        "Magnífica humanidad",
        "Magnifica humanidad",
        "Magnífica humanidade",
        "Magnifica humanidade",
        "Safeguarding the Human Person",
        "custodia de la persona humana",
        "salvaguarda da pessoa humana",
    ],
}


def _build_encyclical_spelling_variants() -> Dict[str, List[str]]:
    """Ensure every CST document title has at least itself as a variant."""
    out: Dict[str, List[str]] = {}
    for title in cst_document_titles():
        extras = list(_ENCYCLICAL_EXTRA.get(title, [title]))
        if title not in extras:
            extras = [title, *extras]
        out[title] = extras
    # Also keep any extras whose key is not in CST list (shouldn't happen)
    for title, extras in _ENCYCLICAL_EXTRA.items():
        out.setdefault(title, extras)
    return out


ENCYCLICAL_SPELLING_VARIANTS = _build_encyclical_spelling_variants()


def accent_pair_variants(term: str) -> List[str]:
    """Return term plus accent-stripped form when they differ."""
    t = (term or "").strip()
    if not t:
        return []
    folded = fold_accents(t)
    if folded == t:
        return [t]
    return [t, folded]


def encyclical_variants_for(term: str) -> List[str]:
    """Expand one keyword if it matches a known encyclical base title."""
    t = (term or "").strip()
    if not t:
        return []
    key = fold_for_match(t)
    for canon, variants in ENCYCLICAL_SPELLING_VARIANTS.items():
        if fold_for_match(canon) == key:
            out: List[str] = []
            for v in variants:
                out.extend(accent_pair_variants(v))
            return out
    # Generic: Laudato-like trailing Si / Sí + optional apostrophe
    if re.search(r"\bsi\b", t, flags=re.I) and "laudato" in key:
        out = list(accent_pair_variants(t))
        for apo in _APOSTROPHES:
            out.append(re.sub(r"(?i)\bsi\b", f"Si{apo}", t, count=1))
            out.append(re.sub(r"(?i)\bsi\b", f"Sí{apo}", t, count=1))
        out.append(re.sub(r"(?i)\bsi\b", "Sí", t, count=1))
        return out
    return accent_pair_variants(t)


def expand_collection_keywords(keywords: Iterable[str]) -> List[str]:
    """Expand keywords with accent + encyclical spelling variants (stable unique)."""
    out: List[str] = []
    seen: Set[str] = set()
    for raw in keywords:
        if not isinstance(raw, str):
            continue
        term = raw.strip()
        if not term:
            continue
        for variant in encyclical_variants_for(term):
            key = fold_for_match(variant)
            if not key or key in seen:
                continue
            if len(key) < 3:
                continue
            seen.add(key)
            out.append(variant.strip())
    return out


def build_folded_keyword_regex(keywords: Sequence[str]) -> re.Pattern:
    """Case- and accent-insensitive OR of folded keyword strings."""
    folded = []
    seen: Set[str] = set()
    for k in keywords:
        if not k or not isinstance(k, str):
            continue
        fk = fold_for_match(k.strip())
        if not fk or fk in seen:
            continue
        if len(fk) < 3:
            continue
        seen.add(fk)
        folded.append(re.escape(fk))
    if not folded:
        return re.compile(r"a^")
    return re.compile(r"(?:" + "|".join(folded) + r")", flags=re.IGNORECASE)
