import os
import sys
import re
from typing import List, Optional, Sequence

# Limit BLAS/OpenMP threads before importing spaCy so multiprocess NER
# does not oversubscribe the CPU (the old one-doc nlp() path was also hit by this).
for _thread_env in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_thread_env, "1")

import spacy

ENTITY_LABELS = frozenset({"PERSON", "GPE", "LOC", "ORG", "DATE", "TIME", "FAC"})
ENTITY_REPLACEMENTS = {
    "PERSON": "[PERSON]",
    "GPE": "[LOCATION]",
    "LOC": "[LOCATION]",
    "FAC": "[LOCATION]",
    "ORG": "[ORGANIZATION]",
    "DATE": "[DATE]",
    "TIME": "[TIME]",
}

_SPACY_EXCLUDE = (
    "parser",
    "tagger",
    "lemmatizer",
    "attribute_ruler",
    "senter",
    "morphologizer",
)

_USER_RE = re.compile(r"@[A-Za-z0-9_]+")
_ADDRESS_STREET_RE = re.compile(
    r"\b\d{1,5}\s+(?:[NESW]\.?\s+)?[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+)*\s+"
    r"(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Place|Pl|Court|Ct|Circle|Way)\b",
    re.IGNORECASE,
)
_ADDRESS_TAG_RE = re.compile(
    r"\b\d{1,5}\s+(?:[NESW]\.?\s+)?[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+)*\s+\[STREET\]",
)

_LOCATION_PATTERNS = [
    (re.compile(r"\b(?:St\.|Saint)\s+[A-Za-z]+\s+(?:County|Parish|City|Town)\b", re.I), "[LOCATION]"),
    (re.compile(r"\b(?:Community|Resource)\s+Center\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:Public|Private)\s+(?:School|University|College)\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:Medical|Health)\s+Center\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:Police|Fire)\s+Department\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:City|County|State)\s+Hall\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:Public|Private)\s+(?:Library|Park|Garden)\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:Shopping|Retail)\s+Mall\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:Bus|Train|Subway)\s+Station\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:Airport|Harbor|Port)\b", re.I), "[INSTITUTION]"),
    (re.compile(r"\b(?:Street|Avenue|Road|Boulevard|Drive|Lane|Place|Court|Circle|Way)\b", re.I), "[STREET]"),
    (
        re.compile(
            r"\b(?:North|South|East|West|N|S|E|W)\s+"
            r"(?:Street|Avenue|Road|Boulevard|Drive|Lane|Place|Court|Circle|Way)\b",
            re.I,
        ),
        "[STREET]",
    ),
    (
        re.compile(
            r"\b(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+"
            r"(?:Street|Avenue|Road|Boulevard|Drive|Lane|Place|Court|Circle|Way)\b",
            re.I,
        ),
        "[STREET]",
    ),
    (
        re.compile(
            r"\b(?:Main|Broad|Market|Park|Church|School|College|University|Hospital|Library)\s+"
            r"(?:Street|Avenue|Road|Boulevard|Drive|Lane|Place|Court|Circle|Way)\b",
            re.I,
        ),
        "[STREET]",
    ),
]

_PII_PATTERNS = [
    (re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"), "[PHONE]"),
    (re.compile(r"\+\d{1,2}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"), "[PHONE]"),
    (re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?"), "[URL]"),
    (re.compile(r"www\.(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?"), "[URL]"),
    (
        re.compile(
            r"(?:[-\w.]|(?:%[\da-fA-F]{2}))+\."
            r"(?:com|org|net|edu|gov|mil|biz|info|mobi|name|aero|asia|jobs|museum)(?:/[^\s]*)?"
        ),
        "[URL]",
    ),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "[CARD]"),
    (re.compile(r"\b\d{5}(?:-\d{4})?\b"), "[ZIP]"),
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"), "[DATE]"),
    (re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b"), "[DATE]"),
    (re.compile(r"\[URL\]/[^\s]+"), "[URL]"),
    (re.compile(r"\[URL\]\[URL\]"), "[URL]"),
    (re.compile(r"\[LOCATION\]/[^\s]+"), "[LOCATION]"),
    (re.compile(r"\[LOCATION\]\[LOCATION\]"), "[LOCATION]"),
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),
]

DEFAULT_PIPE_BATCH_SIZE = 64


def _spacy_model_name(language: Optional[str]) -> str:
    lang = (language or "english").lower().strip()
    if lang == "spanish":
        return "es_core_news_sm"
    if lang == "portuguese":
        return "pt_core_news_sm"
    return "en_core_web_sm"


def load_spacy_model(use_gpu: bool = False, language: Optional[str] = "english"):
    if use_gpu:
        try:
            spacy.prefer_gpu()
        except Exception:
            pass
    model_name = _spacy_model_name(language)
    try:
        nlp = spacy.load(model_name, exclude=list(_SPACY_EXCLUDE))
    except OSError:
        print("Downloading spaCy model...")
        import subprocess

        subprocess.run([sys.executable, "-m", "spacy", "download", model_name], check=True)
        nlp = spacy.load(model_name, exclude=list(_SPACY_EXCLUDE))
    nlp.max_length = 2_000_000
    # Keep tok2vec + NER only if those pipes exist (parser/tagger already excluded).
    keep = [name for name in nlp.pipe_names if name in ("tok2vec", "ner")]
    if keep:
        nlp.select_pipes(enable=keep)
    return nlp


def get_deidentifier(language: Optional[str] = "english"):
    """Kept for compatibility. Hot path no longer uses pydeidentify (duplicate spaCy NER)."""
    return None


def _apply_entity_replacements(text: str, doc) -> str:
    """Replace NER spans by character offset (right-to-left) to avoid global str.replace."""
    spans = []
    for ent in doc.ents:
        if ent.label_ not in ENTITY_LABELS:
            continue
        replacement = ENTITY_REPLACEMENTS.get(ent.label_)
        if replacement:
            spans.append((ent.start_char, ent.end_char, replacement))
    if not spans:
        return text
    spans.sort(key=lambda item: item[0], reverse=True)
    out = text
    for start, end, replacement in spans:
        out = out[:start] + replacement + out[end:]
    return out


def apply_pii_regexes(text: str) -> str:
    text = _USER_RE.sub("[USER]", text)
    text = _ADDRESS_STREET_RE.sub("[ADDRESS]", text)
    text = _ADDRESS_TAG_RE.sub("[ADDRESS]", text)
    for pattern, replacement in _LOCATION_PATTERNS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def deidentify_from_doc(text: str, doc) -> str:
    """NER replacements first (offsets valid), then regex PII."""
    return apply_pii_regexes(_apply_entity_replacements(text, doc))


def deidentify_texts(
    texts: Sequence[str],
    nlp,
    *,
    batch_size: int = DEFAULT_PIPE_BATCH_SIZE,
) -> List[str]:
    """Batch NER via nlp.pipe (much faster than nlp(text) per string)."""
    if not texts:
        return []
    out: List[str] = [""] * len(texts)
    nonempty = []
    for i, raw in enumerate(texts):
        if not isinstance(raw, str) or not raw.strip():
            out[i] = "" if not isinstance(raw, str) else raw
            continue
        text = raw if len(raw) <= nlp.max_length else raw[: nlp.max_length]
        nonempty.append((i, text))
    if not nonempty:
        return out
    docs = nlp.pipe((t for _, t in nonempty), batch_size=max(int(batch_size), 1))
    for (i, text), doc in zip(nonempty, docs):
        out[i] = deidentify_from_doc(text, doc)
    return out


def deidentify_text(text, nlp=None, deidentifier=None, language: Optional[str] = "english"):
    if not isinstance(text, str):
        return ""
    if nlp is None:
        nlp = load_spacy_model(language=language)
    return deidentify_texts([text], nlp)[0]
