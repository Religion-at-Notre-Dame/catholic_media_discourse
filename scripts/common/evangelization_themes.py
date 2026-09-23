"""Lexicons for evangelization framing, theological accents, and Americas regions.

Theological accents (RQ8) are a light discourse lens — not systematic theology.
They help distinguish magisterial / liberation / popular / sacramental speech
within media text about Catholic evangelization in the Americas.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

# Search keywords (collection) — mission / pastoral terms (CST encyclicals live in cst_papal_documents).
EVANGELIZATION_KEYWORDS_EN = [
    "evangelization",
    "new evangelization",
    "missionary",
    "pastoral",
    "catechesis",
    "kerygma",
    "liberation theology",
    "preferential option",
    "inculturation",
    "Our Lady of Guadalupe",
    "discipleship",
    "preferential option for the poor",
]

EVANGELIZATION_KEYWORDS_ES = [
    "evangelización",
    "evangelizacion",
    "nueva evangelización",
    "misión",
    "misionero",
    "pastoral",
    "catequesis",
    "evangelio",
    "testimonio",
    "teología de la liberación",
    "opción preferencial",
    "inculturación",
    "Virgen de Guadalupe",
    "discipulado",
    "opción por los pobres",
]

EVANGELIZATION_KEYWORDS_PT = [
    "evangelização",
    "evangelizacao",
    "nova evangelização",
    "missão",
    "missionário",
    "missionario",
    "pastoral",
    "catequese",
    "evangelho",
    "testemunho",
    "teologia da libertação",
    "teologia da libertacao",
    "opção preferencial",
    "opcao preferencial",
    "inculturação",
    "inculturacao",
    "Nossa Senhora de Aparecida",
    "Nossa Senhora de Guadalupe",
    "discipulado",
    "opção pelos pobres",
    "opcao pelos pobres",
    "comunidades eclesiais de base",
]

THEME_GROUP_LABELS = {
    "core_mission": "Core mission & evangelization",
    "formation": "Pastoral formation & catechesis",
    "cultural_context": "Cultural & social context",
    "theology": "Theological accents",
}

# Accent buckets for RQ8 (a record may hit multiple)
THEOLOGY_ACCENT_LABELS = {
    "magisterial": "Magisterial / conciliar evangelization",
    "liberation": "Liberation / preferential option",
    "popular_piety": "Popular piety & Marian devotion",
    "sacramental": "Sacramental life & discipleship",
    "inculturation": "Inculturation",
    "synodal": "Synodal ecclesiology",
}

CORE_MISSION_EN = frozenset({"evangelization", "new_evangelization", "mission", "gospel"})
CORE_MISSION_ES = frozenset({"evangelization", "nueva_evangelizacion", "mision", "evangelio"})
CORE_MISSION_PT = frozenset({"evangelization", "nueva_evangelizacion", "mision", "evangelio"})
FORMATION_THEMES = frozenset({"pastoral", "catechesis", "youth", "synod", "witness"})
CULTURAL_THEMES = frozenset({"immigration", "indigenous", "us_latino"})
THEOLOGY_THEMES = frozenset(
    {
        "new_evangelization",
        "nueva_evangelizacion",
        "evangelii_gaudium",
        "aparecida_celam",
        "liberation_theology",
        "preferential_option",
        "guadalupe",
        "popular_piety",
        "inculturation",
        "sacrament",
        "eucharist",
        "conversion_discipleship",
        "synodality",
        "kerygma",
        "laudato_si",
        "fratelli_tutti",
        "evangelii_nuntiandi",
        "redemptoris_missio",
        "rerum_novarum",
        "quadragesimo_anno",
        "divini_redemptoris",
        "mater_et_magistra",
        "pacem_in_terris",
        "populorum_progressio",
        "octogesima_adveniens",
        "laborem_exercens",
        "familiaris_consortio",
        "sollicitudo_rei_socialis",
        "christifideles_laici",
        "centesimus_annus",
        "evangelium_vitae",
        "fides_et_ratio",
        "deus_caritas_est",
        "spe_salvi",
        "caritas_in_veritate",
        "lumen_fidei",
        "amoris_laetitia",
        "gaudete_et_exsultate",
        "christus_vivit",
        "querida_amazonia",
        "laudate_deum",
        "dilexit_nos",
        "magnifica_humanitas",
        "marian_devotion",
        "catholic_social_teaching",
        "base_communities",
        "oscar_romero",
    }
)

# Map theme labels → theological accent(s)
THEME_TO_ACCENTS: dict[str, frozenset[str]] = {
    "new_evangelization": frozenset({"magisterial"}),
    "nueva_evangelizacion": frozenset({"magisterial"}),
    "evangelii_gaudium": frozenset({"magisterial"}),
    "aparecida_celam": frozenset({"magisterial", "inculturation"}),
    "kerygma": frozenset({"magisterial", "sacramental"}),
    "liberation_theology": frozenset({"liberation"}),
    "preferential_option": frozenset({"liberation"}),
    "guadalupe": frozenset({"popular_piety", "inculturation"}),
    "marian_devotion": frozenset({"popular_piety"}),
    "catholic_social_teaching": frozenset({"liberation", "magisterial"}),
    "base_communities": frozenset({"liberation", "inculturation"}),
    "oscar_romero": frozenset({"liberation", "popular_piety"}),
    "popular_piety": frozenset({"popular_piety"}),
    "inculturation": frozenset({"inculturation"}),
    "sacrament": frozenset({"sacramental"}),
    "eucharist": frozenset({"sacramental"}),
    "conversion_discipleship": frozenset({"sacramental"}),
    "synodality": frozenset({"synodal"}),
    "synod": frozenset({"synodal"}),
    "laudato_si": frozenset({"magisterial"}),
    "fratelli_tutti": frozenset({"magisterial"}),
    "evangelii_nuntiandi": frozenset({"magisterial"}),
    "redemptoris_missio": frozenset({"magisterial"}),
    "rerum_novarum": frozenset({"magisterial", "liberation"}),
    "quadragesimo_anno": frozenset({"magisterial", "liberation"}),
    "divini_redemptoris": frozenset({"magisterial"}),
    "mater_et_magistra": frozenset({"magisterial", "liberation"}),
    "pacem_in_terris": frozenset({"magisterial"}),
    "populorum_progressio": frozenset({"magisterial", "liberation"}),
    "octogesima_adveniens": frozenset({"magisterial", "liberation"}),
    "laborem_exercens": frozenset({"magisterial", "liberation"}),
    "familiaris_consortio": frozenset({"magisterial"}),
    "sollicitudo_rei_socialis": frozenset({"magisterial", "liberation"}),
    "christifideles_laici": frozenset({"magisterial"}),
    "centesimus_annus": frozenset({"magisterial", "liberation"}),
    "evangelium_vitae": frozenset({"magisterial"}),
    "fides_et_ratio": frozenset({"magisterial"}),
    "deus_caritas_est": frozenset({"magisterial"}),
    "spe_salvi": frozenset({"magisterial"}),
    "amoris_laetitia": frozenset({"magisterial"}),
    "lumen_fidei": frozenset({"magisterial"}),
    "caritas_in_veritate": frozenset({"magisterial", "liberation"}),
    "gaudete_et_exsultate": frozenset({"magisterial"}),
    "christus_vivit": frozenset({"magisterial"}),
    "querida_amazonia": frozenset({"magisterial", "inculturation"}),
    "laudate_deum": frozenset({"magisterial"}),
    "dilexit_nos": frozenset({"magisterial"}),
    "magnifica_humanitas": frozenset({"magisterial"}),
    # Discourse bridges (not pure theology labels, but accent signals in Americas media)
    "immigration": frozenset({"liberation"}),
    "indigenous": frozenset({"inculturation", "liberation"}),
}


@dataclass(frozen=True)
class ThemePattern:
    label: str
    pattern: re.Pattern[str]
    language: str  # english | spanish | portuguese | both
    group: str


THEME_PATTERNS: tuple[ThemePattern, ...] = (
    # --- core mission ---
    ThemePattern("evangelization", re.compile(r"\bevangeliz\w*\b", re.I), "both", "core_mission"),
    ThemePattern("new_evangelization", re.compile(r"\bnew evangelization\b", re.I), "english", "core_mission"),
    ThemePattern("nueva_evangelizacion", re.compile(r"\bnueva evangelizaci[oó]n\b|\bnova evangeliza[cç][aã]o\b", re.I), "spanish", "core_mission"),
    ThemePattern("mission", re.compile(r"\bmission(?:ary|s)?\b", re.I), "english", "core_mission"),
    ThemePattern("mision", re.compile(r"\bmisi[oó]n(?:ero|es)?\b|\bmiss[aã]o\b|\bmission[aá]ri[oa]s?\b", re.I), "spanish", "core_mission"),
    ThemePattern("gospel", re.compile(r"\bgospel\b", re.I), "english", "core_mission"),
    ThemePattern("evangelio", re.compile(r"\bevangelio\b|\bevangelho\b", re.I), "spanish", "core_mission"),
    ThemePattern("kerygma", re.compile(r"\bkerygma\b|\bquerigma\b", re.I), "both", "theology"),
    # --- formation ---
    ThemePattern("pastoral", re.compile(r"\bpastoral\b", re.I), "both", "formation"),
    ThemePattern("catechesis", re.compile(r"\bcatequesis\b|\bcatechesis\b", re.I), "both", "formation"),
    ThemePattern("synod", re.compile(r"\bsynod(?:al)?\b|\bs[ií]nodo\b", re.I), "both", "formation"),
    ThemePattern("youth", re.compile(r"\byouth\b|\bjuventud\b|\bj[oó]venes\b|\bjovens\b", re.I), "both", "formation"),
    ThemePattern("witness", re.compile(r"\bwitness\b|\btestimonio\b|\btestemunho\b|\btestimony\b", re.I), "both", "formation"),
    # --- cultural context ---
    ThemePattern("immigration", re.compile(r"\bimmigr\w*\b|\bmigraci[oó]n\b|\bimigra[cç][aã]o\b|\bmigrant\w*\b|\bfrontera\b|\bfronteira\b", re.I), "both", "cultural_context"),
    ThemePattern("indigenous", re.compile(r"\bindigenous\b|\bnative american\b|\bfirst nations\b|\bpueblos originarios\b|\bpovos origin[aá]rios\b|\bind[ií]genas?\b|\btribal\b", re.I), "both", "cultural_context"),
    # --- theological accents (RQ8) ---
    ThemePattern(
        "evangelii_gaudium",
        re.compile(r"\bevangelii gaudium\b|\bjoy of the gospel\b|\balegr[ií]a del evangelio\b|\balegría do evangelho\b|\balegria do evangelho\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "aparecida_celam",
        re.compile(r"\baparecida\b|\bcelam\b|\bconference of latin american bishops\b|\bconsejo episcopal latinoamericano\b|\bconselho episcopal latino-americano\b|\bconfer[eê]ncia nacional dos bispos do brasil\b|\bcnbb\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "liberation_theology",
        re.compile(
            r"\bliberation theology\b|\btheology of liberation\b|\bteolog[ií]a de la liberaci[oó]n\b|"
            r"\bteologia da liberta[cç][aã]o\b|"
            r"\bliberation(?:ist)? theolog\w*\b",
            re.I,
        ),
        "both",
        "theology",
    ),
    ThemePattern(
        "preferential_option",
        re.compile(
            r"\bpreferential option\b|\boption for the poor\b|\bopci[oó]n preferencial\b|"
            r"\bopci[oó]n por los pobres\b|"
            r"\bop[cç][aã]o preferencial\b|\bop[cç][aã]o pelos pobres\b|"
            r"\bpreferencia(?:l)? por los pobres\b|\bpreferential love of the poor\b",
            re.I,
        ),
        "both",
        "theology",
    ),
    ThemePattern(
        "guadalupe",
        re.compile(r"\bguadalupe\b|\bour lady of guadalupe\b|\bvirgen de guadalupe\b|\bnuestra se[nñ]ora de guadalupe\b|\bnossa senhora de guadalupe\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "marian_devotion",
        re.compile(
            r"\b(?:Our Lady of|Nuestra Se[nñ]ora de|Nossa Senhora de|Virgen de)\b|"
            r"\b(?:Marian|Mar[ií]a)\b.{0,40}\b(?:devotion|devoci[oó]n|pilgrimage|peregrinaci[oó]n)\b|"
            r"\b(?:Fatima|F[aá]tima|Lourdes|Aparecida|Caridad del Cobre|Altagracia|San Juan de los Lagos)\b",
            re.I,
        ),
        "both",
        "theology",
    ),
    ThemePattern(
        "catholic_social_teaching",
        re.compile(
            r"\bcatholic social teaching\b|\bsocial doctrine\b|\bdoctrina social\b|\bdoutrina social\b|"
            r"\bcommon good\b|\bbien com[uú]n\b|\bbem comum\b|\bhuman dignity\b|\bdignidad humana\b|\bdignidade humana\b|"
            r"\bsolidarity\b|\bsolidaridad\b|\bsolidariedade\b|\bsubsidiarity\b|\bsubsidiari(?:edad|ty|edade)\b",
            re.I,
        ),
        "both",
        "theology",
    ),
    ThemePattern(
        "base_communities",
        re.compile(
            r"\bbase (?:ecclesial |christian )?communit(?:y|ies)\b|"
            r"\bcomunidades? (?:eclesiales? )?de base\b|"
            r"\bcomunidades? eclesiais de base\b|\bCEBs?\b|"
            r"\bcomunidad(?:es)? eclesial(?:es)?\b",
            re.I,
        ),
        "both",
        "theology",
    ),
    ThemePattern(
        "oscar_romero",
        re.compile(r"\b(?:Oscar|Óscar)\s+Romero\b|\bSan Romero\b|\bSaint Romero\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "popular_piety",
        re.compile(
            r"\bpopular piety\b|\bpopular religion\b|\bpopular devotion\b|\bpiedad popular\b|"
            r"\bpiedade popular\b|\breligiosidad popular\b|\breligiosidade popular\b|"
            r"\bdevoci[oó]n popular\b|\bdevoc[aã]o popular\b|\bfolk Catholicism\b",
            re.I,
        ),
        "both",
        "theology",
    ),
    ThemePattern(
        "inculturation",
        re.compile(r"\binculturat\w*\b|\binculturaci[oó]n\b|\benculturaci[oó]n\b|\bincultura[cç][aã]o\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "sacrament",
        re.compile(r"\bsacrament(?:s|al)?\b|\bsacramento(?:s)?\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "eucharist",
        re.compile(r"\beucharist\w*\b|\bholy communion\b|\beucarist[ií]a\b|\bsanta comunión\b|\bsanta comunion\b|\bsanta comunh[aã]o\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "conversion_discipleship",
        re.compile(
            r"\bdiscipleship\b|\bdisciple(?:s)? of Christ\b|\bdiscipulado\b|\bconversi[oó]n\b|"
            r"\bconvers[aã]o\b|\bpersonal conversion\b|\bmetanoia\b",
            re.I,
        ),
        "both",
        "theology",
    ),
    ThemePattern(
        "synodality",
        re.compile(r"\bsynodality\b|\bsinodalidad\b|\bsinodalidade\b|\bsynodal church\b|\biglesia sinodal\b|\bigreja sinodal\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "laudato_si",
        re.compile(
            r"\blaudato\s+s[ií]['\u2019´`]?\b|"
            r"\bcuidado de la casa com[uú]n\b|"
            r"\bcuidado da casa comum\b|"
            r"\bcare for (?:our |the )?common home\b",
            re.I,
        ),
        "both",
        "theology",
    ),
    ThemePattern(
        "fratelli_tutti",
        re.compile(r"\bfratelli tutti\b|\btodos hermanos\b|\btodos somos hermanos\b|\btodos irm[aã]os\b|\bbrothers and sisters all\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "evangelii_nuntiandi",
        re.compile(r"\bevangelii nuntiandi\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "redemptoris_missio",
        re.compile(r"\bredemptoris missio\b|\bmission of the redeemer\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "rerum_novarum",
        re.compile(r"\brerum novarum\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "quadragesimo_anno",
        re.compile(r"\bquadragesimo anno\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "divini_redemptoris",
        re.compile(r"\bdivini redemptoris\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "mater_et_magistra",
        re.compile(r"\bmater et magistra\b|\bmother and teacher\b|\bmadre y maestra\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "pacem_in_terris",
        re.compile(r"\bpacem in terris\b|\bpeace on earth\b|\bpaz en la tierra\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "populorum_progressio",
        re.compile(r"\bpopulorum progressio\b|\bdevelopment of peoples\b|\bdesarrollo de los pueblos\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "octogesima_adveniens",
        re.compile(r"\boctogesima adveniens\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "laborem_exercens",
        re.compile(r"\blaborem exercens\b|\bon human work\b|\btrabajo humano\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "familiaris_consortio",
        re.compile(r"\bfamiliaris consortio\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "sollicitudo_rei_socialis",
        re.compile(r"\bsollicitudo rei socialis\b|\bon social concern\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "christifideles_laici",
        re.compile(r"\bchristifideles laici\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "centesimus_annus",
        re.compile(r"\bcentesimus annus\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "evangelium_vitae",
        re.compile(r"\bevangelium vitae\b|\bgospel of life\b|\bevangelio de la vida\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "fides_et_ratio",
        re.compile(r"\bfides et ratio\b|\bfaith and reason\b|\bfe y raz[oó]n\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "deus_caritas_est",
        re.compile(r"\bdeus caritas est\b|\bgod is love\b|\bdios es amor\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "spe_salvi",
        re.compile(r"\bspe salvi\b|\bsaved in hope\b|\bsalvados en esperanza\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "amoris_laetitia",
        re.compile(r"\bamoris laetitia\b|\bla alegr[ií]a del amor\b|\ba alegria do amor\b|\bjoy of love\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "lumen_fidei",
        re.compile(r"\blumen fidei\b|\bla luz de la fe\b|\blight of faith\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "caritas_in_veritate",
        re.compile(r"\bcaritas in veritate\b|\bcharity in truth\b|\bcaridad en la verdad\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "gaudete_et_exsultate",
        re.compile(r"\bgaudete et exsultate\b|\brejoice and be glad\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "christus_vivit",
        re.compile(r"\bchristus vivit\b|\bchrist is alive\b|\bcristo vive\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "querida_amazonia",
        re.compile(r"\bquerida amazon[ií]a\b|\bbeloved amazon\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "laudate_deum",
        re.compile(r"\blaudate deum\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "dilexit_nos",
        re.compile(r"\bdilexit nos\b|\bhe loved us\b", re.I),
        "both",
        "theology",
    ),
    ThemePattern(
        "magnifica_humanitas",
        re.compile(
            r"\bmagnifica humanitas\b|"
            r"\bmagnificent humanity\b|"
            r"\bmagn[ií]fica humanidad\b|"
            r"\bmagn[ií]fica humanidade\b|"
            r"\bsafeguarding the human person\b|"
            r"\bcustodia de la persona humana\b|"
            r"\bsalvaguarda da pessoa humana\b",
            re.I,
        ),
        "both",
        "theology",
    ),
)

# Subset for reporting — magisterial documents & papal teaching markers
PAPAL_DOCUMENT_LABELS = frozenset(
    {
        "evangelii_gaudium",
        "evangelii_nuntiandi",
        "redemptoris_missio",
        "laudato_si",
        "fratelli_tutti",
        "rerum_novarum",
        "quadragesimo_anno",
        "divini_redemptoris",
        "mater_et_magistra",
        "pacem_in_terris",
        "populorum_progressio",
        "octogesima_adveniens",
        "laborem_exercens",
        "familiaris_consortio",
        "sollicitudo_rei_socialis",
        "christifideles_laici",
        "centesimus_annus",
        "evangelium_vitae",
        "fides_et_ratio",
        "deus_caritas_est",
        "spe_salvi",
        "amoris_laetitia",
        "lumen_fidei",
        "caritas_in_veritate",
        "gaudete_et_exsultate",
        "christus_vivit",
        "querida_amazonia",
        "laudate_deum",
        "dilexit_nos",
        "magnifica_humanitas",
        "aparecida_celam",
        "catholic_social_teaching",
    }
)

REGION_PATTERNS: tuple[ThemePattern, ...] = (
    ThemePattern("mexico", re.compile(r"\bmexic\w*\b", re.I), "both", "cultural_context"),
    ThemePattern("brazil", re.compile(r"\bbrazil\b|\bbrasil\b", re.I), "both", "cultural_context"),
    ThemePattern("central_america", re.compile(r"\bcentral america\b|\bguatemala\b|\bhonduras\b|\bel salvador\b|\bnicaragua\b|\bcosta rica\b|\bpanama\b", re.I), "both", "cultural_context"),
    ThemePattern("caribbean", re.compile(r"\bcaribbean\b|\bcuba\b|\bpuerto rico\b|\bdominican republic\b|\bhaiti\b|\brepública dominicana\b", re.I), "both", "cultural_context"),
    ThemePattern("andes_south_cone", re.compile(r"\bchile\b|\bargentina\b|\bperu\b|\bperú\b|\bbolivia\b|\buruguay\b|\bparaguay\b|\becuador\b|\bcolombia\b|\bvenezuela\b", re.I), "both", "cultural_context"),
    ThemePattern("us_latino", re.compile(r"\blatino\b|\blatinx\b|\bhispanic\b|\btejan\w*\b|\bchican\w*\b|\blatin american\b|\bcomunidad hispana\b", re.I), "both", "cultural_context"),
    ThemePattern("canada", re.compile(r"\bcanada\b|\bcanadian\b|\bcanadá\b", re.I), "both", "cultural_context"),
    ThemePattern("united_states", re.compile(r"\bunited states\b|\bu\.s\.\b|\bamerican catholic\b", re.I), "both", "cultural_context"),
)

_PBCORE_DESC = re.compile(
    r"<pbcoreDescription[^>]*descriptionType=['\"]Episode['\"][^>]*>\s*(.*?)\s*</pbcoreDescription>",
    re.I | re.S,
)


def _strip_xml(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def iter_text_blobs(record: dict) -> Iterable[str]:
    for key in ("paragraph_text", "title", "description", "snippet", "show"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            yield value
    raw = record.get("api_raw")
    if not isinstance(raw, dict):
        return
    for sub in raw.values():
        if not isinstance(sub, dict):
            continue
        snippet = sub.get("snippet")
        if isinstance(snippet, dict):
            for key in ("title", "description"):
                value = snippet.get(key)
                if isinstance(value, str) and value.strip():
                    yield value
        xml = sub.get("xml")
        if isinstance(xml, str):
            for block in _PBCORE_DESC.findall(xml):
                cleaned = _strip_xml(block)
                if cleaned:
                    yield cleaned


def combined_text(record: dict) -> str:
    return " ".join(iter_text_blobs(record))


def infer_record_language(record: dict, source_hint: str = "") -> str:
    lang = str(record.get("language") or record.get("content_language") or "").lower()
    if lang.startswith("pt") or lang in ("portuguese", "português", "portugues"):
        return "portuguese"
    if lang.startswith("es") or lang == "spanish":
        return "spanish"
    if lang.startswith("en") or lang == "english":
        return "english"
    keyword = str(record.get("keyword_query") or record.get("keyword") or "").lower()
    if any(
        token in keyword
        for token in (
            "igreja",
            "evangelho",
            "evangelização",
            "evangelizacao",
            "missão",
            "missao",
            "libertação",
            "libertacao",
            "nossa senhora",
            "doutrina social da",
            "opção pelos pobres",
            "opcao pelos pobres",
        )
    ):
        return "portuguese"
    if any(
        token in keyword
        for token in (
            "católico",
            "catolico",
            "iglesia",
            "papa",
            "vaticano",
            "obispos",
            "evangeliz",
            "misión",
            "mision",
            "guadalupe",
            "liberación",
            "liberacion",
        )
    ):
        return "spanish"
    if source_hint.endswith("_es") or source_hint == "aapb_es":
        return "spanish"
    if source_hint.endswith("_pt"):
        return "portuguese"
    if source_hint.endswith("_en") or source_hint == "aapb_en":
        return "english"
    if source_hint == "americas_radio" or source_hint.startswith("americas_news"):
        blob = f" {combined_text(record)[:4000].lower()} "
        pt_hits = sum(
            1
            for w in (" não ", " uma ", " também ", " são ", " igreja ", " para os ", " do brasil ")
            if w in blob
        )
        es_hits = sum(
            1 for w in (" el ", " los ", " las ", " del ", " iglesia ", " también ")
            if w in blob
        )
        en_hits = sum(1 for w in (" the ", " and ", " of ", " to ", " for ") if w in blob)
        best = max(("portuguese", pt_hits), ("spanish", es_hits), ("english", en_hits), key=lambda x: x[1])
        if best[1] > 0 and best[1] >= max(pt_hits, es_hits, en_hits):
            if pt_hits > es_hits and pt_hits > en_hits:
                return "portuguese"
            if es_hits > en_hits:
                return "spanish"
    return "english"


def _applicable(pattern: ThemePattern, lang: str) -> bool:
    if pattern.language == "both":
        return True
    if pattern.language == "spanish" and lang in ("spanish", "portuguese"):
        return True
    if pattern.language == "portuguese" and lang == "portuguese":
        return True
    return pattern.language == lang


# Phrase-level naming (abstract claim check). Narrower than theme buckets:
# catholic_social_teaching also matches solidarity / common good / human dignity.
NAMING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("laudato_si_title", re.compile(r"\blaudato\s+s[ií]['’´`]?", re.I)),
    (
        "evangelii_gaudium_title",
        re.compile(
            r"\bevangelii\s+gaudium\b|\bjoy of the gospel\b|\balegr[ií]a del evangelio\b",
            re.I,
        ),
    ),
    ("doctrina_social", re.compile(r"\bdoctrina social(?: de la iglesia)?\b", re.I)),
    (
        "catholic_social_teaching_en",
        re.compile(r"\bcatholic social (?:teaching|doctrine)\b|\bsocial encyclical\b", re.I),
    ),
    ("opcion_preferencial", re.compile(r"\bopci[oó]n preferencial\b|\bpreferential option\b", re.I)),
    ("opcion_por_los_pobres", re.compile(r"\bopci[oó]n por los pobres\b|\boption for the poor\b", re.I)),
    ("evangelio_token", re.compile(r"\bevangelio\b", re.I)),
    ("mision_token", re.compile(r"\bmisi[oó]n\b", re.I)),
    ("gospel_token", re.compile(r"\bgospel\b", re.I)),
    ("mission_en_token", re.compile(r"\bmission\b", re.I)),
)


def match_naming_labels(text: str) -> set[str]:
    if not text.strip():
        return set()
    from common.text_normalize import fold_accents

    folded = fold_accents(text)
    hits: set[str] = set()
    for label, pat in NAMING_PATTERNS:
        if pat.search(text) or (folded != text and pat.search(folded)):
            hits.add(label)
    return hits


def match_theme_labels(text: str, lang: str, patterns: tuple[ThemePattern, ...] = THEME_PATTERNS) -> set[str]:
    if not text.strip():
        return set()
    from common.text_normalize import fold_accents

    # Also search accent-folded text so Sí/ñ variants still hit Latin patterns.
    folded = fold_accents(text)
    hits: set[str] = set()
    for theme in patterns:
        if not _applicable(theme, lang):
            continue
        if theme.pattern.search(text) or (folded != text and theme.pattern.search(folded)):
            hits.add(theme.label)
    return hits


def accents_from_themes(themes: set[str]) -> set[str]:
    accents: set[str] = set()
    for label in themes:
        accents |= set(THEME_TO_ACCENTS.get(label, ()))
    return accents


def match_theology_accents(text: str, lang: str) -> set[str]:
    return accents_from_themes(match_theme_labels(text, lang, THEME_PATTERNS))


def count_themes(text: str, lang: str = "english", patterns: tuple[ThemePattern, ...] = THEME_PATTERNS) -> Counter:
    return Counter(match_theme_labels(text, lang, patterns))


def theme_group(label: str) -> str:
    for theme in THEME_PATTERNS:
        if theme.label == label:
            return theme.group
    for region in REGION_PATTERNS:
        if region.label == label:
            return region.group
    return "other"


def core_mission_labels(lang: str) -> frozenset[str]:
    if lang == "spanish":
        return CORE_MISSION_ES
    if lang == "portuguese":
        return CORE_MISSION_PT
    return CORE_MISSION_EN
