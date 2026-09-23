"""Bilingual surface cues for speech-act / discourse mix (not gold labels).

English regex used to miss Spanish radio (the cheap eval sample was 100%
``other_or_mixed`` in Spanish). These patterns add interrogatives and ES/PT
reporting, opinion, advocacy, and devotion cues.

``question`` is orthogonal to genre: a homily can still ask a question.
"""

from __future__ import annotations

import re
from typing import Dict

QUESTION_MARK = re.compile(r"[¿?]")
INTERROG = re.compile(
    r"(?:^|[.\"«»“”]\s+)"
    r"(?:who|what|when|where|why|how|which|is|are|do|does|did|"
    r"qué|quien|quién|cuál|cuáles|cómo|dónde|cuándo|cuánto|"
    r"por\s+qu[eé]|por\s+que|"
    r"quem|quando|onde|por\s+que)\b",
    re.I,
)
QUESTION_VERB = re.compile(
    r"\b(?:asked|asks|asking|pregunta(?:n|mos|ba)?|preguntó|preguntar|"
    r"question(?:s|ed|ing)?)\b",
    re.I,
)

REPORTING = re.compile(
    r"\b(?:said|says|according to|reported|announced|told reporters|"
    r"statement|press release|confirmed|denied|sources say|"
    r"dijo|seg[uú]n|inform[oó]|anunci[oó]|de acuerdo con|"
    r"disse|segundo|informou|anunciou)\b",
    re.I,
)
OPINION = re.compile(
    r"\b(?:I (?:think|believe|feel|argue)|in my (?:view|opinion)|we must|"
    r"should|ought|it is clear that|clearly|obviously|outrageous|"
    r"creo que|opino que|debemos|es evidente|lamentable|"
    r"acho que|devemos|é evidente)\b",
    re.I,
)
ADVOCACY = re.compile(
    r"\b(?:call(?:s|ed|ing)? (?:on|for|to)|urge[sd]?|demand[sd]?|"
    r"petition|protest|campaign|lobby|solidarity|stand with|"
    r"exhorta|exige|llamado a|en solidaridad|"
    r"exigimos|convoca)\b",
    re.I,
)
DEVOTIONAL = re.compile(
    r"\b(?:pray(?:er|ing|s)?|homily|liturgy|mass|adoration|rosary|"
    r"blessed sacrament|holy spirit|amen|allelui?a|"
    r"oración|homil[ií]a|liturgia|misa|rosario|esp[ií]ritu santo|"
    r"oração|homilia|liturgia)\b",
    re.I,
)
FACTISH = re.compile(
    r"\b(?:\d{1,2}%|\$[\d,]+|\d{4}|\d+ (?:people|immigrants|bishops|parishes|dioceses)|"
    r"percent|million|thousand|on \w+ \d{1,2}|according to (?:the )?(?:census|poll|survey|report)|"
    r"por\s+ciento|millones?|informe|encuesta|censo)\b",
    re.I,
)

# Zero-shot NLI labels (English names; multilingual models still score ES/PT text).
ZERO_SHOT_LABELS = (
    "news reporting",
    "homily or religious teaching",
    "opinion or editorial",
    "advocacy or protest",
    "interview or questions",
)

ZERO_SHOT_SHORT = {
    "news reporting": "news_report",
    "homily or religious teaching": "homily",
    "opinion or editorial": "opinion",
    "advocacy or protest": "advocacy",
    "interview or questions": "interview",
}

DEFAULT_MODEL = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"


def confirm_language(lang: str, text: str, source: str) -> str:
    """Keyword routing (guadalupe, papa) is not language. Check function words."""
    if source in ("aapb_es",) or str(source).endswith("_es"):
        return "spanish"
    blob = f" {text[:2500].lower()} "
    es = sum(blob.count(w) for w in (" el ", " los ", " las ", " del ", " que ", " una ", " para ", " iglesia "))
    en = sum(blob.count(w) for w in (" the ", " and ", " of ", " to ", " for ", " with ", " that "))
    pt = sum(blob.count(w) for w in (" não ", " uma ", " são ", " também ", " igreja "))
    if es >= 3 and es > en and es >= pt:
        return "spanish"
    if pt >= 3 and pt > en and pt > es:
        return "portuguese"
    if lang == "spanish" and es <= en:
        return "english"
    if lang == "portuguese" and pt <= en:
        return "english"
    return lang if lang in ("english", "spanish", "portuguese") else "english"


def is_question(text: str) -> bool:
    if QUESTION_MARK.search(text):
        return True
    if QUESTION_VERB.search(text) and INTERROG.search(text):
        return True
    return bool(INTERROG.search(text[:280]))


def discourse_modes(text: str) -> Dict[str, bool]:
    return {
        "question": is_question(text),
        "reporting": bool(REPORTING.search(text)),
        "opinion": bool(OPINION.search(text)),
        "advocacy": bool(ADVOCACY.search(text)),
        "devotional": bool(DEVOTIONAL.search(text)),
        "factish_markers": bool(FACTISH.search(text)),
    }


def primary_discourse(modes: Dict[str, bool]) -> str:
    for key in ("devotional", "advocacy", "opinion", "reporting"):
        if modes.get(key):
            return key
    return "other_or_mixed"
