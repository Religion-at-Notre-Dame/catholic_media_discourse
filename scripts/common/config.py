import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

# Inclusive collection window: 1 Jan 2015 through Q2 2026 (30 June).
CORPUS_START = date(2015, 1, 1)
CORPUS_END = date(2026, 6, 30)
CORPUS_START_YEAR = CORPUS_START.year
CORPUS_END_YEAR = CORPUS_END.year
CORPUS_START_YYYYMMDD = CORPUS_START.strftime("%Y%m%d")
CORPUS_END_YYYYMMDD = CORPUS_END.strftime("%Y%m%d")
CORPUS_END_MONTH = CORPUS_END.strftime("%Y%m")
CORPUS_END_ISO = CORPUS_END.isoformat()


def corpus_window_end(end_year: int) -> date:
    """Last inclusive day for an --end-year flag (Q2 cutoff in the corpus end year)."""
    if int(end_year) >= CORPUS_END.year:
        return CORPUS_END
    return date(int(end_year), 12, 31)


SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY") or YOUTUBE_API_KEY

# OpenRouter (TypeSafe Jev Decisions API — informal-learning judge)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_JEV_MODEL = os.getenv("OPENROUTER_JEV_MODEL", "typesafe/jev-1.13")
