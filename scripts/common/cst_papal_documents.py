"""Catholic Social Teaching papal encyclicals and equivalent magisterial writings.

Titles are Latin (or customary) forms used as collection keywords. Spelling /
apostrophe / vernacular variants live in ``text_normalize.ENCYCLICAL_SPELLING_VARIANTS``.
"""

from __future__ import annotations

from typing import List, Tuple

# (canonical_title, kind, pontiff_short, year)
# kind: encyclical | apostolic_exhortation | apostolic_letter | motu_proprio
CST_PAPAL_DOCUMENTS: Tuple[Tuple[str, str, str, int], ...] = (
    # Leo XIII
    ("Rerum Novarum", "encyclical", "Leo XIII", 1891),
    # Pius XI
    ("Quadragesimo Anno", "encyclical", "Pius XI", 1931),
    ("Divini Redemptoris", "encyclical", "Pius XI", 1937),
    # John XXIII
    ("Mater et Magistra", "encyclical", "John XXIII", 1961),
    ("Pacem in Terris", "encyclical", "John XXIII", 1963),
    # Paul VI
    ("Populorum Progressio", "encyclical", "Paul VI", 1967),
    ("Octogesima Adveniens", "apostolic_letter", "Paul VI", 1971),
    ("Evangelii Nuntiandi", "apostolic_exhortation", "Paul VI", 1975),
    # John Paul II
    ("Laborem Exercens", "encyclical", "John Paul II", 1981),
    ("Familiaris Consortio", "apostolic_exhortation", "John Paul II", 1981),
    ("Sollicitudo Rei Socialis", "encyclical", "John Paul II", 1987),
    ("Christifideles Laici", "apostolic_exhortation", "John Paul II", 1988),
    ("Redemptoris Missio", "encyclical", "John Paul II", 1990),
    ("Centesimus Annus", "encyclical", "John Paul II", 1991),
    ("Evangelium Vitae", "encyclical", "John Paul II", 1995),
    ("Fides et Ratio", "encyclical", "John Paul II", 1998),
    # Benedict XVI / Francis
    ("Deus Caritas Est", "encyclical", "Benedict XVI", 2005),
    ("Spe Salvi", "encyclical", "Benedict XVI", 2007),
    ("Caritas in Veritate", "encyclical", "Benedict XVI", 2009),
    ("Lumen Fidei", "encyclical", "Francis", 2013),
    ("Evangelii Gaudium", "apostolic_exhortation", "Francis", 2013),
    ("Laudato Si", "encyclical", "Francis", 2015),
    ("Amoris Laetitia", "apostolic_exhortation", "Francis", 2016),
    ("Gaudete et Exsultate", "apostolic_exhortation", "Francis", 2018),
    ("Christus Vivit", "apostolic_exhortation", "Francis", 2019),
    ("Querida Amazonia", "apostolic_exhortation", "Francis", 2020),
    ("Fratelli Tutti", "encyclical", "Francis", 2020),
    ("Laudate Deum", "apostolic_exhortation", "Francis", 2023),
    ("Dilexit Nos", "encyclical", "Francis", 2024),
    # Leo XIV — first encyclical; signed 15 May 2026, released 25 May 2026 (Q2).
    ("Magnifica Humanitas", "encyclical", "Leo XIV", 2026),
)


def cst_document_titles() -> List[str]:
    return [title for title, *_ in CST_PAPAL_DOCUMENTS]


def cst_keywords_en() -> List[str]:
    """Collection keywords (EN side): Latin titles + umbrella CST phrases."""
    return [
        *cst_document_titles(),
        "Catholic social teaching",
        "Catholic social doctrine",
        "social encyclical",
        "papal encyclical",
    ]


def cst_keywords_es() -> List[str]:
    """Collection keywords (ES side): same Latin titles + Spanish CST phrases."""
    return [
        *cst_document_titles(),
        "doctrina social de la Iglesia",
        "doctrina social católica",
        "doctrina social",
        "encíclica social",
        "enciclica social",
        "encíclica papal",
        "enciclica papal",
    ]


def cst_keywords_pt() -> List[str]:
    """Collection keywords (PT side): Latin titles + Portuguese CST phrases."""
    return [
        *cst_document_titles(),
        "doutrina social da Igreja",
        "doutrina social católica",
        "doutrina social",
        "encíclica social",
        "enciclica social",
        "encíclica papal",
        "enciclica papal",
    ]
