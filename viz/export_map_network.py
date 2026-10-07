#!/usr/bin/env python3
"""Export Places (ActionGeo lat/lon, US states) + Topics (theme co-occurrence).

Place counts use the unified GDELT news corpora (2015-01-01 → 2026-06-30):
``gdelt_us_paragraphs_20150101_20260630.jsonl`` + ``gdelt_americas_paragraphs_20150101_20260630.jsonl``.

  python3 viz/export_map_network.py
  python3 viz/export_map_network.py --skip-themes
  python3 viz/export_map_network.py --encyclicals-only
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
VIZ_DIR = Path(__file__).resolve().parent
for p in (SCRIPTS, VIZ_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from common.evangelization_themes import THEME_PATTERNS, match_theme_labels, theme_group  # noqa: E402
from common.gdelt_paths import paragraph_scan_paths  # noqa: E402
from common.geography import fips_country_name  # noqa: E402
from common.progress import section, write  # noqa: E402
from viz_fast import cache_path, default_jobs, inventory_fingerprint, load_cache, save_cache  # noqa: E402

CACHE_DIR = VIZ_DIR / ".cache"
_MAX_NEWS_ROWS = int(os.environ.get("VIZ_MAX_NEWS_ROWS", "0") or "0")

NET = ROOT / "data/network"
OUT = Path(__file__).resolve().parent / "data.js"

try:
    import orjson as _orjson

    def _loads(line: str) -> dict:
        return _orjson.loads(line)
except ImportError:  # pragma: no cover
    def _loads(line: str) -> dict:
        return json.loads(line)

CENTROIDS = {
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
    "TD": (10.7, -61.2),
    "BB": (13.2, -59.5),
    "BF": (25.0, -77.4),
    "GJ": (12.1, -61.7),
    "VC": (13.25, -61.2),
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
    "GY": (4.9, -58.9),
    "NS": (4.0, -56.0),
    "FG": (4.0, -53.0),
}

TEACHING_MAP = {
    "MX": ("guadalupe", "immigration"),
    "ES": ("oscar_romero", "liberation_theology", "preferential_option"),
    "GT": ("oscar_romero",),
    "HO": ("oscar_romero",),
    "BR": ("aparecida_celam", "querida_amazonia", "inculturation"),
    "CO": ("aparecida_celam", "mision"),
    "AR": ("mision", "evangelio"),
    "CI": ("mision", "evangelio"),
    "PE": ("mision", "evangelio"),
    "BL": ("mision",),
    "PA": ("mision",),
    "US": ("laudato_si", "evangelii_gaudium", "gospel", "eucharist"),
}

PRETTY = {
    "guadalupe": "Guadalupe",
    "oscar_romero": "Óscar Romero",
    "aparecida_celam": "Aparecida / CELAM",
    "querida_amazonia": "Querida Amazonia",
    "laudato_si": "Laudato Si'",
    "evangelii_gaudium": "Evangelii Gaudium",
    "fratelli_tutti": "Fratelli Tutti",
    "preferential_option": "opción preferencial",
    "liberation_theology": "liberation theology",
    "inculturation": "inculturation",
    "catholic_social_teaching": "CST / doctrina social",
    "mision": "misión",
    "evangelio": "evangelio",
    "gospel": "gospel",
    "eucharist": "Eucharist",
    "immigration": "immigration",
    "indigenous": "indigenous",
    "marian_devotion": "Marian devotion",
    "mission": "mission",
    "new_evangelization": "new evangelization",
    "evangelization": "evangelization",
    "synod": "synod",
    "synodality": "synodality",
    "sacrament": "sacrament",
    "pastoral": "pastoral",
    "catechesis": "catechesis",
    "amoris_laetitia": "Amoris Laetitia",
    "rerum_novarum": "Rerum Novarum",
    "quadragesimo_anno": "Quadragesimo Anno",
    "familiaris_consortio": "Familiaris Consortio",
    "evangelii_nuntiandi": "Evangelii Nuntiandi",
    "base_communities": "base communities",
    "centesimus_annus": "Centesimus Annus",
    "christus_vivit": "Christus Vivit",
    "conversion_discipleship": "conversion / discipleship",
    "evangelium_vitae": "Evangelium Vitae",
    "fides_et_ratio": "Fides et Ratio",
    "lumen_fidei": "Lumen Fidei",
    "pacem_in_terris": "Pacem in Terris",
    "populorum_progressio": "Populorum Progressio",
    "popular_piety": "popular piety",
    "witness": "witness",
    "youth": "youth",
}

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "PR": "Puerto Rico",
}

MX_ADM = {
    "MX01": "Aguascalientes", "MX02": "Baja California", "MX03": "Baja California Sur",
    "MX04": "Campeche", "MX05": "Chiapas", "MX06": "Chihuahua", "MX07": "Coahuila",
    "MX08": "Colima", "MX09": "Mexico City", "MX10": "Durango", "MX11": "Guanajuato",
    "MX12": "Guerrero", "MX13": "Hidalgo", "MX14": "Jalisco", "MX15": "State of México",
    "MX16": "Michoacán", "MX17": "Morelos", "MX18": "Nayarit", "MX19": "Nuevo León",
    "MX20": "Oaxaca", "MX21": "Puebla", "MX22": "Querétaro", "MX23": "Quintana Roo",
    "MX24": "San Luis Potosí", "MX25": "Sinaloa", "MX26": "Sonora", "MX27": "Tabasco",
    "MX28": "Tamaulipas", "MX29": "Tlaxcala", "MX30": "Veracruz", "MX31": "Yucatán",
    "MX32": "Zacatecas",
}

BR_ADM = {
    "BR01": "Acre", "BR02": "Alagoas", "BR03": "Amapá", "BR04": "Amazonas",
    "BR05": "Bahia", "BR06": "Ceará", "BR07": "Distrito Federal", "BR08": "Espírito Santo",
    "BR11": "Mato Grosso do Sul", "BR13": "Maranhão", "BR15": "Pará",
    "BR16": "Minas Gerais", "BR17": "Mato Grosso", "BR18": "Pernambuco",
    "BR19": "Piauí", "BR21": "Rio de Janeiro", "BR22": "Rio Grande do Norte",
    "BR23": "Rio Grande do Sul", "BR24": "Rondônia", "BR25": "Roraima",
    "BR26": "Santa Catarina", "BR27": "São Paulo", "BR28": "Sergipe",
    "BR29": "Goiás", "BR30": "Paraíba", "BR31": "Paraná", "BR32": "Rio de Janeiro",
    "BR33": "São Paulo",
}

# Named metros so the map is cities, not anonymous cells.
METROS = [
    (40.71, -74.01, "New York", "US"),
    (42.65, -73.76, "Albany", "US"),
    (42.89, -78.88, "Buffalo", "US"),
    (43.16, -77.61, "Rochester", "US"),
    (38.91, -77.04, "Washington, D.C.", "US"),
    (34.05, -118.24, "Los Angeles", "US"),
    (41.88, -87.63, "Chicago", "US"),
    (29.76, -95.37, "Houston", "US"),
    (25.76, -80.19, "Miami", "US"),
    (32.78, -96.80, "Dallas", "US"),
    (37.77, -122.42, "San Francisco", "US"),
    (42.36, -71.06, "Boston", "US"),
    (39.95, -75.17, "Philadelphia", "US"),
    (33.45, -112.07, "Phoenix", "US"),
    (47.61, -122.33, "Seattle", "US"),
    (39.74, -104.99, "Denver", "US"),
    (30.27, -97.74, "Austin", "US"),
    (39.10, -84.51, "Cincinnati", "US"),
    (42.33, -83.05, "Detroit", "US"),
    (44.98, -93.27, "Minneapolis", "US"),
    (38.63, -90.20, "St. Louis", "US"),
    (35.15, -90.05, "Memphis", "US"),
    (29.95, -90.07, "New Orleans", "US"),
    (35.23, -80.84, "Charlotte", "US"),
    (36.16, -86.78, "Nashville", "US"),
    (33.75, -84.39, "Atlanta", "US"),
    (36.17, -115.14, "Las Vegas", "US"),
    (45.52, -122.68, "Portland", "US"),
    (32.72, -117.16, "San Diego", "US"),
    (19.43, -99.13, "Mexico City", "MX"),
    (20.67, -103.35, "Guadalajara", "MX"),
    (25.67, -100.31, "Monterrey", "MX"),
    (21.16, -86.85, "Cancún", "MX"),
    (19.05, -98.20, "Puebla", "MX"),
    (20.97, -89.62, "Mérida", "MX"),
    (16.75, -93.12, "Tuxtla Gutiérrez", "MX"),
    (13.69, -89.19, "San Salvador", "ES"),
    (14.63, -90.51, "Guatemala City", "GT"),
    (14.08, -87.21, "Tegucigalpa", "HO"),
    (12.14, -86.25, "Managua", "NU"),
    (9.93, -84.09, "San José", "CS"),
    (8.98, -79.52, "Panama City", "PM"),
    (-23.55, -46.63, "São Paulo", "BR"),
    (-22.91, -43.17, "Rio de Janeiro", "BR"),
    (-15.79, -47.88, "Brasília", "BR"),
    (-12.97, -38.50, "Salvador", "BR"),
    (-3.72, -38.54, "Fortaleza", "BR"),
    (-8.05, -34.88, "Recife", "BR"),
    (-19.92, -43.94, "Belo Horizonte", "BR"),
    (-30.03, -51.23, "Porto Alegre", "BR"),
    (-25.43, -49.27, "Curitiba", "BR"),
    (-3.12, -60.02, "Manaus", "BR"),
    (-34.60, -58.38, "Buenos Aires", "AR"),
    (-31.42, -64.18, "Córdoba", "AR"),
    (-32.95, -60.64, "Rosario", "AR"),
    (-33.45, -70.67, "Santiago", "CI"),
    (-33.05, -71.62, "Valparaíso", "CI"),
    (-36.83, -73.05, "Concepción", "CI"),
    (4.71, -74.07, "Bogotá", "CO"),
    (6.25, -75.56, "Medellín", "CO"),
    (3.45, -76.53, "Cali", "CO"),
    (-12.05, -77.04, "Lima", "PE"),
    (-16.41, -71.54, "Arequipa", "PE"),
    (-0.18, -78.47, "Quito", "EC"),
    (-2.17, -79.92, "Guayaquil", "EC"),
    (10.48, -66.90, "Caracas", "VE"),
    (-16.50, -68.15, "La Paz", "BL"),
    (-25.26, -57.58, "Asunción", "PA"),
    (-34.90, -56.16, "Montevideo", "UY"),
    (43.65, -79.38, "Toronto", "CA"),
    (45.50, -73.57, "Montreal", "CA"),
    (49.28, -123.12, "Vancouver", "CA"),
    (18.47, -69.90, "Santo Domingo", "DR"),
    (18.47, -66.12, "San Juan", "RQ"),
    (23.11, -82.37, "Havana", "CU"),
    (18.54, -72.34, "Port-au-Prince", "HA"),
    (18.00, -76.79, "Kingston", "JM"),
    (10.66, -61.52, "Port of Spain", "TD"),
]

HYP = {(c, t) for c, ts in TEACHING_MAP.items() for t in ts}

# Vernacular names count as the same teaching (Joy of the Gospel = Evangelii Gaudium).
THEME_ALIAS = {
    "evangelio": "gospel",
    "mision": "mission",
    "nueva_evangelizacion": "new_evangelization",
}

FEATURED = frozenset(
    {
        "guadalupe",
        "oscar_romero",
        "aparecida_celam",
        "querida_amazonia",
        "laudato_si",
        "evangelii_gaudium",
        "fratelli_tutti",
        "amoris_laetitia",
        "liberation_theology",
        "preferential_option",
        "immigration",
        "indigenous",
        "gospel",
        "evangelio",
        "mission",
        "mision",
        "eucharist",
        "synod",
        "catholic_social_teaching",
        "marian_devotion",
        "inculturation",
    }
)
FEATURED_PATTERNS = tuple(p for p in THEME_PATTERNS if p.label in FEATURED)

ALSO = {
    "guadalupe": "EN Our Lady of Guadalupe · ES Virgen de Guadalupe · PT Nossa Senhora de Guadalupe",
    "oscar_romero": "EN Óscar Romero · ES San Romero · PT São Romero",
    "aparecida_celam": "PT Nossa Senhora de Aparecida · ES/EN Aparecida / CELAM",
    "querida_amazonia": "EN Beloved Amazon · ES/PT Querida Amazonia",
    "laudato_si": "EN care for our common home · ES casa común · PT casa comum",
    "evangelii_gaudium": "EN Joy of the Gospel · ES Alegría del Evangelio · PT Alegria do Evangelho",
    "fratelli_tutti": "EN brothers and sisters all · ES Hermanos todos · PT Todos irmãos",
    "amoris_laetitia": "EN Joy of Love · ES Alegría del amor · PT Alegria do Amor",
    "liberation_theology": "EN liberation theology · ES teología de la liberación · PT teologia da libertação",
    "preferential_option": "EN option for the poor · ES opción preferencial · PT opção pelos pobres",
    "immigration": "EN immigration · ES migración · PT imigração",
    "indigenous": "EN indigenous · ES pueblos originarios · PT povos originários",
    "gospel": "EN gospel · ES evangelio · PT evangelho",
    "mission": "EN mission · ES misión · PT missão",
    "eucharist": "EN Eucharist · ES Eucaristía · PT Eucaristia",
    "synod": "EN synod · ES/PT sínodo",
    "catholic_social_teaching": "EN CST · ES doctrina social · PT doutrina social",
    "marian_devotion": "EN Our Lady · ES Nuestra Señora · PT Nossa Senhora",
    "inculturation": "EN inculturation · ES inculturación · PT inculturação",
}

NAMES = {
    "guadalupe": {"en": "Our Lady of Guadalupe", "es": "Virgen de Guadalupe", "pt": "Nossa Senhora de Guadalupe"},
    "oscar_romero": {"en": "Óscar Romero", "es": "San Romero", "pt": "São Romero"},
    "aparecida_celam": {"en": "Aparecida / CELAM", "es": "Aparecida / CELAM", "pt": "Nossa Senhora de Aparecida"},
    "querida_amazonia": {"en": "Beloved Amazon", "es": "Querida Amazonia", "pt": "Querida Amazônia"},
    "laudato_si": {"en": "care for our common home", "es": "casa común", "pt": "casa comum"},
    "evangelii_gaudium": {"en": "Joy of the Gospel", "es": "Alegría del Evangelio", "pt": "Alegria do Evangelho"},
    "fratelli_tutti": {"en": "brothers and sisters all", "es": "Hermanos todos", "pt": "Todos irmãos"},
    "amoris_laetitia": {"en": "Joy of Love", "es": "Alegría del amor", "pt": "Alegria do Amor"},
    "liberation_theology": {"en": "liberation theology", "es": "teología de la liberación", "pt": "teologia da libertação"},
    "preferential_option": {"en": "option for the poor", "es": "opción preferencial", "pt": "opção pelos pobres"},
    "immigration": {"en": "immigration", "es": "migración", "pt": "imigração"},
    "indigenous": {"en": "indigenous", "es": "pueblos originarios", "pt": "povos originários"},
    "gospel": {"en": "gospel", "es": "evangelio", "pt": "evangelho"},
    "mission": {"en": "mission", "es": "misión", "pt": "missão"},
    "eucharist": {"en": "Eucharist", "es": "Eucaristía", "pt": "Eucaristia"},
    "synod": {"en": "synod", "es": "sínodo", "pt": "sínodo"},
    "catholic_social_teaching": {"en": "Catholic social teaching", "es": "doctrina social", "pt": "doutrina social"},
    "marian_devotion": {"en": "Our Lady", "es": "Nuestra Señora", "pt": "Nossa Senhora"},
    "inculturation": {"en": "inculturation", "es": "inculturación", "pt": "inculturação"},
}

CHAPTERS = [
    {"q": "2015Q2", "id": "laudato_si", "label": "Laudato Si'", "en": "care for our common home", "es": "casa común", "pt": "casa comum"},
    {"q": "2016Q2", "id": "amoris_laetitia", "label": "Amoris Laetitia", "caption": "Joy of Love / Alegría del amor / Alegria do Amor"},
    {"q": "2020Q1", "id": "querida_amazonia", "label": "Querida Amazonia", "caption": "Beloved Amazon"},
    {"q": "2020Q4", "id": "fratelli_tutti", "label": "Fratelli Tutti", "en": "brothers and sisters all", "es": "Hermanos todos", "pt": "Todos irmãos"},
    {"q": "2026Q2", "id": "magnifica_humanitas", "label": "Magnifica Humanitas", "en": "Magnificent Humanity", "es": "Magnífica humanidad", "pt": "Magnífica humanidade"},
]
PROMULGATION = {
    "evangelii_gaudium": (2013, 11),
    "lumen_fidei": (2013, 6),
    "laudato_si": (2015, 5),
    "amoris_laetitia": (2016, 4),
    "fratelli_tutti": (2020, 10),
    "querida_amazonia": (2020, 2),
    "christus_vivit": (2019, 3),
    "magnifica_humanitas": (2026, 5),
}

# Francis documents the classroom can watch day-by-day from promulgation.
# Exhortations sit next to encyclicals because the press treats them as one papal wave.
ENCYCLICAL_META = [
    {"id": "evangelii_gaudium", "label": "Evangelii Gaudium", "promulgated": "2013-11-24", "kind": "apostolic exhortation"},
    {"id": "laudato_si", "label": "Laudato Si'", "promulgated": "2015-05-24", "kind": "encyclical"},
    {"id": "amoris_laetitia", "label": "Amoris Laetitia", "promulgated": "2016-04-08", "kind": "apostolic exhortation"},
    {"id": "christus_vivit", "label": "Christus Vivit", "promulgated": "2019-03-25", "kind": "apostolic exhortation"},
    {"id": "querida_amazonia", "label": "Querida Amazonia", "promulgated": "2020-02-02", "kind": "apostolic exhortation"},
    {"id": "fratelli_tutti", "label": "Fratelli Tutti", "promulgated": "2020-10-03", "kind": "encyclical"},
    {"id": "magnifica_humanitas", "label": "Magnifica Humanitas", "promulgated": "2026-05-25", "kind": "encyclical"},
]
ENCYCLICAL_IDS = frozenset(row["id"] for row in ENCYCLICAL_META)
ENCYC_BY_ID = {row["id"]: row for row in ENCYCLICAL_META}
ENCYCLICAL_PATTERNS = tuple(p for p in THEME_PATTERNS if p.label in ENCYCLICAL_IDS)
_ENCYC_PREFILTER = re.compile(
    r"laudato|amoris laetitia|alegr[ií]a del amor|alegria do amor|joy of love|"
    r"fratelli|hermanos todos|todos hermanos|todos irm[aã]os|brothers and sisters all|"
    r"querida amazon|beloved amazon|evangelii gaudium|joy of the gospel|"
    r"alegr[ií]a del evangelio|alegria do evangelho|christus vivit|christ is alive|cristo vive|"
    r"casa com[uú]n|casa comum|"
    r"magnifica humanitas|magnificent humanity|magn[ií]fica humanidad|"
    r"magn[ií]fica humanidade|custodia de la persona humana|salvaguarda da pessoa humana",
    re.I,
)
_FRATELLI_ES = re.compile(r"\bhermanos todos\b|\btodos hermanos\b", re.I)
CENTRAL_FIPS = frozenset({"GT", "BH", "HO", "ES", "NU", "CS", "PM"})
ANDES_REST_FIPS = frozenset({"AR", "CO", "PE", "EC", "BL", "PA", "UY", "VE"})
CARIB_FIPS = frozenset({"CU", "HA", "DR", "JM", "RQ", "TD", "BB", "BF", "GJ", "VC"})
ENCYC_REGION_ORDER = ("US", "MX", "BR", "CI", "andes", "central", "caribbean", "CA", "other")
ENCYC_REGIONS = [
    {"id": "US", "label": "United States", "color": "#e4c37a", "lat": 39.8, "lon": -98.5},
    {"id": "MX", "label": "Mexico", "color": "#e07a5f", "lat": 23.6, "lon": -102.5},
    {"id": "BR", "label": "Brazil", "color": "#9db384", "lat": -14.2, "lon": -51.9},
    {"id": "CI", "label": "Chile", "color": "#7eb8c9", "lat": -35.7, "lon": -71.5},
    {"id": "andes", "label": "Andes / Southern Cone", "color": "#c17b6b", "lat": -16.3, "lon": -68.1},
    {"id": "central", "label": "Central America", "color": "#d4a574", "lat": 13.7, "lon": -88.9},
    {"id": "caribbean", "label": "Caribbean", "color": "#8f9ec9", "lat": 18.5, "lon": -72.3},
    {"id": "CA", "label": "Canada", "color": "#b7b0a3", "lat": 56.1, "lon": -106.3},
    {"id": "other", "label": "elsewhere", "color": "#5c6570", "lat": 41.9, "lon": 12.5},
]

NEWS_FILES = [
    ROOT / "data/us/news/gdelt_us_geolocated_2015_2022_fetched.jsonl",
    ROOT / "data/us/news/gdelt_us_geolocated_2015-01-01_to_2025-12-31.jsonl",
    ROOT / "data/americas/news/gdelt_americas_fetched.jsonl",
]


def news_geo_paths() -> list[Path]:
    """Minimal paragraph JSONL set — no stub/shard double-counts."""
    paths = paragraph_scan_paths(ROOT)
    if paths:
        return paths
    return [p for p in NEWS_FILES if p.exists()]


def text_paragraph_paths() -> list[Path]:
    """Paragraph files for theme harvesting (same inventory as places)."""
    return news_geo_paths()


def _cell_key(lat: float, lon: float) -> str:
    return f"{lat:.4f},{lon:.4f}"


def _parse_cell_key(s: str) -> tuple[float, float]:
    a, b = s.split(",", 1)
    return float(a), float(b)


def _places_worker(path_str: str, max_rows: int = 0) -> dict:
    """Scan one JSONL file; return serializable partial counters (for ProcessPool)."""
    from collections import Counter, defaultdict

    path = Path(path_str)
    cell_n: Counter = Counter()
    cell_fips: dict[str, str] = {}
    cell_adm: dict[str, str] = {}
    adm_n: Counter = Counter()
    adm_lat: dict[str, float] = defaultdict(float)
    adm_lon: dict[str, float] = defaultdict(float)
    adm_fips: dict[str, str] = {}
    fips_n: Counter = Counter()
    fips_lat: dict[str, float] = defaultdict(float)
    fips_lon: dict[str, float] = defaultdict(float)
    metro_n: Counter = Counter()
    qcell: Counter = Counter()
    scanned = with_xy = skipped_xy = 0

    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scanned += 1
            if max_rows and scanned > max_rows:
                break
            try:
                rec = _loads(line)
            except Exception:
                continue
            xy = record_xy(rec)
            if not xy:
                skipped_xy += 1
                continue
            lat, lon = xy
            if lat == 0 and lon == 0:
                skipped_xy += 1
                continue
            with_xy += 1
            fips = record_fips(rec)
            if not fips and path.name.startswith("gdelt_us"):
                fips = "US"
            fips_n[fips] += 1
            fips_lat[fips] += lat
            fips_lon[fips] += lon
            step = 0.3 if fips == "US" else 0.45
            rlat = round(lat / step) * step
            rlon = round(lon / step) * step
            ck = _cell_key(rlat, rlon)
            cell_n[ck] += 1
            cell_fips[ck] = fips or cell_fips.get(ck, "")
            adm = record_adm1(rec)
            if adm and len(adm) >= 4 and adm != fips:
                cell_adm[ck] = adm
                adm_n[adm] += 1
                adm_lat[adm] += lat
                adm_lon[adm] += lon
                adm_fips[adm] = fips
            metro = nearest_metro(lat, lon, fips)
            if metro:
                metro_n[(metro, fips)] += 1
            q = record_quarter(rec)
            if q:
                qcell[(q, round(lat, 1), round(lon, 1), fips)] += 1

    return {
        "cell_n": list(cell_n.items()),
        "cell_fips": cell_fips,
        "cell_adm": cell_adm,
        "adm_n": list(adm_n.items()),
        "adm_lat": dict(adm_lat),
        "adm_lon": dict(adm_lon),
        "adm_fips": adm_fips,
        "fips_n": list(fips_n.items()),
        "fips_lat": dict(fips_lat),
        "fips_lon": dict(fips_lon),
        "metro_n": [((a, b), n) for (a, b), n in metro_n.items()],
        "qcell": [((q, lat, lon, fips), n) for (q, lat, lon, fips), n in qcell.items()],
        "scanned": scanned,
        "with_xy": with_xy,
        "skipped_xy": skipped_xy,
    }


def _merge_places_partials(partials: list[dict]) -> dict:
    cell_n: Counter = Counter()
    cell_fips: dict[tuple, str] = {}
    cell_adm: dict[tuple, str] = {}
    adm_n: Counter = Counter()
    adm_lat: dict[str, float] = defaultdict(float)
    adm_lon: dict[str, float] = defaultdict(float)
    adm_fips: dict[str, str] = {}
    fips_n: Counter = Counter()
    fips_lat: dict[str, float] = defaultdict(float)
    fips_lon: dict[str, float] = defaultdict(float)
    metro_n: Counter = Counter()
    qcell: Counter = Counter()
    scanned = with_xy = skipped_xy = 0

    for part in partials:
        scanned += part.get("scanned", 0)
        with_xy += part.get("with_xy", 0)
        skipped_xy += part.get("skipped_xy", 0)
        for ck, n in part.get("cell_n", []):
            key = _parse_cell_key(ck)
            cell_n[key] += n
            cell_fips[key] = part.get("cell_fips", {}).get(ck, cell_fips.get(key, ""))
            if ck in part.get("cell_adm", {}):
                cell_adm[key] = part["cell_adm"][ck]
        for adm, n in part.get("adm_n", []):
            adm_n[adm] += n
        for adm, v in part.get("adm_lat", {}).items():
            adm_lat[adm] += v
        for adm, v in part.get("adm_lon", {}).items():
            adm_lon[adm] += v
        adm_fips.update(part.get("adm_fips", {}))
        for fips, n in part.get("fips_n", []):
            fips_n[fips] += n
        for fips, v in part.get("fips_lat", {}).items():
            fips_lat[fips] += v
        for fips, v in part.get("fips_lon", {}).items():
            fips_lon[fips] += v
        for (name, fips), n in part.get("metro_n", []):
            metro_n[(name, fips)] += n
        for (q, lat, lon, fips), n in part.get("qcell", []):
            qcell[(q, lat, lon, fips)] += n

    return {
        "cell_n": cell_n,
        "cell_fips": cell_fips,
        "cell_adm": cell_adm,
        "adm_n": adm_n,
        "adm_lat": adm_lat,
        "adm_lon": adm_lon,
        "adm_fips": adm_fips,
        "fips_n": fips_n,
        "fips_lat": fips_lat,
        "fips_lon": fips_lon,
        "metro_n": metro_n,
        "qcell": qcell,
        "scanned": scanned,
        "with_xy": with_xy,
        "skipped_xy": skipped_xy,
    }


def _build_places_from_merged(merged: dict) -> tuple[list[dict], list[dict], list[dict], list[dict], dict, list[dict]]:
    cell_n = merged["cell_n"]
    cell_fips = merged["cell_fips"]
    cell_adm = merged["cell_adm"]
    adm_n = merged["adm_n"]
    adm_lat = merged["adm_lat"]
    adm_lon = merged["adm_lon"]
    adm_fips = merged["adm_fips"]
    fips_n = merged["fips_n"]
    fips_lat = merged["fips_lat"]
    fips_lon = merged["fips_lon"]
    metro_n = merged["metro_n"]
    qcell = merged["qcell"]
    metro_meta = {(name, mfips): (mlat, mlon) for mlat, mlon, name, mfips in METROS}
    scanned = merged["scanned"]
    with_xy = merged["with_xy"]
    skipped_xy = merged["skipped_xy"]

    places = []
    for (lat, lon), n in cell_n.most_common():
        fips = cell_fips.get((lat, lon), "")
        adm = cell_adm.get((lat, lon), "")
        metro = nearest_metro(lat, lon, fips)
        places.append(
            {
                "lat": round(lat, 3),
                "lon": round(lon, 3),
                "n": int(n),
                "fips": fips,
                "country": fips_country_name(fips) if fips else "",
                "adm": adm,
                "region": adm_label(adm, fips) if adm else "",
                "metro": metro,
                "us": fips == "US",
            }
        )
        if len(places) >= 1800:
            break

    states = []
    for adm, n in adm_n.most_common():
        fips = adm_fips.get(adm, adm[:2])
        if n < 8:
            continue
        states.append(
            {
                "id": adm,
                "label": adm_label(adm, fips),
                "fips": fips,
                "country": fips_country_name(fips),
                "lat": round(adm_lat[adm] / n, 3),
                "lon": round(adm_lon[adm] / n, 3),
                "n": int(n),
                "us": fips == "US",
            }
        )

    metros = []
    for (name, fips), n in metro_n.most_common():
        if n < 12:
            continue
        lat, lon = metro_meta[(name, fips)]
        metros.append(
            {
                "name": name,
                "fips": fips,
                "country": fips_country_name(fips),
                "lat": lat,
                "lon": lon,
                "n": int(n),
                "us": fips == "US",
            }
        )

    countries = []
    for fips, n in fips_n.most_common():
        if not fips or n < 5:
            continue
        countries.append(
            {
                "fips": fips,
                "country": fips_country_name(fips),
                "n": int(n),
                "lat": round(fips_lat[fips] / n, 3),
                "lon": round(fips_lon[fips] / n, 3),
                "host": fips == "CI",
            }
        )

    us_n = fips_n.get("US", 0)
    meta = {
        "news_scanned": scanned,
        "news_with_latlon": with_xy,
        "skipped_no_latlon": skipped_xy,
        "place_cells": len(places),
        "us_n": us_n,
        "us_share": round(us_n / max(with_xy, 1), 3),
        "inventory": "paragraph_scan",
        "top_countries": [
            {"fips": f, "country": fips_country_name(f), "n": n}
            for f, n in fips_n.most_common(12)
        ],
        "top_us_states": [
            {"label": s["label"], "n": s["n"]}
            for s in states
            if s["us"]
        ][:12],
    }
    all_pulses = []
    for (q, lat, lon, fips), n in qcell.most_common(2800):
        all_pulses.append(
            {
                "q": q,
                "lat": lat,
                "lon": lon,
                "n": int(n),
                "fips": fips,
            }
        )
    write(
        f"Places: {with_xy:,} geocoded rows / {scanned:,} scanned → "
        f"{len(places)} cells, {len(states)} ADM1, {len(metros)} metros, {len(all_pulses)} time cells"
    )
    return places, states, metros, countries, meta, all_pulses

_PREFILTER = re.compile(
    r"guadalupe|romero|laudato|evangelii\s+gaudium|joy of the gospel|alegr[ií]a del evangelio|alegria do evangelho|"
    r"fratelli|hermanos todos|todos irm[aã]os|aparecida|\bcelam\b|querida amazonia|beloved amazon|"
    r"liberaci[oó]n|liberta[cç][aã]o|liberation theology|"
    r"preferential option|opci[oó]n preferencial|op[cç][aã]o pelos pobres|"
    r"immigr|migraci|imigra|indígen|indigenous|pueblos originarios|povos origin|"
    r"evangelio|evangelho|\bgospel\b|\bmission|\bmisi[oó]n|miss[aã]o|eucharist|eucarist|s[ií]nodo|\bsynod|"
    r"doctrina social|catholic social|doutrina social|nossa senhora|nuestra se[nñ]ora|our lady|"
    r"casa com[uú]n|casa comum|amoris laetitia|incultur|catequese|catequesis",
    re.I,
)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(_loads(line))
    return rows


def fips_of(nid: str) -> str:
    return nid.split(":", 1)[-1]


def theme_of(nid: str) -> str:
    return nid.split(":", 1)[-1]


def pretty_theme(tid: str, fallback: str = "") -> str:
    if tid in PRETTY:
        return PRETTY[tid]
    lab = fallback or tid
    return lab.replace("_", " ")


def record_xy(rec: dict) -> tuple[float, float] | None:
    try:
        lat = float(rec.get("action_lat"))
        lon = float(rec.get("action_lon"))
        if lat == 0 and lon == 0:
            raise ValueError
        return lat, lon
    except (TypeError, ValueError):
        pass
    api = rec.get("api_raw")
    if not isinstance(api, dict):
        return None
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


def record_fips(rec: dict) -> str:
    raw = rec.get("action_country") or ""
    if not raw:
        api = rec.get("api_raw")
        if isinstance(api, dict):
            raw = api.get("col_51") or api.get("ActionGeo_CountryCode") or ""
    return str(raw or "").upper()[:2]


def record_adm1(rec: dict) -> str:
    api = rec.get("api_raw")
    if not isinstance(api, dict):
        return str(rec.get("action_adm1") or "").upper().strip()
    return str(api.get("col_52") or rec.get("action_adm1") or "").upper().strip()


def record_quarter(rec: dict) -> str:
    raw = str(rec.get("gdelt_day") or rec.get("date") or "").strip()
    digits = "".join(ch for ch in raw[:10] if ch.isdigit())
    if len(digits) < 6:
        return ""
    y, m = int(digits[:4]), int(digits[4:6])
    if not (2015 <= y <= 2026) or not (1 <= m <= 12):
        return ""
    return f"{y}Q{(m - 1) // 3 + 1}"


def record_day(rec: dict) -> str:
    raw = str(rec.get("gdelt_day") or rec.get("date") or "").strip()
    digits = "".join(ch for ch in raw[:10] if ch.isdigit())
    if len(digits) < 8:
        return ""
    y, m, d = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return ""


def parse_iso(day: str) -> date | None:
    try:
        return date.fromisoformat(day[:10])
    except ValueError:
        return None


def region_bucket(fips: str) -> str:
    if fips in {"US", "MX", "BR", "CI", "CA"}:
        return fips
    if fips in CENTRAL_FIPS:
        return "central"
    if fips in ANDES_REST_FIPS:
        return "andes"
    if fips in CARIB_FIPS:
        return "caribbean"
    return "other"


def fips_from_xy(lat: float, lon: float) -> str:
    best, best_d = "", 9e9
    for fips, (clat, clon) in CENTROIDS.items():
        d = (lat - clat) ** 2 + (lon - clon) ** 2
        if d < best_d:
            best, best_d = fips, d
    return best


def match_encyclicals(text: str) -> set[str]:
    if not text or not _ENCYC_PREFILTER.search(text):
        return set()
    hits: set[str] = set()
    for lang in ("english", "spanish", "portuguese"):
        hits |= match_theme_labels(text, lang, ENCYCLICAL_PATTERNS)
    if _FRATELLI_ES.search(text):
        hits.add("fratelli_tutti")
    return hits & ENCYCLICAL_IDS


def canonical_theme(label: str) -> str:
    return THEME_ALIAS.get(label, label)


def after_promulgation(label: str, quarter: str) -> bool:
    prom = PROMULGATION.get(label)
    if not prom or not quarter:
        return True
    y = int(quarter[:4])
    q = int(quarter[-1])
    month = 1 + (q - 1) * 3
    return (y, month) >= prom


def match_featured(text: str) -> set[str]:
    if not text or not _PREFILTER.search(text):
        return set()
    hits: set[str] = set()
    for lang in ("english", "spanish", "portuguese"):
        hits |= match_theme_labels(text, lang, FEATURED_PATTERNS)
    return {canonical_theme(lab) for lab in hits}


def iter_article_blobs(path: Path):
    """Yield (rec, text) grouped by article_id / url from paragraph JSONL."""
    cur = None
    buf: list[str] = []
    meta = None
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = _loads(line)
            except Exception:
                continue
            para = rec.get("paragraph_text")
            if not para:
                continue
            aid = rec.get("article_id") or rec.get("url") or rec.get("event_id")
            if cur is None:
                cur, meta, buf = aid, rec, [str(para)]
                continue
            if aid == cur:
                if sum(len(x) for x in buf) < 8000:
                    buf.append(str(para))
                continue
            yield meta, " ".join(buf)[:8000]
            cur, meta, buf = aid, rec, [str(para)]
    if meta is not None and buf:
        yield meta, " ".join(buf)[:8000]


def adm_label(adm: str, fips: str) -> str:
    if fips == "US" and len(adm) >= 4 and adm.startswith("US"):
        return US_STATES.get(adm[2:4], adm[2:4])
    if adm in MX_ADM:
        return MX_ADM[adm]
    if adm in BR_ADM:
        return BR_ADM[adm]
    return adm


def nearest_metro(lat: float, lon: float, fips: str) -> str:
    rad = 0.75 if fips == "US" else 0.85
    best, best_d = "", rad ** 2
    for mlat, mlon, name, mfips in METROS:
        if mfips != fips:
            continue
        d = (lat - mlat) ** 2 + (lon - mlon) ** 2
        if d < best_d:
            best, best_d = name, d
    return best


def harvest_places(
    *,
    use_cache: bool = False,
    jobs: int | None = None,
    max_rows: int = 0,
) -> tuple[list[dict], list[dict], list[dict], list[dict], dict, list[dict]]:
    paths = news_geo_paths()
    fp = inventory_fingerprint(paths)
    if max_rows:
        fp = f"{fp}_max{max_rows}"
    cache_file = cache_path(CACHE_DIR, "places", fp)
    if use_cache:
        cached = load_cache(cache_file)
        if cached:
            write(f"Places cache hit ({cache_file.name})")
            return (
                cached["places"],
                cached["states"],
                cached["metros"],
                cached["countries"],
                cached["geo"],
                cached["all_pulses"],
            )

    jobs = jobs or default_jobs()
    max_rows = max_rows or _MAX_NEWS_ROWS
    partials: list[dict] = []
    if jobs > 1 and len(paths) > 1:
        from concurrent.futures import ProcessPoolExecutor, as_completed

        write(f"Scanning {len(paths)} files with {jobs} workers")
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futs = {
                pool.submit(_places_worker, str(p), max_rows): p
                for p in paths
                if p.exists()
            }
            for fut in as_completed(futs):
                path = futs[fut]
                write(f"  done {path.name}")
                partials.append(fut.result())
    else:
        for path in paths:
            write(f"Scanning {path.name}")
            partials.append(_places_worker(str(path), max_rows))

    merged = _merge_places_partials(partials)
    result = _build_places_from_merged(merged)
    if use_cache:
        save_cache(
            cache_file,
            {
                "places": result[0],
                "states": result[1],
                "metros": result[2],
                "countries": result[3],
                "geo": result[4],
                "all_pulses": result[5],
            },
        )
        write(f"Cached places → {cache_file.name}")
    return result


def harvest_spread() -> dict:
    """Theme × quarter × place from fetched paragraphs. EN/ES/PT names are one topic."""
    pulse: Counter = Counter()
    theme_n: Counter = Counter()
    first_fips: dict[str, dict[str, str]] = defaultdict(dict)
    seen: set[str] = set()
    articles = 0
    with_theme = 0
    for path in text_paragraph_paths():
        if not path.exists():
            continue
        write(f"Themes {path.name}")
        default_us = "gdelt_us" in path.name
        n_here = 0
        for rec, text in iter_article_blobs(path):
            uid = str(rec.get("article_id") or rec.get("url") or "")
            if uid:
                if uid in seen:
                    continue
                seen.add(uid)
            articles += 1
            n_here += 1
            xy = record_xy(rec)
            if not xy:
                continue
            lat, lon = xy
            if not (-60 <= lat <= 75 and -170 <= lon <= -20):
                continue
            q = record_quarter(rec)
            if not q:
                continue
            themes = match_featured(text)
            if not themes:
                continue
            fips = record_fips(rec) or ("US" if default_us else "")
            with_theme += 1
            step = 0.5 if fips == "US" else 0.7
            blat = round(lat / step) * step
            blon = round(lon / step) * step
            for lab in themes:
                if not after_promulgation(lab, q):
                    continue
                theme_n[lab] += 1
                pulse[(lab, q, blat, blon, fips)] += 1
                if not fips:
                    continue
                prev = first_fips[lab].get(fips)
                if prev is None or q < prev:
                    first_fips[lab][fips] = q
            if n_here % 25000 == 0:
                write(f"  {n_here:,} articles · {with_theme:,} with a featured theme")
        write(f"  {n_here:,} articles in {path.name}")

    months = []
    for y in range(2015, 2026):
        for q in range(1, 5):
            months.append(f"{y}Q{q}")

    by_theme: dict[str, list] = defaultdict(list)
    for (lab, q, lat, lon, fips), n in pulse.most_common():
        bucket = by_theme[lab]
        if len(bucket) >= 700:
            continue
        by_theme[lab].append(
            {
                "q": q,
                "lat": round(lat, 2),
                "lon": round(lon, 2),
                "n": int(n),
                "fips": fips,
            }
        )

    catalog = []
    for lab, n in theme_n.most_common():
        origins = [
            {
                "fips": f,
                "country": fips_country_name(f),
                "q": q,
            }
            for f, q in sorted(first_fips[lab].items(), key=lambda kv: (kv[1], kv[0]))
        ]
        catalog.append(
            {
                "id": lab,
                "label": pretty_theme(lab),
                "also": ALSO.get(lab, ""),
                "names": NAMES.get(lab) or {},
                "group": theme_group(lab),
                "n": int(n),
                "first": origins[0]["q"] if origins else "",
                "origins": origins[:10],
            }
        )

    write(f"Spread: {articles:,} articles · {with_theme:,} themed · {len(catalog)} topics")
    return {
        "note": "English, Spanish, and Portuguese names count as one topic (gospel = evangelio = evangelho). Dots are fetched-text stories, not the full GDELT stub file.",
        "months": months,
        "catalog": catalog,
        "themes": {row["id"]: by_theme[row["id"]] for row in catalog},
        "chapters": CHAPTERS,
        "names": NAMES,
    }


def encyclical_text_paths() -> list[Path]:
    paths = paragraph_scan_paths(ROOT)
    if paths:
        return paths
    return [p for p in NEWS_FILES if p.exists()]


def harvest_encyclicals() -> dict:
    """Daily mentions of papal documents by writing region, from promulgation day."""
    corpus_start = date(2015, 1, 1)
    counts: dict[str, Counter] = {row["id"]: Counter() for row in ENCYCLICAL_META}
    first: dict[str, dict[str, int]] = {row["id"]: {} for row in ENCYCLICAL_META}
    geo_n: dict[str, Counter] = {row["id"]: Counter() for row in ENCYCLICAL_META}
    seen: set[str] = set()
    articles = 0
    with_hit = 0
    for path in encyclical_text_paths():
        write(f"Encyclicals {path.name}")
        default_us = "gdelt_us" in path.name
        n_here = 0
        for rec, text in iter_article_blobs(path):
            uid = str(rec.get("article_id") or rec.get("url") or "")
            if uid:
                if uid in seen:
                    continue
                seen.add(uid)
            articles += 1
            n_here += 1
            labs = match_encyclicals(text)
            if not labs:
                continue
            day_s = record_day(rec)
            day = parse_iso(day_s)
            if not day or day < corpus_start:
                continue
            xy = record_xy(rec)
            fips = record_fips(rec) or ("US" if default_us else "")
            if not fips and xy:
                fips = fips_from_xy(*xy)
            rid = region_bucket(fips)
            lat = lon = None
            if xy:
                lat, lon = xy
            else:
                for row in ENCYC_REGIONS:
                    if row["id"] == rid:
                        lat, lon = row["lat"], row["lon"]
                        break
            with_hit += 1
            for lab in labs:
                meta = ENCYC_BY_ID[lab]
                prom = parse_iso(meta["promulgated"])
                start = max(prom, corpus_start) if prom else corpus_start
                if day < start:
                    continue
                offset = (day - start).days
                counts[lab][(offset, rid)] += 1
                prev = first[lab].get(rid)
                if prev is None or offset < prev:
                    first[lab][rid] = offset
                if lat is not None:
                    blat = round(lat / 0.25) * 0.25
                    blon = round(lon / 0.25) * 0.25
                    geo_n[lab][(offset, blat, blon, rid, (fips or "")[:2])] += 1
            if n_here % 25000 == 0:
                write(f"  {n_here:,} articles · {with_hit:,} papal documents")
        write(f"  {n_here:,} articles in {path.name}")

    items = {}
    for meta in ENCYCLICAL_META:
        lab = meta["id"]
        by_day: dict[int, list[int]] = {}
        for (offset, rid), n in counts[lab].items():
            row = by_day.setdefault(offset, [0] * len(ENCYC_REGION_ORDER))
            row[ENCYC_REGION_ORDER.index(rid)] += int(n)
        if not by_day:
            continue
        hits = [[d, *by_day[d]] for d in sorted(by_day)]
        totals = [0] * len(ENCYC_REGION_ORDER)
        peak_d, peak_n = 0, 0
        n_all = 0
        for d, *vals in hits:
            s = sum(vals)
            n_all += s
            if s > peak_n:
                peak_d, peak_n = d, s
            for i, v in enumerate(vals):
                totals[i] += v
        prom = parse_iso(meta["promulgated"])
        start = max(prom, corpus_start)
        peak_date = (start + timedelta(days=peak_d)).isoformat()
        geo = []
        for (d, lat, lon, rid, fips), n in geo_n[lab].most_common():
            geo.append(
                {
                    "d": int(d),
                    "lat": round(lat, 3),
                    "lon": round(lon, 3),
                    "n": int(n),
                    "rid": rid,
                    "fips": fips or (rid if len(rid) == 2 else ""),
                }
            )
            if len(geo) >= 2200:
                break
        items[lab] = {
            "id": lab,
            "label": meta["label"],
            "kind": meta["kind"],
            "promulgated": meta["promulgated"],
            "start": start.isoformat(),
            "n": n_all,
            "max_d": int(max(by_day)),
            "hits": hits,
            "geo": geo,
            "first": first[lab],
            "totals": {ENCYC_REGION_ORDER[i]: totals[i] for i, v in enumerate(totals) if v},
            "peak": {"d": peak_d, "n": peak_n, "date": peak_date},
        }
        write(
            f"  {meta['label']}: {n_all:,} stories · {len(hits)} days · {len(geo)} map cells"
        )

    return {
        "note": "Each map dot is an ActionGeo writing cell for a story that names the document. The chart stacks those stories by region from the promulgation day. 7-day rolling when you pick This day.",
        "corpus_start": "2015-01-01",
        "regions": ENCYC_REGIONS,
        "items": items,
    }


def teaching_payload() -> tuple[list[dict], list[dict]]:
    nodes = load_jsonl(NET / "country_teaching" / "nodes.jsonl")
    edges = load_jsonl(NET / "country_teaching" / "edges.jsonl")
    out_nodes = []
    for n in nodes:
        row = dict(n)
        if row.get("item_type") == "country":
            fips = str(row.get("fips") or fips_of(row["id"]))
            lat, lon = CENTROIDS.get(fips, (0.0, -70.0))
            row["lat"] = lat
            row["lon"] = lon
            row["host"] = fips == "CI"
        elif row.get("item_type") == "theme":
            tid = theme_of(row["id"])
            row["pretty"] = pretty_theme(tid, str(row.get("label") or ""))
        out_nodes.append(row)
    out_edges = []
    for e in edges:
        if e.get("type") != "teaches":
            continue
        c, t = fips_of(e["source"]), theme_of(e["target"])
        lift = float(e.get("lift_vs_us") or 0)
        out_edges.append(
            {
                "source": e["source"],
                "target": e["target"],
                "fips": c,
                "theme": t,
                "hits": int(e.get("weight") or 0),
                "lift": round(lift, 2),
                "distinctive": bool(e.get("distinctive")),
                "hypothesized": (c, t) in HYP,
                "weight": round(math.log1p(max(lift, 0)), 3),
            }
        )
    return out_nodes, out_edges


def topics_payload() -> dict:
    nodes = load_jsonl(NET / "theme_cooccurrence" / "nodes.jsonl")
    edges = load_jsonl(NET / "theme_cooccurrence" / "edges.jsonl")
    out_n = []
    for n in nodes:
        tid = theme_of(n["id"])
        out_n.append(
            {
                "id": n["id"],
                "label": pretty_theme(tid, str(n.get("label") or "")),
                "group": n.get("group") or "other",
                "papal": bool(n.get("papal")),
                "n": int(n.get("n") or 0),
                "degree": int(n.get("degree") or 0),
            }
        )
    out_e = []
    for e in edges:
        if e.get("type") != "cooccurs":
            continue
        lift = float(e.get("lift") or 0)
        out_e.append(
            {
                "source": e["source"],
                "target": e["target"],
                "n": int(e.get("weight") or 0),
                "lift": round(lift, 2),
            }
        )
    return {"nodes": out_n, "edges": out_e}


def load_existing_payload() -> dict | None:
    if not OUT.exists():
        return None
    text = OUT.read_text(encoding="utf-8")
    prefix = "window.VIZ = "
    if not text.startswith(prefix):
        return None
    payload = json.loads(text[len(prefix) :].rstrip().rstrip(";").rstrip())
    return payload if isinstance(payload, dict) else None


def load_existing_spread() -> dict | None:
    payload = load_existing_payload()
    if not payload:
        return None
    spread = payload.get("spread")
    return spread if isinstance(spread, dict) else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-themes",
        action="store_true",
        help="Reuse theme pulses from existing data.js (places still re-harvested).",
    )
    parser.add_argument(
        "--encyclicals-only",
        action="store_true",
        help="Harvest daily encyclical series and merge into existing data.js.",
    )
    parser.add_argument(
        "--skip-encyclicals",
        action="store_true",
        help="Do not harvest daily encyclical series.",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Reuse viz/.cache/ when source JSONL mtimes unchanged.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=0,
        help=f"Parallel file workers for place scan (default {default_jobs()} on this Mac).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Cap rows per news file (or set VIZ_MAX_NEWS_ROWS).",
    )
    args = parser.parse_args()
    section("Export interactive Places + Topics")
    if args.encyclicals_only:
        payload = load_existing_payload()
        if not payload:
            raise SystemExit("Need an existing data.js before --encyclicals-only")
        payload["encyclicals"] = harvest_encyclicals()
        OUT.write_text("window.VIZ = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
        n_docs = len((payload["encyclicals"] or {}).get("items") or {})
        write(f"Wrote {OUT.name} with {n_docs} papal-document day series")
        return
    t_nodes, t_edges = teaching_payload()
    topics = topics_payload()
    places, states, metros, countries, geo_meta, all_pulses = harvest_places(
        use_cache=args.use_cache,
        jobs=args.jobs or None,
        max_rows=args.max_rows,
    )
    spread = load_existing_spread() if args.skip_themes else None
    if spread is None:
        spread = harvest_spread()
    else:
        write("Reusing theme pulses from existing data.js")
    spread["all"] = all_pulses
    encyclicals = None if args.skip_encyclicals else harvest_encyclicals()
    if encyclicals is None:
        old = load_existing_payload() or {}
        encyclicals = old.get("encyclicals") or {"items": {}, "regions": ENCYC_REGIONS}
    payload = {
        "title": "How the Americas Hear the Church",
        "qap": "QAP r=0.38, p<0.001 · origin 6/6",
        "note": "Dots are ActionGeo writing locations, not viewership. The U.S. is many cities, not one blob. Topic filter treats English, Spanish, and Portuguese as the same teaching.",
        "teaching_map": {k: list(v) for k, v in TEACHING_MAP.items()},
        "teaching": {"nodes": t_nodes, "edges": t_edges},
        "topics": topics,
        "places": places,
        "states": states,
        "metros": metros,
        "countries": countries,
        "geo": geo_meta,
        "spread": spread,
        "encyclicals": encyclicals,
    }
    OUT.write_text("window.VIZ = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
    write(
        f"Wrote {OUT.name}  places={len(places)}  metros={len(metros)}  "
        f"topics={len(topics['nodes'])}n/{len(topics['edges'])}e"
    )


if __name__ == "__main__":
    main()
