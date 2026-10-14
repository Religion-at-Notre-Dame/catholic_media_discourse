"""Human labels for Jev taxonomy ids (Story, figures, Triage)."""

from __future__ import annotations

PRETTY = {
    "cst_papal": "CST / papal",
    "doctrine_sacrament": "Doctrine / sacrament",
    "institutional_news": "Institutional news",
    "moral_ethics": "Moral / ethics",
    "devotion_piety": "Devotion / piety",
    "migration_politics": "Migration / politics",
    "evangelization_mission": "Evangelization / mission",
    "misunderstanding": "Misunderstanding",
    "other_unclear": "Other / unclear",
    "liberation_theology": "Liberation theology",
    "laudato_si": "Laudato Si'",
    "guadalupe": "Guadalupe",
    "immigration": "Immigration",
    "mission": "Mission",
    "gospel": "Gospel",
    "evangelio": "Evangelio",
    "eucharist": "Eucharist",
    "factual_claim": "Factual claim",
    "doctrinal_claim": "Doctrinal claim",
    "question": "Question",
    "news_report": "News report",
    "opinion": "Opinion",
    "advocacy": "Advocacy",
    "homily_devotion": "Homily / devotion",
    "interview": "Interview",
}


def pretty_label(s: str | None) -> str:
    if s is None:
        return "n/a"
    key = str(s)
    if key in PRETTY:
        return PRETTY[key]
    return key.replace("_", " ").strip().title()


def pretty_hook_text(text: str | None) -> str:
    """Human labels for hooks; drop Fisher/Holm jargon for classroom pages."""
    import re

    if not text:
        return "n/a"
    out = str(text)
    # Longer keys first so cst_papal beats papal-only mistakes
    for key in sorted(PRETTY.keys(), key=len, reverse=True):
        out = out.replace(key, PRETTY[key])
    # Strip parenthetical stats (lift, OR, stars, Holm) for everyday readers
    out = re.sub(r"\s*\([^)]*(?:lift|OR|Holm|\*{1,3})[^)]*\)", "", out, flags=re.I)
    out = re.sub(r"\s*·\s*[^·]*(?:lift|OR|Holm|\*{1,3})[^·]*", "", out, flags=re.I)
    out = re.sub(r"\s*[×x]\s*", " with ", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out or "n/a"
