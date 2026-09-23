"""Americas country codes for collectors.

GDELT ActionGeo_CountryCode is **FIPS 10-4**, not ISO 3166-1 alpha-2.
Chile is ISO ``CL`` but GDELT FIPS ``CI`` (FIPS ``CL`` is Sri Lanka).

User-facing ``--country`` values are ISO-2, comma lists, or aliases:

- ``AMERICAS`` — whole Western Hemisphere (incl. US)
- ``AMERICAS_NOT_US`` — same minus the United States (default for new hemisphere jobs)
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Optional

# ISO-2 → GDELT FIPS 10-4 for independent states + PR in the Americas.
AMERICAS_ISO_TO_FIPS: Dict[str, str] = {
    # North America
    "CA": "CA",
    "MX": "MX",
    "US": "US",
    # Central America
    "BZ": "BH",
    "CR": "CS",
    "GT": "GT",
    "HN": "HO",
    "NI": "NU",
    "PA": "PM",
    "SV": "ES",
    # South America (Chile = CL → FIPS CI; RISE host)
    "AR": "AR",
    "BO": "BL",
    "BR": "BR",
    "CL": "CI",
    "CO": "CO",
    "EC": "EC",
    "GF": "FG",
    "GY": "GY",
    "PE": "PE",
    "PY": "PA",
    "SR": "NS",
    "UY": "UY",
    "VE": "VE",
    # Caribbean
    "AG": "AC",
    "BB": "BB",
    "BS": "BF",
    "CU": "CU",
    "DM": "DO",
    "DO": "DR",
    "GD": "GJ",
    "HT": "HA",
    "JM": "JM",
    "KN": "SC",
    "LC": "ST",
    "PR": "RQ",
    "TT": "TD",
    "VC": "VC",
}

YOUTUBE_REGION_PRIORITY: tuple[str, ...] = (
    "CL",
    "MX",
    "AR",
    "CO",
    "PE",
    "BR",
    "CA",
    "GT",
    "SV",
    "HN",
    "NI",
    "CR",
    "PA",
    "CU",
    "DO",
    "HT",
    "VE",
    "EC",
    "BO",
    "UY",
    "PY",
    "JM",
    "TT",
    "BZ",
    "GY",
    "SR",
    "PR",
    "BB",
    "BS",
    "AG",
    "LC",
    "GD",
    "KN",
    "VC",
    "DM",
    "GF",
)

# English/Spanish place names for Internet Archive audio queries (not GDELT FIPS).
AMERICAS_PLACE_QUERY_TERMS: tuple[str, ...] = (
    "mexico",
    "méxico",
    "chile",
    "argentina",
    "colombia",
    "peru",
    "perú",
    "brazil",
    "brasil",
    "bolivia",
    "ecuador",
    "paraguay",
    "uruguay",
    "venezuela",
    "guatemala",
    "honduras",
    "el salvador",
    "nicaragua",
    "costa rica",
    "panama",
    "panamá",
    "cuba",
    "haiti",
    "haití",
    "jamaica",
    "caribbean",
    "caribe",
    "dominican",
    "república dominicana",
    "puerto rico",
    "canada",
    "canadá",
    "andes",
    "latin america",
    "américa latina",
    "latinoamerica",
    "sudamerica",
    "south america",
    "central america",
    "centroamérica",
)

AMERICAS_FIPS: FrozenSet[str] = frozenset(AMERICAS_ISO_TO_FIPS.values())
AMERICAS_FIPS_NOT_US: FrozenSet[str] = frozenset(c for c in AMERICAS_FIPS if c != "US")

# Reverse map for labels (FIPS → ISO). Chile is FIPS CI → ISO CL.
FIPS_TO_ISO: Dict[str, str] = {v: k for k, v in AMERICAS_ISO_TO_FIPS.items()}

FIPS_COUNTRY_NAME: Dict[str, str] = {
    "US": "United States",
    "CA": "Canada",
    "MX": "Mexico",
    "BH": "Belize",
    "CS": "Costa Rica",
    "GT": "Guatemala",
    "HO": "Honduras",
    "NU": "Nicaragua",
    "PM": "Panama",
    "ES": "El Salvador",
    "AR": "Argentina",
    "BL": "Bolivia",
    "BR": "Brazil",
    "CI": "Chile",
    "CO": "Colombia",
    "EC": "Ecuador",
    "FG": "French Guiana",
    "GY": "Guyana",
    "PE": "Peru",
    "PA": "Paraguay",
    "NS": "Suriname",
    "UY": "Uruguay",
    "VE": "Venezuela",
    "AC": "Antigua and Barbuda",
    "BB": "Barbados",
    "BF": "Bahamas",
    "CU": "Cuba",
    "DO": "Dominica",
    "DR": "Dominican Republic",
    "GJ": "Grenada",
    "HA": "Haiti",
    "JM": "Jamaica",
    "SC": "Saint Kitts and Nevis",
    "ST": "Saint Lucia",
    "RQ": "Puerto Rico",
    "TD": "Trinidad and Tobago",
    "VC": "Saint Vincent and the Grenadines",
}

_CENTRAL_AMERICA_FIPS = frozenset({"BH", "CS", "GT", "HO", "NU", "PM", "ES"})
_CARIBBEAN_FIPS = frozenset(
    {"AC", "BB", "BF", "CU", "DO", "DR", "GJ", "HA", "JM", "SC", "ST", "RQ", "TD", "VC"}
)
_ANDES_SOUTH_CONE_FIPS = frozenset(
    {"AR", "BL", "CI", "CO", "EC", "FG", "GY", "PE", "PA", "NS", "UY", "VE"}
)


# UN WESP 2024 developed economies in the Americas (Canada, United States).
# Latin America and the Caribbean are developing economies in the same report.
# https://www.un.org/development/desa/dpad/publication/world-economic-situation-and-prospects-2024/
UN_WESP_DEVELOPED_FIPS: FrozenSet[str] = frozenset({"US", "CA"})

# World Bank Atlas method, FY2025 (July 2024–June 2025) high-income Americas.
# Chile, Uruguay, Panama, Guyana, and several Caribbean states are high-income
# but still UN-developing. Puerto Rico is a U.S. territory (high-income).
WB_HIGH_INCOME_FIPS: FrozenSet[str] = frozenset(
    {
        "US",
        "CA",
        "CI",  # Chile
        "UY",
        "PM",  # Panama
        "GY",  # Guyana (oil; reclassified high-income)
        "BF",  # Bahamas
        "BB",
        "TD",  # Trinidad and Tobago
        "AC",  # Antigua and Barbuda
        "SC",  # Saint Kitts and Nevis
        "RQ",  # Puerto Rico
        "VC",
        "ST",  # Saint Lucia
        "GJ",  # Grenada
    }
)


def fips_country_name(fips: str) -> str:
    code = (fips or "").upper()[:2]
    return FIPS_COUNTRY_NAME.get(code, code or "(unknown)")


# Approximate centroids for ActionGeo lat/lon → FIPS when col_51 is missing (fetched paragraphs).
_LATLON_CENTROIDS: dict[str, tuple[float, float]] = {
    "US": (39.8, -98.5),
    "CA": (56.1, -106.3),
    "MX": (23.6, -102.5),
    "GT": (15.8, -90.2),
    "BH": (17.2, -88.5),
    "HO": (15.2, -86.2),
    "ES": (13.8, -88.9),
    "NU": (12.9, -85.2),
    "CS": (9.9, -84.1),
    "PM": (8.5, -80.0),
    "CU": (21.5, -77.8),
    "HA": (18.97, -72.3),
    "DR": (18.7, -70.2),
    "JM": (18.1, -77.3),
    "RQ": (18.2, -66.5),
    "AR": (-38.4, -63.6),
    "CI": (-35.7, -71.5),
    "BR": (-14.2, -51.9),
    "CO": (4.6, -74.3),
    "PE": (-9.2, -75.0),
    "VE": (6.4, -66.6),
    "EC": (-1.8, -78.2),
    "BL": (-16.3, -63.6),
    "PA": (-23.4, -58.4),
    "UY": (-32.5, -55.8),
}


def record_action_latlon(rec: dict) -> tuple[float, float] | None:
    try:
        lat = float(rec.get("action_lat"))
        lon = float(rec.get("action_lon"))
        if lat == 0 and lon == 0:
            raise ValueError
        return lat, lon
    except (TypeError, ValueError):
        pass
    api = rec.get("api_raw")
    if isinstance(api, dict):
        for la, lo in (("col_53", "col_54"), ("col_56", "col_57")):
            try:
                lat = float(api.get(la))
                lon = float(api.get(lo))
                if lat == 0 and lon == 0:
                    continue
                return lat, lon
            except (TypeError, ValueError):
                continue
    return None


def fips_from_latlon(lat: float, lon: float, *, max_deg2: float = 25.0) -> str:
    best, best_d = "", 9e9
    for fips, (clat, clon) in _LATLON_CENTROIDS.items():
        d = (lat - clat) ** 2 + (lon - clon) ** 2
        if d < best_d:
            best, best_d = fips, d
    return best if best_d <= max_deg2 else ""


def record_action_fips(rec: dict, source_hint: str = "") -> str:
    """GDELT ActionGeo FIPS from a news record (empty if unknown)."""
    raw = rec.get("action_country") or ""
    if not raw:
        api = rec.get("api_raw")
        if isinstance(api, dict):
            raw = (
                api.get("action_country")
                or api.get("ActionGeo_CountryCode")
                or api.get("col_51")
                or ""
            )
    code = str(raw or "").upper()[:2]
    if not code:
        xy = record_action_latlon(rec)
        if xy:
            lat, lon = xy
            if -60 <= lat <= 75 and -170 <= lon <= -20:
                code = fips_from_latlon(lat, lon)
    # U.S. fetched paragraphs often keep lat/lon but drop ActionGeo FIPS.
    if not code and source_hint in (
        "gdelt_news_us",
        "gdelt_news_2015_2022",
        "gdelt_news_main",
        "gdelt_news_2025_26",
    ):
        return "US"
    return code


def un_wesp_development_group(fips: str) -> str:
    """UN WESP developed vs developing. Unmapped FIPS → unclassified."""
    code = (fips or "").upper()[:2]
    if not code or code not in FIPS_COUNTRY_NAME:
        return "unclassified"
    if code in UN_WESP_DEVELOPED_FIPS:
        return "developed"
    return "developing"


def wb_income_group(fips: str) -> str:
    """World Bank FY2025 high-income vs not, for Americas FIPS we collect."""
    code = (fips or "").upper()[:2]
    if not code or code not in FIPS_COUNTRY_NAME:
        return "unclassified"
    if code in WB_HIGH_INCOME_FIPS:
        return "high_income"
    return "not_high_income"


def collection_region_from_fips(fips: str) -> str | None:
    """Map GDELT ActionGeo FIPS to the same region labels used in theme scans."""
    code = (fips or "").upper()[:2]
    if not code:
        return None
    if code == "US":
        return "united_states"
    if code == "CA":
        return "canada"
    if code == "MX":
        return "mexico"
    if code == "BR":
        return "brazil"
    if code in _CENTRAL_AMERICA_FIPS:
        return "central_america"
    if code in _CARIBBEAN_FIPS:
        return "caribbean"
    if code in _ANDES_SOUTH_CONE_FIPS:
        return "andes_south_cone"
    return None

_ALIASES = {
    "AMERICAS": AMERICAS_FIPS,
    "ALL": AMERICAS_FIPS,
    "WESTERN_HEMISPHERE": AMERICAS_FIPS,
    "AMERICAS_NOT_US": AMERICAS_FIPS_NOT_US,
    "LATAM": AMERICAS_FIPS_NOT_US,
    "NOT_US": AMERICAS_FIPS_NOT_US,
}


def resolve_gdelt_fips_codes(spec: str) -> FrozenSet[str]:
    """Resolve ``--country`` (ISO / alias / comma list) to GDELT FIPS codes."""
    raw = (spec or "").strip()
    if not raw:
        raise ValueError("Empty country spec")
    key = raw.upper().replace(" ", "")
    if key in _ALIASES:
        return _ALIASES[key]

    fips: List[str] = []
    for token in key.split(","):
        tok = token.strip()
        if not tok:
            continue
        if tok in _ALIASES:
            fips.extend(_ALIASES[tok])
            continue
        if tok in AMERICAS_ISO_TO_FIPS:
            fips.append(AMERICAS_ISO_TO_FIPS[tok])
            continue
        if tok in AMERICAS_FIPS:
            fips.append(tok)
            continue
        hint = ""
        if tok == "CL":
            hint = " (Chile is ISO CL → GDELT FIPS CI)"
        raise ValueError(
            f"Unknown Americas country code {tok!r}{hint}. "
            "Use ISO-2 (CL, MX, BR, AR, …), AMERICAS, or AMERICAS_NOT_US."
        )
    if not fips:
        raise ValueError(f"No country codes in spec {spec!r}")
    return frozenset(fips)


def describe_country_spec(spec: str, fips: Optional[Iterable[str]] = None) -> str:
    codes = sorted(fips if fips is not None else resolve_gdelt_fips_codes(spec))
    return f"ActionGeo filter {spec!r} → {len(codes)} FIPS code(s): {', '.join(codes)}"


def youtube_region_codes(spec: str) -> List[str]:
    """ISO-2 regionCodes for YouTube (single-region API; loop these). Chile first."""
    fips = resolve_gdelt_fips_codes(spec)
    iso_by_fips = {v: k for k, v in AMERICAS_ISO_TO_FIPS.items()}
    codes = [iso_by_fips[c] for c in fips if c in iso_by_fips]
    wanted = set(codes)
    ordered = [c for c in YOUTUBE_REGION_PRIORITY if c in wanted]
    ordered.extend(sorted(c for c in wanted if c not in ordered))
    return ordered


def americas_place_solr_clause() -> str:
    """OR-clause of Americas place names for Internet Archive / Solr queries."""
    terms: List[str] = []
    for raw in AMERICAS_PLACE_QUERY_TERMS:
        text = raw.strip()
        if not text:
            continue
        terms.append(f'"{text}"' if " " in text else text)
    return "(" + " OR ".join(terms) + ")"
