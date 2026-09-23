"""Papal name keywords for collection (modern era: Leo XIII → present).

Focused on names that appear in Catholic media / CST discourse. Earlier historical
popes are omitted as single-name queries (Peter, Paul, Gregory, …) are too noisy
for GDELT/YouTube search.
"""

from __future__ import annotations

from typing import List, Tuple

# (english_forms, spanish_forms) — first EN form is the canonical display name
PAPAL_NAME_GROUPS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (
        ("Pope Leo XIII", "Leo XIII"),
        ("Papa León XIII", "León XIII", "Leon XIII"),
    ),
    (
        ("Pope Pius X", "Pius X", "Saint Pius X"),
        ("Papa Pío X", "Pío X", "San Pío X", "Pio X"),
    ),
    (
        ("Pope Benedict XV", "Benedict XV"),
        ("Papa Benedicto XV", "Benedicto XV"),
    ),
    (
        ("Pope Pius XI", "Pius XI"),
        ("Papa Pío XI", "Pío XI", "Pio XI"),
    ),
    (
        ("Pope Pius XII", "Pius XII"),
        ("Papa Pío XII", "Pío XII", "Pio XII"),
    ),
    (
        ("Pope John XXIII", "John XXIII", "Saint John XXIII"),
        ("Papa Juan XXIII", "Juan XXIII", "San Juan XXIII"),
    ),
    (
        ("Pope Paul VI", "Paul VI", "Saint Paul VI"),
        ("Papa Pablo VI", "Pablo VI", "San Pablo VI"),
    ),
    (
        ("Pope John Paul I", "John Paul I"),
        ("Papa Juan Pablo I", "Juan Pablo I"),
    ),
    (
        ("Pope John Paul II", "John Paul II", "Saint John Paul II", "JPII", "John Paul 2"),
        ("Papa Juan Pablo II", "Juan Pablo II", "San Juan Pablo II", "Juan Pablo 2"),
    ),
    (
        ("Pope Benedict XVI", "Benedict XVI", "Joseph Ratzinger"),
        ("Papa Benedicto XVI", "Benedicto XVI", "Joseph Ratzinger"),
    ),
    (
        ("Pope Francis", "Jorge Bergoglio", "Jorge Mario Bergoglio"),
        ("Papa Francisco", "Jorge Bergoglio", "Jorge Mario Bergoglio"),
    ),
    (
        ("Pope Leo XIV", "Pope Leo", "Leo XIV"),
        ("Papa León XIV", "Papa León", "León XIV", "Leon XIV", "Papa Leon"),
    ),
)


def papal_keywords_en() -> List[str]:
    out: List[str] = []
    for en_forms, _es in PAPAL_NAME_GROUPS:
        out.extend(en_forms)
    # Umbrella phrases common in coverage
    out.extend(
        [
            "the Holy Father",
            "Holy Father",
            "Supreme Pontiff",
            "Bishop of Rome",
        ]
    )
    return out


def papal_keywords_es() -> List[str]:
    out: List[str] = []
    for _en, es_forms in PAPAL_NAME_GROUPS:
        out.extend(es_forms)
    out.extend(
        [
            "Santo Padre",
            "el Santo Padre",
            "Sumo Pontífice",
            "Sumo Pontifice",
            "Obispo de Roma",
        ]
    )
    return out


def papal_keywords_pt() -> List[str]:
    """Portuguese papal name queries (Brazil / Lusophone Americas media)."""
    return [
        "Papa Leão XIII",
        "Leão XIII",
        "Papa Pio X",
        "São Pio X",
        "Papa Bento XV",
        "Bento XV",
        "Papa Pio XI",
        "Papa Pio XII",
        "Papa João XXIII",
        "João XXIII",
        "São João XXIII",
        "Papa Paulo VI",
        "Paulo VI",
        "São Paulo VI",
        "Papa João Paulo I",
        "João Paulo I",
        "Papa João Paulo II",
        "João Paulo II",
        "São João Paulo II",
        "Papa Bento XVI",
        "Bento XVI",
        "Papa Francisco",
        "Papa Leão XIV",
        "Papa Leão",
        "Leão XIV",
        "Santo Padre",
        "Sumo Pontífice",
        "Sumo Pontifice",
        "Bispo de Roma",
    ]
