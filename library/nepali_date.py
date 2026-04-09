"""
nepali_date.py
==============
Nepali (Bikram Sambat, BS) <-> English (Anno Domini, AD) date conversion
with millisecond-precision interval-based iterators.

Design principles:
  • Constants-out  : all lookup tables are module-level frozen constants
  • Collector style: list/dict/generator comprehensions favoured over imperative loops
  • Millisecond precision throughout (datetime + timedelta(milliseconds=…))
  • Every "Nepali" iterator runs on an English datetime spine internally
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from itertools import islice
import re
from typing import Any, Generator, Iterator, List, Optional, Tuple, Callable, \
    Dict, Iterable, Literal

# ---------------------------------------------------------------------------
# CONSTANTS — BS calendar data (1970 BS – 2100 BS)
# Each row = one BS year; each value = days in that BS month (1-12)
# Source: cross-validated against multiple public BS calendar tables.
# ---------------------------------------------------------------------------

# fmt: off
_BS_YEAR_DATA: dict[int, Tuple[int, ...]] = {
    1970: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    1971: (31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30),
    1972: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    1973: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    1974: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    1975: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    1976: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    1977: (30, 32, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    1978: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    1979: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    1980: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    1981: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    1982: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    1983: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    1984: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    1985: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    1986: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    1987: (31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    1988: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    1989: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    1990: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    1991: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    1992: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    1993: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    1994: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    1995: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    1996: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    1997: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    1998: (31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30),
    1999: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2000: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2001: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2002: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2003: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2004: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2005: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2006: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2007: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2008: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    2009: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2010: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2011: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2012: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2013: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2014: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2015: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2016: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2017: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2018: (31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2019: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2020: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2021: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2022: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2023: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2024: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2025: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2026: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2027: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2028: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2029: (31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30),
    2030: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2031: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2032: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2033: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2034: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2035: (30, 32, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    2036: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2037: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2038: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2039: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2040: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2041: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2042: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2043: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2044: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2045: (31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2046: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2047: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2048: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2049: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2050: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2051: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2052: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2053: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2054: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2055: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2056: (31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30),
    2057: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2058: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2059: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2060: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2061: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2062: (31, 31, 31, 32, 31, 31, 29, 30, 29, 30, 29, 31),
    2063: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2064: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2065: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2066: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    2067: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2068: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2069: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2070: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2071: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2072: (31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2073: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2074: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2075: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2076: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2077: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2078: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2079: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2080: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2081: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2082: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2083: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2084: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2085: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2086: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2087: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2088: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2089: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2090: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2091: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2092: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2093: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    2094: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2095: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2096: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2097: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2098: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2099: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2100: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
}
# fmt: on

# Anchor: BS 1970-01-01  ==  AD 1913-04-14
# Verified against official GoN calendar: BS 2081-01-01 = AD 2024-04-13
_ANCHOR_BS = (1970, 1, 1)
_ANCHOR_AD = datetime.date(1913, 4, 14)

# Supported BS range
TOTAL_MONTHS: int = 12
UNIT_MONTH: int = 1
_BS_MIN_YEAR: int = min(_BS_YEAR_DATA)
_BS_MAX_YEAR: int = max(_BS_YEAR_DATA)

# Nepali month names (index 1-12)
_BS_MONTH_NAMES: Tuple[str, ...] = (
    "",  # placeholder so index=1 → Baisakh
    "Baisakh",  # 1
    "Jestha",  # 2
    "Ashadh",  # 3
    "Shrawan",  # 4
    "Bhadra",  # 5
    "Ashwin",  # 6
    "Kartik",  # 7
    "Mangsir",  # 8
    "Poush",  # 9
    "Magh",  # 10
    "Falgun",  # 11
    "Chaitra",  # 12
)

# Nepali day names (Monday = 0, standard Python weekday())
_BS_WEEKDAY_NAMES: Tuple[str, ...] = (
    "Sombar",  # 0 Monday
    "Mangalbar",  # 1 Tuesday
    "Budhabar",  # 2 Wednesday
    "Bihibar",  # 3 Thursday
    "Sukrabar",  # 4 Friday
    "Sanibar",  # 5 Saturday
    "Aaitabar",  # 6 Sunday
)
# Regular expression for parsing relative date strings like "3 days ago"
_RELATIVE_PATTERN = re.compile(r'^(\d+)\s+(day|week)s?\s+(ago|back)$')

# ---------------------------------------------------------------------------
# DEVANAGARI CONSTANTS
# ---------------------------------------------------------------------------

# Digit mapping: ASCII digit → Devanagari digit (U+0966–U+096F)
# Used as a single translation table for the entire module.
_DEVANAGARI_DIGIT_MAP: dict[int, str] = {
    ord("0"): "०",  # U+0966
    ord("1"): "१",  # U+0967
    ord("2"): "२",  # U+0968
    ord("3"): "३",  # U+0969
    ord("4"): "४",  # U+096A
    ord("5"): "५",  # U+096B
    ord("6"): "६",  # U+096C
    ord("7"): "७",  # U+096D
    ord("8"): "८",  # U+096E
    ord("9"): "९",  # U+096F
}

# Reverse map: Devanagari digit → ASCII digit  (for parsing)
_DEVANAGARI_DIGIT_REVERSE: dict[str, str] = {
    v: str(k - ord("0")) for k, v in _DEVANAGARI_DIGIT_MAP.items()
}

# BS month names in Devanagari (index 1-12; index 0 is a placeholder)
_BS_MONTH_NAMES_DEVANAGARI: Tuple[str, ...] = (
    "",  # 0 — placeholder
    "बैशाख",  # 1  Baisakh
    "जेठ",  # 2  Jestha
    "असार",  # 3  Ashadh
    "साउन",  # 4  Shrawan
    "भदौ",  # 5  Bhadra
    "असोज",  # 6  Ashwin
    "कार्तिक",  # 7  Kartik
    "मंसिर",  # 8  Mangsir
    "पुस",  # 9  Poush
    "माघ",  # 10 Magh
    "फागुन",  # 11 Falgun
    "चैत",  # 12 Chaitra
)

# Weekday names in Devanagari (Monday = 0, matching Python weekday())
_BS_WEEKDAY_NAMES_DEVANAGARI: Tuple[str, ...] = (
    "सोमबार",  # 0 Monday    Sombar
    "मंगलबार",  # 1 Tuesday   Mangalbar
    "बुधबार",  # 2 Wednesday Budhabar
    "बिहीबार",  # 3 Thursday  Bihibar
    "शुक्रबार",  # 4 Friday    Sukrabar
    "शनिबार",  # 5 Saturday  Sanibar
    "आइतबार",  # 6 Sunday    Aaitabar
)

# Bidirectional month-name lookup tables (constants-out; built once at import)
# Latin → Devanagari
_MONTH_LATIN_TO_DEVANAGARI: dict[str, str] = {
    _BS_MONTH_NAMES[i]: _BS_MONTH_NAMES_DEVANAGARI[i]
    for i in range(1, 13)
}
# Devanagari → Latin
_MONTH_DEVANAGARI_TO_LATIN: dict[str, str] = {
    v: k for k, v in _MONTH_LATIN_TO_DEVANAGARI.items()
}

# Bidirectional weekday-name lookup tables
_WEEKDAY_LATIN_TO_DEVANAGARI: dict[str, str] = {
    _BS_WEEKDAY_NAMES[i]: _BS_WEEKDAY_NAMES_DEVANAGARI[i]
    for i in range(7)
}
_WEEKDAY_DEVANAGARI_TO_LATIN: dict[str, str] = {
    v: k for k, v in _WEEKDAY_LATIN_TO_DEVANAGARI.items()
}

# ---------------------------------------------------------------------------
# MONTH NAME VARIANT / ALIAS TABLE
# Maps every known romanised spelling (case-insensitive) and Devanagari form
# to the canonical month number (1–12).
#
# Sources: user-supplied table + common usage.
# ---------------------------------------------------------------------------
_BS_MONTH_ALIASES: dict[str, int] = {
    alias: month
    for month, aliases in [
        # ── Month 1 — Baisakh ──────────────────────────────────────────────────
        (1, (
            "baishakh", "baisakh", "baisakha", "vaisakh", "vaishakh", "beshakh",
            "baisak", "baisackh", "baisahk", "baishak", "baisakhh", "vaisahk",
            "vaisakha", "besakh", "beshakha", "बैशाख", "बैसाख", "बिशाख", "वैशाख"
        )),
        # ── Month 2 — Jestha ───────────────────────────────────────────────────
        (2, (
            "jestha", "jeth", "jaistha", "jaishtha", "jyeshtha", "jyaistha",
            "jesta", "jesth", "jetha", "jeshtha", "jaitha", "jeistha",
            "jesatha", "jjestha", "jyesta", "jyeth", "जेठ", "जेथ", "जेष्ठ"
        )),
        # ── Month 3 — Ashadh ───────────────────────────────────────────────────
        (3, (
            "ashadh", "asaar", "ashad", "ashar", "asadh", "aasaar", "aasadh",
            "ashadha", "asad", "asadha", "aashar", "ashada", "aaashar", "assar",
            "aasad", "ashardh", "असार", "आसार", "असाढ", "आषाढ"
        )),
        # ── Month 4 — Shrawan ──────────────────────────────────────────────────
        (4, (
            "shrawan", "sawan", "saun", "shrawn", "shraawan", "shravan",
            "srabon",
            "shawan", "sraban", "shrawaan", "sraawan", "shreawan", "shrawon",
            "shrabn", "sharwan", "sharawn", "shrwan", "shaun", "saawn",
            "sraavn", "shravana", "साउन", "सावन", "श्रावण", "शावन"
        )),
        # ── Month 5 — Bhadra ───────────────────────────────────────────────────
        (5, (
            "bhadra", "bhadau", "bhadon", "bhaadra", "bhadro", "bhadara",
            "bhadaa", "bhadou", "bhadaau", "bhadoo", "bhadaw", "bhadraa",
            "bhardo", "bhadar", "bhadrapada", "भदौ", "भाद्र", "भदो", "भाद्रपद"
        )),
        # ── Month 6 — Ashwin ───────────────────────────────────────────────────
        (6, (
            "ashwin", "asoj", "aswin", "ashvin", "aashwin", "aswoj", "ashwoj",
            "ashween", "ashveen", "aswinn", "asshwin", "assoj", "azoj",
            "asswin", "ashvina", "असोज", "आसोज", "अश्विन", "आश्विन"
        )),
        # ── Month 7 — Kartik ───────────────────────────────────────────────────
        (7, (
            "kartik", "kartika", "katik", "karthik", "kartick", "karttik",
            "kartikk", "kaartik", "karteak", "kartikha", "karthika", "katika",
            "kattik", "kartic", "karteek", "कात्तिक", "कार्तिक", "कर्तिक",
            "कातिक"
        )),
        # ── Month 8 — Mangsir ──────────────────────────────────────────────────
        (8, (
            "mangsir", "margashir", "mansir", "mangshir", "margashirsha",
            "mangseer", "manshir", "mangsheer", "mangasir", "mangsirr",
            "mangsire", "manngsir", "mangsiir", "margsir", "margasir",
            "मंसिर", "मंगसिर", "मार्गशीर्ष", "मनसिर"
        )),
        # ── Month 9 — Poush ────────────────────────────────────────────────────
        (9, (
            "poush", "push", "paush", "pus", "poos", "pаush", "pouush", "poosh",
            "phouush", "posh", "paaus", "pauush", "pausha", "pusha",
            "पुष", "पुस", "पौष", "पूस"
        )),
        # ── Month 10 — Magh ────────────────────────────────────────────────────
        (10, (
            "magh", "maagh", "maag", "mag", "magg", "maagha", "magha",
            "maakh", "maaghh", "माघ"
        )),
        # ── Month 11 — Falgun ──────────────────────────────────────────────────
        (11, (
            "falgun", "phagun", "phalguna", "fagun", "phalgun", "phaagun",
            "falgan", "phaalgun", "falgunn", "falgon", "falgen", "phaagoon",
            "falugn", "phalugna", "phaalguna", "फाल्गुण", "फागुन", "फाल्गुन",
            "फागून"
        )),
        # ── Month 12 — Chaitra ─────────────────────────────────────────────────
        (12, (
            "chaitra", "chait", "chaitta", "chaita", "chaiter", "chaitraa",
            "chaitrra", "chaeta", "chyaitra", "chaaitr", "chaetra", "chaeit",
            "चैत्र", "चैत", "चैत्रा", "चैत्"
        ))
    ]
    for alias in aliases
}


# ---------------------------------------------------------------------------
# NUMERAL CONVERSION HELPERS
# ---------------------------------------------------------------------------

def to_devanagari_numeral(value: int | str) -> str:
    """
    Convert an integer (or digit string) to Devanagari numerals.
    to_devanagari_numeral(2081)
    '२०८१'
    to_devanagari_numeral("15")
    '१५'
    """
    return str(value).translate(_DEVANAGARI_DIGIT_MAP)


def from_devanagari_numeral(deva_str: str) -> int:
    """
    Convert a Devanagari numeral string back to a Python int.
    from_devanagari_numeral('२०८१')
    2081
    """
    ascii_digits = "".join(
        _DEVANAGARI_DIGIT_REVERSE.get(ch, ch) for ch in deva_str)
    return int(ascii_digits)


def normalize_month_name(month: "int | str") -> int:
    """
    Resolve a BS month to its canonical number (1-12).

    Accepts:
    - An integer 1-12 directly.
    - Any romanised spelling / variant (case-insensitive), e.g.
      'Baisakh', 'baisakha', 'Baishakh', 'SHRAWAN', 'Saun', 'Asoj', …
    - A Devanagari script name, e.g. 'बैशाख', 'असोज', …

    Returns
    -------
    int  — month number 1-12

    Raises
    ------
    ValueError  if the input cannot be matched.

    Examples
    --------
    normalize_month_name('Baisakh')>>> 1 normalize_month_name('saun') >>> 4
    normalize_month_name('बैशाख') >>> 1  normalize_month_name(6) >>> 6
    """
    if isinstance(month, int):
        if 1 <= month <= 12:
            return month
        raise ValueError(f"Month number must be 1-12, got {month}.")

    # Try Devanagari first (exact key lookup), then case-folded Latin lookup
    num = _BS_MONTH_ALIASES.get(month)
    if num is not None:
        return num
    num = _BS_MONTH_ALIASES.get(month.strip().lower())
    if num is not None:
        return num
    raise ValueError(
        f"Unrecognised BS month name or variant: '{month}'.\n"
        f"Accepted forms include: Baisakh/Baishakh, Jestha/Jeth, "
        f"Ashadh/Asar/Ashad, Shrawan/Saun, Bhadra/Bhadau, "
        f"Ashwin/Asoj, Kartik, Mangsir, Poush/Push, Magh, "
        f"Falgun/Phagun, Chaitra/Chait — and their Devanagari equivalents."
    )


def month_name_to_devanagari(latin_name: str) -> str:
    """Return the Devanagari month name for a given Latin (romanised) name."""
    result = _MONTH_LATIN_TO_DEVANAGARI.get(latin_name)
    if result is None:
        raise KeyError(
            f"Unknown BS month name: '{latin_name}'. "
            f"Valid names: {list(_MONTH_LATIN_TO_DEVANAGARI)}"
        )
    return result


def month_name_from_devanagari(deva_name: str) -> str:
    """Return the Latin month name for a given Devanagari BS month name."""
    result = _MONTH_DEVANAGARI_TO_LATIN.get(deva_name)
    if result is None:
        raise KeyError(
            f"Unknown Devanagari month name: '{deva_name}'. "
            f"Valid names: {list(_MONTH_DEVANAGARI_TO_LATIN)}"
        )
    return result


def weekday_name_to_devanagari(latin_name: str) -> str:
    """Return the Devanagari weekday name for a given Latin name."""
    result = _WEEKDAY_LATIN_TO_DEVANAGARI.get(latin_name)
    if result is None:
        raise KeyError(f"Unknown weekday name: '{latin_name}'.")
    return result


def weekday_name_from_devanagari(deva_name: str) -> str:
    """Return the Latin weekday name for a given Devanagari weekday name."""
    result = _WEEKDAY_DEVANAGARI_TO_LATIN.get(deva_name)
    if result is None:
        raise KeyError(f"Unknown Devanagari weekday name: '{deva_name}'.")
    return result


# ---------------------------------------------------------------------------
# GREGORIAN (AD) MONTH ALIAS TABLE
# Maps full English month names, 3-letter abbreviations, and numeric strings
# to Gregorian month numbers (1-12). Lookup is case-insensitive.
# ---------------------------------------------------------------------------
_AD_MONTH_ALIASES: dict[str, int] = {
    alias: month
    for month, aliases in [
        # January
        (1, (
            "january", "jan", "1", "januray", "januery", "janaury", "janury",
            "janwari", "janwary"
        )),
        # February
        (2, (
            "february", "feb", "2", "febuary", "feburary", "februray",
            "febrary", "febrari"
        )),
        # March
        (3, (
            "march", "mar", "3", "marck", "mach", "marsch"
        )),
        # April
        (4, (
            "april", "apr", "4", "apirl", "aprl", "aprill", "apryl"
        )),
        # May
        (5, (
            "may", "5", "maay", "maye", "mey"
        )),
        # June
        (6, (
            "june", "jun", "6", "juune", "juen", "joon"
        )),
        # July
        (7, (
            "july", "jul", "7", "juuly", "jully", "julye", "julai"
        )),
        # August
        (8, (
            "august", "aug", "8", "agast", "agust", "augist", "augest",
            "augustt"
        )),
        # September
        (9, (
            "september", "sep", "sept", "9", "setember", "septmber",
            "septembar", "septembe"
        )),
        # October
        (10, (
            "october", "oct", "10", "octber", "ocober", "octobar", "octobr"
        )),
        # November
        (11, (
            "november", "nov", "11", "novmber", "noveber", "novembar", "novembr"
        )),
        # December
        (12, (
            "december", "dec", "12", "decmber", "deceber", "decembar", "decembr"
        ))
    ]
    for alias in aliases
}


def normalize_ad_month(month: "int | str") -> int:
    """
    Resolve a Gregorian (AD) month to a number 1-12.

    Accepts:
    - An integer 1-12 directly.
    - Full English name  : 'January' … 'December'  (case-insensitive)
    - 3-letter abbreviation: 'Jan', 'APR', 'dec', …
    - Numeric string     : '1' … '12'

    Examples
    --------
    normalize_ad_month('April') >>>  4, normalize_ad_month('apr') >>> 4
    normalize_ad_month('APR') >>> 4, normalize_ad_month(4) >>> 4
    """
    if isinstance(month, int):
        if 1 <= month <= 12:
            return month
        raise ValueError(f"AD month number must be 1-12, got {month}.")
    num = _AD_MONTH_ALIASES.get(month.strip().lower())
    if num is None:
        raise ValueError(
            f"Unrecognised AD month name: '{month}'. "
            f"Use a full name (January…December), 3-letter abbreviation "
            f"(Jan…Dec), or integer 1-12."
        )
    return num


# ---------------------------------------------------------------------------
# WEEKDAY ALIAS TABLE  (English + Nepali names and abbreviations)
# Maps to Python weekday() integers: Monday=0 … Sunday=6
# ---------------------------------------------------------------------------
_WEEKDAY_ALIASES: dict[str, int] = {
    alias: weekday
    for weekday, aliases in [
        # Monday
        (0, (
            "monday", "mondey", "moonday", "moday", "munday", "manday", "mon",
            "mo", "sombar", "somabar", "soma", "som", "sombara", "sombarr",
            "somabaar", "somabarr", "somabara", "सोमबार", "सोमवार", "सोम"
        )),
        # Tuesday
        (1, (
            "tuesday", "tuseday", "tusday", "teusday", "thuseday", "tue",
            "tues", "tu", "mangalbar", "mangal", "mangala", "mangalbaar",
            "mangalbarr", "mangalbara", "mangelbar", "mangalvaar", "मंगलबार",
            "मंगलवार", "मंगल", "मङ्गलबार", "मङ्गल"
        )),
        # Wednesday
        (2, (
            "wednesday", "wendsday", "wensday", "wednseday", "wednsday", "wed",
            "we", "budhabar", "budha", "budh", "budhvar", "budhabaar",
            "budhabarr", "budhab", "budhaabar", "budhavar", "budaabar",
            "बुधबार", "बुधवार", "बुध", "बुद्धबार"
        )),
        # Thursday
        (3, (
            "thursday", "thurdsay", "thursay", "thurday", "thirsday", "thusday",
            "thu", "thur", "thurs", "th", "bihibar", "bihivar", "brihaspatibar",
            "gurubar", "guruvar", "bihibarr", "bihibaar", "bihaabar", "bihavar",
            "brihaspati", "बिहीबार", "बिहिबार", "बिहीवार", "बृहस्पतिबार",
            "गुरुवार", "गुरुबार", "बिहि", "बिही"
        )),
        # Friday
        (4, (
            "friday", "firday", "fryday", "friay", "fri", "fr", "sukrabar",
            "sukra", "shukra", "shukrabar", "sukravar", "sukrabaar",
            "sukrabarr", "shukravar", "shukrabaar", "sukrbar", "शुक्रबार",
            "शुक्रवार", "शुक्र", "शुक्राबार", "सुक्रबार"
        )),
        # Saturday
        (5, (
            "saturday", "saterday", "saturdy", "satarday", "sat", "sa",
            "sanibar", "shani", "shanibar", "sanibaar", "sanibarr", "sanibara",
            "shanibaar", "shanibara", "shaanibar", "शनिबार", "शनिवार", "शनि",
            "शनीबार", "सनिबार", "शानिबार"
        )),
        # Sunday
        (6, (
            "sunday", "sunady", "sonday", "sunnday", "sun", "su", "aaitabar",
            "aitabaar", "aaita", "aita", "aitabar", "rabibar", "ravivar",
            "ravi", "itvar", "aaitabarr", "aaitabara", "aitabarr", "aytabar",
            "rabibaar", "rabibarr", "rabibara", "आइतबार", "आइतवार", "आइत",
            "रविबार", "रबिबार", "इतवार", "इतबार", "रबिवार"
        ))
    ]
    for alias in aliases
}


def normalize_weekday(day: "int | str") -> int:
    """
    Resolve a weekday to a Python weekday() integer (Monday=0 … Sunday=6).

    Accepts:
    - An integer 0-6 directly.
    - English full name  : 'Monday' … 'Sunday'  (case-insensitive)
    - English abbreviation: 'Mon', 'MON', 'SUN', 'Fri', …
    - Nepali romanised   : 'Sombar', 'Aaitabar', …
    - Nepali Devanagari  : 'सोमबार', 'आइतबार', …

    Examples
    --------
    normalize_weekday('Sun') >>> 6,  normalize_weekday('sunday') >>> 6,
    normalize_weekday('SUN') >>>  6, normalize_weekday('Aaitabar') >>> 6
    normalize_weekday(6) >>> 6
    """
    if isinstance(day, int):
        if 0 <= day <= 6:
            return day
        raise ValueError(f"Weekday integer must be 0-6 (Mon-Sun), got {day}.")
    # Try Devanagari (exact), then case-folded Latin lookup
    num = _WEEKDAY_ALIASES.get(day)
    if num is not None:
        return num
    num = _WEEKDAY_ALIASES.get(day.strip().lower())
    if num is not None:
        return num
    raise ValueError(
        f"Unrecognised weekday: '{day}'. "
        f"Use English (Monday/Mon/MON … Sunday/Sun/SUN), "
        f"Nepali romanised (Sombar … Aaitabar), "
        f"or Devanagari (सोमबार … आइतबार)."
    )


# ---------------------------------------------------------------------------
# PURE HELPERS (stateless functions)
# ---------------------------------------------------------------------------

def _days_in_bs_month(year: int, month: int) -> int:
    """Return number of days in a given BS year/month."""
    if year not in _BS_YEAR_DATA:
        raise ValueError(
            f"BS year {year} not in supported range "
            f"[{_BS_MIN_YEAR}, {_BS_MAX_YEAR}]."
        )
    return _BS_YEAR_DATA[year][month - 1]


def _total_bs_days_from_anchor(year: int, month: int, day: int) -> int:
    """Count calendar days from BS anchor (1970-01-01) to given BS date."""
    if year < _BS_MIN_YEAR or year > _BS_MAX_YEAR:
        raise ValueError(
            f"BS year {year} out of range [{_BS_MIN_YEAR}, {_BS_MAX_YEAR}]."
        )
    # days from anchor-year start to target year start
    year_days = sum(
        sum(_BS_YEAR_DATA[year_idx]) for year_idx in range(_ANCHOR_BS[0], year)
    )
    # days within target year up to target month
    month_days = sum(
        _BS_YEAR_DATA[year][month_idx] for month_idx in range(month - 1)
        # months are 0-indexed in tuple
    )
    return year_days + month_days + (day - 1)


# ---------------------------------------------------------------------------
# CORE CONVERSION FUNCTIONS
# ---------------------------------------------------------------------------

def bs_to_ad(year: int, month: int | str, day: int) -> datetime.date:
    """
    Convert a Bikram Sambat (BS) date to Gregorian (AD) date.

    Parameters
    ----------
    year  : BS year  (e.g. 2081)
    month : BS month — either an integer (1 = Baisakh … 12 = Chaitra)
            or any recognised month name / variant string, e.g.
            'Baisakh', 'Baishakh', 'Saun', 'Shrawan', 'Asoj', 'Ashwin',
            'Phagun', 'Chaitra', 'चैत्र', 'बैशाख', …
    day   : BS day

    Returns
    -------
    datetime.date
    """
    month_num = normalize_month_name(month)
    total_days = _total_bs_days_from_anchor(year, month_num, day)
    return _ANCHOR_AD + datetime.timedelta(days=total_days)


def ad_to_bs(
        date: datetime.date | None = None,
        year: int | None = None,
        month: int | str | None = None,
        day: int | None = None,
) -> Tuple[int, int, int]:
    """
    Convert a Gregorian (AD) date to Bikram Sambat (BS) date.

    Can be called in two ways:

    1. Pass a ``datetime.date`` (or ``datetime.datetime``) object::
           ad_to_bs(datetime.date(2024, 4, 13))

    2. Pass year / month / day as keyword (or positional) arguments.
       ``month`` accepts an integer OR any English month name / abbreviation::

           ad_to_bs(year=2024, month=4,       day=13)
           ad_to_bs(year=2024, month='April', day=13)
           ad_to_bs(year=2024, month='Apr',   day=13)
           ad_to_bs(year=2024, month='APR',   day=13)

    Parameters
    ----------
    date  : datetime.date | datetime.datetime, optional
    year  : int, optional
    month : int | str, optional  — integer 1-12 or English month name/abbrev
    day   : int, optional

    Returns
    -------
    (bs_year, bs_month, bs_day)
    """
    if date is None and year is not None:
        # called as ad_to_bs(year=…, month=…, day=…)
        if month is None or day is None:
            raise ValueError(
                "When passing year/month/day, all three must be provided."
            )
        month_num = normalize_ad_month(month)
        date = datetime.date(year, month_num, day)
    elif date is None:
        raise ValueError(
            "Provide either a date object or year/month/day keyword arguments."
        )
    if hasattr(date, "date"):  # accept datetime objects too
        date = date.date()
    delta_days: int = (date - _ANCHOR_AD).days
    if delta_days < 0:
        raise ValueError(
            f"AD date {date} is before the supported anchor {_ANCHOR_AD}.")

    # Walk forward through BS years/months consuming delta_days
    # Collector-style: build a flat sequence of (year, month, days_in_month)
    # then iterate — avoids nested imperative loops.
    bs_year = _ANCHOR_BS[0]
    bs_month = _ANCHOR_BS[1]
    bs_day = _ANCHOR_BS[2] - 1  # will be incremented

    remaining = delta_days

    # consume whole years
    while True:
        if bs_year > _BS_MAX_YEAR:
            raise ValueError(f"AD date {date} exceeds supported BS range.")
        days_in_year = sum(_BS_YEAR_DATA[bs_year])
        if remaining < days_in_year:
            break
        remaining -= days_in_year
        bs_year += 1

    # consume whole months
    while True:
        dim = _days_in_bs_month(bs_year, bs_month)
        if remaining < dim:
            break
        remaining -= dim
        bs_month += 1

    bs_day = remaining + 1
    return (bs_year, bs_month, bs_day)


# ---------------------------------------------------------------------------
# PARTIAL DATE RANGE CONVERSIONS
# ---------------------------------------------------------------------------
import calendar as _calendar


@dataclass(frozen=True)
class DateRange:
    """
    A calendar range stored as a pair of AD dates (start inclusive, end inclusive).

    Provides formatted views in both AD and BS scripts.

    Attributes
    ----------
    start_ad : datetime.date   — range start (Gregorian)
    end_ad   : datetime.date   — range end   (Gregorian)
    label    : str             — human-readable description of the source period
    """
    start_ad: datetime.date
    end_ad: datetime.date
    label: str = ""

    # -- BS views -----------------------------------------------------------

    @property
    def start_bs(self) -> Tuple[int, int, int]:
        """Start date as (bs_year, bs_month, bs_day)."""
        return ad_to_bs(self.start_ad)

    @property
    def end_bs(self) -> Tuple[int, int, int]:
        """End date as (bs_year, bs_month, bs_day)."""
        return ad_to_bs(self.end_ad)

    # -- Formatters ---------------------------------------------------------

    def format_ad(self, fmt: str = "%B %d, %Y") -> str:
        """e.g. 'April 14, 2025 to April 13, 2026'"""
        return f"{self.start_ad.strftime(fmt)} to {self.end_ad.strftime(fmt)}"

    def format_bs(self) -> str:
        """e.g. 'Baisakh 01, 2082 BS to Chaitra 30, 2082 BS'"""
        sy, sm, sd = self.start_bs
        ey, em, ed = self.end_bs
        return (f"{_BS_MONTH_NAMES[sm]} {sd:02d}, {sy} BS"
                f" to {_BS_MONTH_NAMES[em]} {ed:02d}, {ey} BS")

    def format_bs_devanagari(self) -> str:
        """Same as format_bs but in Devanagari script."""
        sy, sm, sd = self.start_bs
        ey, em, ed = self.end_bs
        deva = to_devanagari_numeral
        return (
            f"{_BS_MONTH_NAMES_DEVANAGARI[sm]} {deva(f'{sd:02d}')}, {deva(str(sy))} BS"
            f" to {_BS_MONTH_NAMES_DEVANAGARI[em]} {deva(f'{ed:02d}')}, {deva(str(ey))} BS")

    def __str__(self) -> str:
        parts = [f"  AD : {self.format_ad()}",
                 f"  BS : {self.format_bs()}"]
        if self.label:
            parts.insert(0, f"  [{self.label}]")
        return "\n".join(parts)

    # -- Range Algebra ------------------------------------------------------

    def contains_date(self, date_obj: "Any") -> bool:
        """Check if a date (datetime.date, datetime.datetime, or NepaliDateTime) falls in this range."""
        value = getattr(date_obj, "dt", date_obj)
        date_to_check = value.date() if hasattr(value, "date") else value
        return self.start_ad <= date_to_check <= self.end_ad

    def overlaps(self, other: DateRange) -> bool:
        """Check if this period overlaps with another DateRange."""
        return max(self.start_ad, other.start_ad) <= min(self.end_ad,
                                                         other.end_ad)

    def intersection(self, other: DateRange) -> DateRange | None:
        """Return the intersecting DateRange, or None if disjoint."""
        start = max(self.start_ad, other.start_ad)
        end = min(self.end_ad, other.end_ad)
        return DateRange(
            start, end, label=f"({self.label} ∩ {other.label})"
        ) if start <= end else None


# -- Helper: current BS year / AD year ------------------------------------

def current_bs_year() -> int:
    """Return the BS year for today's date."""
    return ad_to_bs(datetime.date.today())[0]


def current_bs_month() -> int:
    """Return the BS month number for today's date."""
    return ad_to_bs(datetime.date.today())[1]


# -- Internal helpers for range building ----------------------------------

def _bs_month_start_ad(bs_year: int, bs_month: int) -> datetime.date:
    return bs_to_ad(bs_year, bs_month, 1)


def _bs_month_end_ad(bs_year: int, bs_month: int) -> datetime.date:
    return bs_to_ad(bs_year, bs_month, _days_in_bs_month(bs_year, bs_month))


# =========================================================================
# YEAR RANGE FUNCTIONS
# =========================================================================

def ad_year_to_bs_range(ad_year: int) -> DateRange:
    """
    Convert an AD year to the equivalent BS date range.
    Example
    -------
    r = ad_year_to_bs_range(2025)
    print(r)
    # AD : January 01, 2025 to December 31, 2025
    # BS : Poush 17, 2081 BS to Poush 16, 2082 BS
    """
    start_ad = datetime.date(ad_year, 1, 1)
    end_ad = datetime.date(ad_year, 12, 31)
    return DateRange(start_ad, end_ad, label=f"AD Year {ad_year}")


def bs_year_to_ad_range(bs_year: int) -> DateRange:
    """
    Convert a BS year to the equivalent AD date range.

    The range spans from Baisakh 1 of *bs_year* to the last day of Chaitra
    of *bs_year* (inclusive on both ends).

    Example
    -------
    r = bs_year_to_ad_range(2082)
    print(r)
    # [BS Year 2082]
    # AD : April 14, 2025 to April 13, 2026
    # BS : Baisakh 01, 2082 BS to Chaitra 31, 2082 BS
    """
    start_ad = _bs_month_start_ad(bs_year, 1)
    end_ad = _bs_month_end_ad(bs_year, 12)
    return DateRange(start_ad, end_ad, label=f"BS Year {bs_year}")


# =========================================================================
# MONTH RANGE FUNCTIONS
# =========================================================================

def bs_month_to_ad_range(
        month: int | str,
        bs_year: int | None = None,
) -> DateRange:
    """
    Convert a BS month (optionally with year) to an AD date range.

    Parameters
    ----------
    month   : int or str — BS month number (1-12) or any recognised name/variant
    bs_year : int, optional — defaults to the current BS year

    Example
    -------
    r = bs_month_to_ad_range('Shrawan')   # current BS year
    print(r)
    # BS : Shrawan 01, 2082 BS to Shrawan 31, 2082 BS
    # AD : July 17, 2025 to August 16, 2025
    """
    bs_year = bs_year if bs_year is not None else current_bs_year()
    month_num = normalize_month_name(month)
    start_ad = _bs_month_start_ad(bs_year, month_num)
    end_ad = _bs_month_end_ad(bs_year, month_num)
    return DateRange(
        start_ad, end_ad, label=f"BS {_BS_MONTH_NAMES[month_num]} {bs_year}"
    )


def ad_month_to_bs_range(
        month: int | str,
        ad_year: int | None = None,
) -> DateRange:
    """
    Convert an AD month (optionally with year) to a BS date range.

    Parameters
    ----------
    month   : int or str — AD month number (1-12), full name, or 3-letter abbrev
    ad_year : int, optional — defaults to the current AD year

    Example
    -------
    r = ad_month_to_bs_range('January')   # current AD year
    print(r)
    # AD : January 01, 2026 to January 31, 2026
    # BS : Poush 17, 2082 BS to Magh 17, 2082 BS
    """
    ad_year = ad_year if ad_year is not None else datetime.date.today().year
    month_num = normalize_ad_month(month)
    last_day = _calendar.monthrange(ad_year, month_num)[1]
    start_ad = datetime.date(ad_year, month_num, 1)
    end_ad = datetime.date(ad_year, month_num, last_day)
    month_name = datetime.date(ad_year, month_num, 1).strftime("%B")
    return DateRange(start_ad, end_ad, label=f"AD {month_name} {ad_year}")


# =========================================================================
# QUARTER RANGE FUNCTIONS   (Q1=1, Q2=2, Q3=3, Q4=4)
# BS  quarters: Q1=Baisakh-Ashadh, Q2=Shrawan-Ashwin,
#               Q3=Kartik-Poush,   Q4=Magh-Chaitra
# AD  quarters: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
# =========================================================================

_BS_QUARTER_MONTHS: dict[int, Tuple[int, int]] = {
    1: (1, 3),  # Baisakh – Ashadh
    2: (4, 6),  # Shrawan – Ashwin
    3: (7, 9),  # Kartik  – Poush
    4: (10, 12),  # Magh    – Chaitra
}
_AD_QUARTER_MONTHS: dict[int, Tuple[int, int]] = {
    1: (1, 3),  # Jan – Mar
    2: (4, 6),  # Apr – Jun
    3: (7, 9),  # Jul – Sep
    4: (10, 12),  # Oct – Dec
}


def bs_quarter_to_ad_range(
        quarter: int,
        bs_year: int | None = None,
) -> DateRange:
    """
    Convert a BS fiscal quarter to an AD date range.

    Parameters
    ----------
    quarter : int  — 1, 2, 3, or 4
    bs_year : int, optional — defaults to the current BS year

    Example
    -------
    r = bs_quarter_to_ad_range(1, 2082)
    print(r)
    # [BS Q1 2082: Baisakh–Ashadh]
    # AD : April 14, 2025 to July 16, 2025
    # BS : Baisakh 01, 2082 BS to Ashadh 31, 2082 BS
    """
    if quarter not in _BS_QUARTER_MONTHS:
        raise ValueError(f"BS quarter must be 1-4, got {quarter}.")
    bs_year = bs_year if bs_year is not None else current_bs_year()
    m_start, m_end = _BS_QUARTER_MONTHS[quarter]
    start_ad = _bs_month_start_ad(bs_year, m_start)
    end_ad = _bs_month_end_ad(bs_year, m_end)
    q_names = f"{_BS_MONTH_NAMES[m_start]}–{_BS_MONTH_NAMES[m_end]}"
    return DateRange(
        start_ad, end_ad, label=f"BS Q{quarter} {bs_year}: {q_names}"
    )


def ad_quarter_to_bs_range(
        quarter: int,
        ad_year: int | None = None,
) -> DateRange:
    """
    Convert an AD fiscal quarter to a BS date range.

    Parameters
    ----------
    quarter : int  — 1, 2, 3, or 4
    ad_year : int, optional — defaults to the current AD year

    Example
    -------
    r = ad_quarter_to_bs_range(2, 2025)
    print(r)
    # [AD Q2 2025: Apr–Jun]
    # AD : April 01, 2025 to June 30, 2025
    # BS : Chaitra 19, 2081 BS to Ashadh 16, 2082 BS
    """
    if quarter not in _AD_QUARTER_MONTHS:
        raise ValueError(f"AD quarter must be 1-4, got {quarter}.")
    ad_year = ad_year if ad_year is not None else datetime.date.today().year
    m_start, m_end = _AD_QUARTER_MONTHS[quarter]
    start_ad = datetime.date(ad_year, m_start, 1)
    end_ad = datetime.date(ad_year, m_end,
                           _calendar.monthrange(ad_year, m_end)[1])
    s_name = datetime.date(ad_year, m_start, 1).strftime("%b")
    e_name = datetime.date(ad_year, m_end, 1).strftime("%b")
    return DateRange(
        start_ad, end_ad, label=f"AD Q{quarter} {ad_year}: {s_name}–{e_name}"
    )


# =========================================================================
# HALF-YEAR RANGE FUNCTIONS  (H1=1 or "first", H2=2 or "second")
# BS  halves: H1=months 1-6, H2=months 7-12
# AD  halves: H1=months 1-6, H2=months 7-12
# =========================================================================

_BS_HALF_MONTHS: dict[int, Tuple[int, int]] = {
    1: (1, 6),  # Baisakh – Ashwin
    2: (7, 12),  # Kartik  – Chaitra
}
_AD_HALF_MONTHS: dict[int, Tuple[int, int]] = {
    1: (1, 6),  # Jan – Jun
    2: (7, 12),  # Jul – Dec
}


def _resolve_half(half: int | str) -> int:
    """Normalise half-year designator to 1 or 2."""
    if isinstance(half, int):
        if half in (1, 2):
            return half
    s = str(half).strip().lower()
    if s in ("1", "first", "h1", "1st", "one"):
        return 1
    if s in ("2", "second", "h2", "2nd", "two"):
        return 2
    raise ValueError(
        f"Half-year must be 1 or 2 (or 'first'/'second'), got '{half}'."
    )


def bs_half_to_ad_range(
        half: int | str,
        bs_year: int | None = None,
) -> DateRange:
    """
    Convert a BS half-year to an AD date range.

    Parameters
    ----------
    half    : int or str — 1/'first'/'H1' or 2/'second'/'H2'
    bs_year : int, optional — defaults to the current BS year

    Example
    -------
    r = bs_half_to_ad_range(1, 2082)
    print(r)
    # [BS H1 2082: Baisakh–Ashwin]
    # AD : April 14, 2025 to October 16, 2025
    # BS : Baisakh 01, 2082 BS to Ashwin 29, 2082 BS
    """
    h = _resolve_half(half)
    bs_year = bs_year if bs_year is not None else current_bs_year()
    m_start, m_end = _BS_HALF_MONTHS[h]
    start_ad = _bs_month_start_ad(bs_year, m_start)
    end_ad = _bs_month_end_ad(bs_year, m_end)
    h_names = f"{_BS_MONTH_NAMES[m_start]}–{_BS_MONTH_NAMES[m_end]}"
    return DateRange(start_ad, end_ad, label=f"BS H{h} {bs_year}: {h_names}")


def ad_half_to_bs_range(
        half: int | str,
        ad_year: int | None = None,
) -> DateRange:
    """
    Convert an AD half-year to a BS date range.

    Parameters
    ----------
    half    : int or str — 1/'first'/'H1' or 2/'second'/'H2'
    ad_year : int, optional — defaults to the current AD year

    Example
    -------
    r = ad_half_to_bs_range(1, 2025)
    print(r)
    # [AD H1 2025: Jan–Jun]
    # AD : January 01, 2025 to June 30, 2025
    # BS : Poush 17, 2081 BS to Ashadh 16, 2082 BS
    """
    h = _resolve_half(half)
    ad_year = ad_year if ad_year is not None else datetime.date.today().year
    m_start, m_end = _AD_HALF_MONTHS[h]
    start_ad = datetime.date(ad_year, m_start, 1)
    end_ad = datetime.date(ad_year, m_end,
                           _calendar.monthrange(ad_year, m_end)[1])
    s_name = datetime.date(ad_year, m_start, 1).strftime("%b")
    e_name = datetime.date(ad_year, m_end, 1).strftime("%b")
    return DateRange(start_ad, end_ad,
                     label=f"AD H{h} {ad_year}: {s_name}–{e_name}")


# ---------------------------------------------------------------------------
# FIELD / GRANULARITY STRING CONSTANTS
# ---------------------------------------------------------------------------
# All string keys used for field lookup (getLong, with_) and granularity
# selection (nepali_range, make_iterator, _GRANULARITY_FIXED) are defined
# here once so no bare literals appear in logic code.

FIELD_YEAR: str = "year"
FIELD_MONTH: str = "month"
FIELD_DAY: str = "day"
FIELD_DAY_OF_YEAR: str = "day_of_year"
FIELD_DAY_OF_WEEK: str = "day_of_week"
FIELD_HOUR: str = "hour"
FIELD_MINUTE: str = "minute"
FIELD_SECOND: str = "second"
FIELD_MILLISECOND: str = "millisecond"
FIELD_WEEK: str = "week"
FIELD_FORTNIGHT: str = "fortnight"
FIELD_YEARS: str = "years"  # plural form used in plus/minus kwargs
FIELD_MONTHS: str = "months"  # plural form used in plus/minus kwargs

# ---------------------------------------------------------------------------
# GROUPING / ANALYTICS STRING CONSTANTS
# ---------------------------------------------------------------------------
DAY_LITERAL: str = "day"
WEEK_LITERAL: str = "week"
MONTH_LITERAL: str = "month"
QUARTER_LITERAL: str = "quarter"
HALF_LITERAL: str = "half"
YEAR_LITERAL: str = "year"

TODAY_LITERAL: str = "today"
YESTERDAY_LITERAL: str = "yesterday"
TOMORROW_LITERAL: str = "tomorrow"
DAY_AFTER_TOMORROW_LITERAL: str = "day_after_tomorrow"

THIS_WEEK_LITERAL: str = "this_week"
LAST_WEEK_LITERAL: str = "last_week"
NEXT_WEEK_LITERAL: str = "next_week"

THIS_MONTH_LITERAL: str = "this_month"
LAST_MONTH_LITERAL: str = "last_month"
NEXT_MONTH_LITERAL: str = "next_month"

THIS_YEAR_LITERAL: str = "this_year"
LAST_YEAR_LITERAL: str = "last_year"
NEXT_YEAR_LITERAL: str = "next_year"

ROLLING_7_LITERAL: str = "rolling_7"
ROLLING_30_LITERAL: str = "rolling_30"

AAJA_LITERAL: str = "aaja"
HIJO_LITERAL: str = "hijo"
BHOLI_LITERAL: str = "bholi"

AAJA_DEVA_LITERAL: str = "आज"
HIJO_DEVA_LITERAL: str = "हिजो"
BHOLI_DEVA_LITERAL: str = "भोलि"
PARSI_DEVA_LITERAL: str = "पर्सि"

YOHAPTA_DEVA_LITERAL: str = "यो_हप्ता"
GATAHAPTA_DEVA_LITERAL: str = "गत_हप्ता"
AAGAMIHAPTA_DEVA_LITERAL: str = "आगामी_हप्ता"

YOMAHINA_DEVA_LITERAL: str = "यो_महिना"
GATAMAHINA_DEVA_LITERAL: str = "गत_महिना"
AAGAMIMAHINA_DEVA_LITERAL: str = "आगामी_महिना"

YOBARSA_DEVA_LITERAL: str = "यो_वर्ष"
GATABARSA_DEVA_LITERAL: str = "गत_वर्ष"
AAGAMIBARSA_DEVA_LITERAL: str = "आगामी_वर्ष"

CURRENT_WEEK_LITERAL: str = "current_week"
GATAHAPTA_LITERAL: str = "gata_hapta"
AAGAMIHAPTA_LITERAL: str = "aagami_hapta"
CURRENT_MONTH_LITERAL: str = "current_month"
GATAMAHINA_LITERAL: str = "gata_mahina"
AAGAMIMAHINA_LITERAL: str = "aagami_mahina"
YOBARSA_LITERAL: str = "yo_barsa"
GATABARSA_LITERAL: str = "gata_barsa"
AAGAMIBARSA_LITERAL: str = "aagami_barsa"

PASHILLO_7_DEVA_LITERAL: str = "पछिल्लो_७_दिन"
PASHILLO_30_DEVA_LITERAL: str = "पछिल्लो_३०_दिन"
PAST_7_DAYS_LITERAL: str = "past_7_days"
ROLLING_7_DAYS_LITERAL: str = "rolling_7_days"
PAST_30_DAYS_LITERAL: str = "past_30_days"
ROLLING_30_DAYS_LITERAL: str = "rolling_30_days"


# ---------------------------------------------------------------------------
# NepaliDateTime — a thin wrapper that stores a UTC datetime internally
# ---------------------------------------------------------------------------

@dataclass(frozen=True, order=True)
class NepaliDateTime:
    """
    A Nepali (BS) date-time.

    Internally the object holds a standard :class:`datetime.datetime` (UTC
    or timezone-naive, caller's choice). BS year/month/day are derived
    on-demand from the underlying AD datetime.

    Parameters
    ----------
    dt : datetime.datetime
        The underlying Gregorian datetime (timezone-naive or aware).
    """
    dt: datetime.datetime

    # -- BS properties derived from underlying AD datetime ------------------

    @property
    def bs_date(self) -> Tuple[int, int, int]:
        """Return (bs_year, bs_month, bs_day)."""
        return ad_to_bs(self.dt.date())

    @property
    def bs_year(self) -> int:
        return self.bs_date[0]

    @property
    def bs_month(self) -> int:
        return self.bs_date[1]

    @property
    def bs_day(self) -> int:
        return self.bs_date[2]

    @property
    def hour(self) -> int:
        return self.dt.hour

    @property
    def minute(self) -> int:
        return self.dt.minute

    @property
    def second(self) -> int:
        return self.dt.second

    @property
    def microsecond(self) -> int:
        return self.dt.microsecond

    @property
    def millisecond(self) -> int:
        return self.dt.microsecond // 1000

    @property
    def bs_month_name(self) -> str:
        """Latin (romanised) BS month name, e.g. 'Baisakh'."""
        return _BS_MONTH_NAMES[self.bs_month]

    @property
    def bs_month_name_devanagari(self) -> str:
        """Devanagari BS month name, e.g. 'बैशाख'."""
        return _BS_MONTH_NAMES_DEVANAGARI[self.bs_month]

    @property
    def bs_weekday_name(self) -> str:
        """Latin weekday name, e.g. 'Sombar'."""
        return _BS_WEEKDAY_NAMES[self.dt.weekday()]

    @property
    def bs_weekday_name_devanagari(self) -> str:
        """Devanagari weekday name, e.g. 'सोमबार'."""
        return _BS_WEEKDAY_NAMES_DEVANAGARI[self.dt.weekday()]

    @property
    def bs_year_devanagari(self) -> str:
        """BS year in Devanagari numerals, e.g. '२०८१'."""
        return to_devanagari_numeral(self.bs_year)

    @property
    def bs_month_devanagari(self) -> str:
        """BS month number in Devanagari numerals (zero-padded), e.g. '०४'."""
        return to_devanagari_numeral(f"{self.bs_month:02d}")

    @property
    def bs_day_devanagari(self) -> str:
        """BS day number in Devanagari numerals (zero-padded), e.g. '१५'."""
        return to_devanagari_numeral(f"{self.bs_day:02d}")

    def bs_days_in_month(self) -> int:
        return _days_in_bs_month(self.bs_year, self.bs_month)

    # -- Arithmetic ---------------------------------------------------------

    def __add__(self, delta: datetime.timedelta) -> NepaliDateTime:
        return NepaliDateTime(self.dt + delta)

    def __sub__(self, other: NepaliDateTime | datetime.timedelta):
        if isinstance(other, NepaliDateTime):
            return self.dt - other.dt  # timedelta
        return NepaliDateTime(self.dt - other)

    # -- Constructors -------------------------------------------------------

    @classmethod
    def from_bs(cls,
                year: int, month: int, day: int,
                hour: int = 0, minute: int = 0, second: int = 0,
                millisecond: int = 0) -> NepaliDateTime:
        """Build from BS date components."""
        ad_date = bs_to_ad(year, month, day)
        dt = datetime.datetime(
            ad_date.year, ad_date.month, ad_date.day,
            hour, minute, second, millisecond * 1000
        )
        return cls(dt)

    @classmethod
    def from_ad(cls,
                year: int, month: int, day: int,
                hour: int = 0, minute: int = 0, second: int = 0,
                millisecond: int = 0) -> NepaliDateTime:
        """Build from AD date components."""
        dt = datetime.datetime(year, month, day,
                               hour, minute, second, millisecond * 1000)
        return cls(dt)

    @classmethod
    def now(cls) -> NepaliDateTime:
        return cls(datetime.datetime.now())

    # -- Display ------------------------------------------------------------

    def isoformat_bs(self) -> str:
        """ISO-style timestamp using Latin numerals: YYYY-MM-DDTHH:MM:SS.mmm"""
        year, month, day = self.bs_date
        return (f"{year:04d}-{month:02d}-{day:02d}"
                f"T{self.hour:02d}:{self.minute:02d}:{self.second:02d}"
                f".{self.millisecond:03d}")

    def isoformat_bs_devanagari(self) -> str:
        """ISO-style timestamp using Devanagari numerals: YYYY-MM-DDTHH:MM:SS.mmm"""
        year, month, day = self.bs_date
        deva = to_devanagari_numeral
        return (f"{deva(f'{year:04d}')}-{deva(f'{month:02d}')}-{deva(f'{day:02d}')}"
                f"T{deva(f'{self.hour:02d}')}:{deva(f'{self.minute:02d}')}:"
                f"{deva(f'{self.second:02d}')}.{deva(f'{self.millisecond:03d}')}")

    def format_bs(self, devanagari: bool = False) -> str:
        """
        Human-readable BS date string.

        Parameters
        ----------
        devaangari : bool
            If True, render month name, weekday, and numerals in Devanagari.
            If False (default), use Latin script.

        Returns
        -------
        str
            e.g.  'BS 2081-04-15 (Sombar, Shrawan)'
               or 'BS २०८१-०४-१५ (सोमबार, बैशाख)'
        """
        if devanagari:
            return (f"BS {self.isoformat_bs_devanagari()} "
                    f"({self.bs_weekday_name_devanagari}, {self.bs_month_name_devanagari})")
        return (f"BS {self.isoformat_bs()} "
                f"({self.bs_weekday_name}, {self.bs_month_name})")

    def __str__(self) -> str:
        return (f"BS {self.isoformat_bs()} "
                f"({self.bs_weekday_name} / {self.bs_weekday_name_devanagari}, "
                f"{self.bs_month_name} / {self.bs_month_name_devanagari}) "
                f"[AD {self.dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]")

    def __repr__(self) -> str:
        return f"NepaliDateTime(bs={self.bs_date}, ad={self.dt!r})"

    # =========================================================================
    # SECTION 1 — Creation / Factory Methods  (mirroring Java LocalDateTime)
    # =========================================================================

    @classmethod
    def of(
            cls,
            year: int,
            month: int | str,
            day: int,
            hour: int = 0,
            minute: int = 0,
            second: int = 0,
            millisecond: int = 0
    ) -> NepaliDateTime:
        """Create from explicit BS components (month may be name or number).

        Mirrors Java's ``LocalDateTime.of(…)`` factory. Month accepts an
        integer (1-12) or any recognised romanised / Devanagari name.
        """
        return cls.from_bs(
            year, normalize_month_name(month), day,
            hour, minute, second, millisecond
        )

    @classmethod
    def parse(cls, text: str) -> NepaliDateTime:
        """Parse a BS ISO-format string ``YYYY-MM-DDTHH:MM:SS[.mmm]``.

        Mirrors Java's ``LocalDateTime.parse(text)``.  The date portion must
        be a valid BS date; the time portion is optional (defaults to 00:00:00).

        Example::

            NepaliDateTime.parse("2081-04-15T10:30:45.500")
        """
        text = text.strip()
        if "T" in text:
            date_part, time_part = text.split("T", 1)
        else:
            date_part, time_part = text, "00:00:00.000"

        year, month, day = (int(x) for x in date_part.split("-"))

        # Parse HH:MM:SS[.mmm]
        time_parts = time_part.split(":")
        h = int(time_parts[0]) if len(time_parts) > 0 else 0
        mi = int(time_parts[1]) if len(time_parts) > 1 else 0
        sec_ms = time_parts[2] if len(time_parts) > 2 else "0"
        if "." in sec_ms:
            s_str, ms_str = sec_ms.split(".", 1)
            s = int(s_str)
            ms = int(ms_str[:3].ljust(3, "0"))
        else:
            s, ms = int(sec_ms), 0

        return cls.from_bs(year, month, day, h, mi, s, ms)

    @classmethod
    def from_datetime(cls, dt: datetime.datetime) -> NepaliDateTime:
        """Wrap an existing :class:`datetime.datetime` object (AD).

        Mirrors Java's ``LocalDateTime.from(temporal)`` factory.
        """
        return cls(dt)

    # =========================================================================
    # SECTION 2 — Field Accessors  (mirroring Java LocalDateTime.getXxx())
    # =========================================================================

    def get_long(self, field: str) -> int:
        """Return the value of the named field as a long integer.

        Supported field names (case-insensitive):
        ``year``, ``month``, ``day``, ``day_of_year``, ``day_of_week``,
        ``hour``, ``minute``, ``second``, ``millisecond``.
        """
        f = field.lower()
        mapping = {
            FIELD_YEAR: self.get_year,
            FIELD_MONTH: self.get_month_value,
            FIELD_DAY: self.get_day_of_month,
            FIELD_DAY_OF_YEAR: self.get_day_of_year,
            FIELD_DAY_OF_WEEK: self.get_day_of_week,
            FIELD_HOUR: self.get_hour,
            FIELD_MINUTE: self.get_minute,
            FIELD_SECOND: self.get_second,
            FIELD_MILLISECOND: lambda: self.millisecond,
        }
        if f not in mapping:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Valid fields: {list(mapping)}"
            )
        return mapping[f]()

    def get_year(self) -> int:
        """Return the BS year, e.g. 2081."""
        return self.bs_year

    def get_month(self) -> str:
        """Return the BS month name (Latin), e.g. 'Shrawan'."""
        return self.bs_month_name

    def get_month_value(self) -> int:
        """Return the BS month as an integer 1-12."""
        return self.bs_month

    def get_day_of_month(self) -> int:
        """Return the BS day-of-month (1 – 32)."""
        return self.bs_day

    def get_day_of_year(self) -> int:
        """Return the BS day-of-year (1 – 366).

        Computed by summing completed BS months of the current year plus the
        current day.
        """
        year, month, day = self.bs_date
        completed = sum(_BS_YEAR_DATA[year][:month - 1])
        return completed + day

    def get_day_of_week(self) -> int:
        """Return the Python weekday integer (Monday=0 … Sunday=6)."""
        return self.dt.weekday()

    def get_hour(self) -> int:
        """Return the hour-of-day (0-23)."""
        return self.hour

    def get_minute(self) -> int:
        """Return the minute-of-hour (0-59)."""
        return self.minute

    def get_second(self) -> int:
        """Return the second-of-minute (0-59)."""
        return self.second

    # =========================================================================
    # SECTION 3 — Date / Time Extraction  (toLocalDate / toLocalTime)
    # =========================================================================

    def to_local_date(self) -> datetime.date:
        """Extract the underlying AD :class:`datetime.date` component.

        Mirrors Java's ``LocalDateTime.toLocalDate()``.
        """
        return self.dt.date()

    def to_local_time(self) -> datetime.time:
        """Extract the underlying :class:`datetime.time` component (H:M:S.μs).

        Mirrors Java's ``LocalDateTime.toLocalTime()``.
        """
        return self.dt.time()

    def to_bs_date(self) -> Tuple[int, int, int]:
        """Return the BS date triple ``(year, month, day)``."""
        return self.bs_date

    # =========================================================================
    # SECTION 4 — Modification / Adjustment  (with / withXxx)
    # =========================================================================

    def with_(self, **fields) -> NepaliDateTime:
        """Return a copy with the specified BS or time fields replaced.

        Accepted keyword arguments:
        ``year``, ``month``, ``day``, ``hour``, ``minute``, ``second``,
        ``millisecond``.

        Mirrors Java's ``LocalDateTime.with(field, value)``.

        Example::

            ndt.with_(year=2082, hour=9)
        """
        year, month, day = self.bs_date
        h, mi, s, ms = self.hour, self.minute, self.second, self.millisecond
        year = fields.get(FIELD_YEAR, year)
        month = normalize_month_name(
            fields[FIELD_MONTH]) if FIELD_MONTH in fields else month
        day = fields.get(FIELD_DAY, day)
        h = fields.get(FIELD_HOUR, h)
        mi = fields.get(FIELD_MINUTE, mi)
        s = fields.get(FIELD_SECOND, s)
        ms = fields.get(FIELD_MILLISECOND, ms)
        # Clamp day to valid range for the target BS month
        day = min(day, _days_in_bs_month(year, month))
        return NepaliDateTime.from_bs(year, month, day, h, mi, s, ms)

    def with_year(self, year: int) -> NepaliDateTime:
        """Return a copy with the BS year replaced.

        Day is clamped if it exceeds the number of days in the target month.
        """
        return self.with_(year=year)

    def with_month(self, month: "int | str") -> NepaliDateTime:
        """Return a copy with the BS month replaced (int or name).

        Day is clamped to the new month's length if necessary.
        """
        return self.with_(month=month)

    def with_day_of_month(self, day: int) -> NepaliDateTime:
        """Return a copy with the BS day-of-month replaced."""
        return self.with_(day=day)

    def with_day_of_year(self, day_of_year: int) -> NepaliDateTime:
        """Return a copy with the BS day-of-year replaced.

        Walks the BS month table for the current BS year to find the
        target month and day.
        """
        year = self.bs_year
        if day_of_year < 1:
            raise ValueError("day_of_year must be >= 1.")
        remaining = day_of_year
        for month_idx in range(1, TOTAL_MONTHS + 1):
            dim = _BS_YEAR_DATA[year][month_idx - 1]
            if remaining <= dim:
                return NepaliDateTime.from_bs(
                    year, month_idx, remaining,
                    self.hour, self.minute, self.second, self.millisecond
                )
            remaining -= dim
        raise ValueError(
            f"day_of_year={day_of_year} exceeds total days in BS year {year}."
        )

    def with_hour(self, hour: int) -> NepaliDateTime:
        """Return a copy with the hour replaced (0-23)."""
        return self.with_(hour=hour)

    def with_minute(self, minute: int) -> NepaliDateTime:
        """Return a copy with the minute replaced (0-59)."""
        return self.with_(minute=minute)

    def with_second(self, second: int) -> NepaliDateTime:
        """Return a copy with the second replaced (0-59)."""
        return self.with_(second=second)

    # =========================================================================
    # SECTION 5 — Arithmetic Operations  (plus / minus)
    # =========================================================================

    # -- Generic plus / minus -------------------------------------------------

    def plus(self, **kwargs) -> NepaliDateTime:
        """Add a duration expressed as keyword arguments.

        All keyword arguments are forwarded to :class:`datetime.timedelta`
        **except** ``years`` and ``months``, which are handled in BS calendar
        space.

        Example::

            ndt.plus(years=1, months=2, days=3, hours=4)
        """
        result = self
        if FIELD_YEARS in kwargs:
            result = result.plus_years(kwargs.pop(FIELD_YEARS))
        if FIELD_MONTHS in kwargs:
            result = result.plus_months(kwargs.pop(FIELD_MONTHS))
        if kwargs:
            result = NepaliDateTime(result.dt + datetime.timedelta(**kwargs))
        return result

    def minus(self, **kwargs) -> NepaliDateTime:
        """Subtract a duration expressed as keyword arguments.

        Mirror of :meth:`plus`; negates all values before delegating.

        Example::

            ndt.minus(days=7, hours=2)
        """
        negated = {k: -v for k, v in kwargs.items()}
        return self.plus(**negated)

    # -- Year-level -----------------------------------------------------------

    def plus_years(self, years: int) -> NepaliDateTime:
        """Return a copy with the given number of BS years added.

        The day is clamped to the new month's length when it would overflow
        (e.g. adding 1 year to Chaitra 30 in a year where Chaitra has 29 days).
        """
        year, month, day = self.bs_date
        next_year = year + years
        if next_year not in _BS_YEAR_DATA:
            raise ValueError(
                f"Resulting BS year {next_year} is out of supported range.")
        d_clamped = min(day, _BS_YEAR_DATA[next_year][month - 1])
        return NepaliDateTime.from_bs(
            next_year, month, d_clamped,
            self.hour, self.minute, self.second, self.millisecond
        )

    def minus_years(self, years: int) -> NepaliDateTime:
        """Return a copy with the given number of BS years subtracted."""
        return self.plus_years(-years)

    # -- Month-level ----------------------------------------------------------

    def plus_months(self, months: int) -> NepaliDateTime:
        """Return a copy with the given number of BS months added.

        Rolls over year boundaries; day is clamped to the target month's
        length when necessary.
        """
        year, month, day = self.bs_date
        total_months = (year - _BS_MIN_YEAR) * TOTAL_MONTHS + (month - 1) + months
        next_year = _BS_MIN_YEAR + total_months // TOTAL_MONTHS
        next_month = total_months % TOTAL_MONTHS + 1
        if next_year not in _BS_YEAR_DATA:
            raise ValueError(
                f"Resulting BS year {next_year} is out of supported range.")
        d_clamped = min(day, _BS_YEAR_DATA[next_year][next_month - 1])
        return NepaliDateTime.from_bs(
            next_year, next_month, d_clamped,
            self.hour, self.minute, self.second, self.millisecond
        )

    def minus_months(self, months: int) -> NepaliDateTime:
        """Return a copy with the given number of BS months subtracted."""
        return self.plus_months(-months)

    # -- Week-level -----------------------------------------------------------

    def plus_weeks(self, weeks: int) -> NepaliDateTime:
        """Return a copy with the given number of weeks added (7 days each)."""
        return NepaliDateTime(self.dt + datetime.timedelta(weeks=weeks))

    def minus_weeks(self, weeks: int) -> NepaliDateTime:
        """Return a copy with the given number of weeks subtracted."""
        return self.plus_weeks(-weeks)

    # -- Day-level ------------------------------------------------------------

    def plus_days(self, days: int) -> NepaliDateTime:
        """Return a copy with the given number of days added."""
        return NepaliDateTime(self.dt + datetime.timedelta(days=days))

    def minus_days(self, days: int) -> NepaliDateTime:
        """Return a copy with the given number of days subtracted."""
        return self.plus_days(-days)

    # -- Hour-level -----------------------------------------------------------

    def plus_hours(self, hours: int) -> NepaliDateTime:
        """Return a copy with the given number of hours added."""
        return NepaliDateTime(self.dt + datetime.timedelta(hours=hours))

    def minus_hours(self, hours: int) -> NepaliDateTime:
        """Return a copy with the given number of hours subtracted."""
        return self.plus_hours(-hours)

    # -- Minute-level ---------------------------------------------------------

    def plus_minutes(self, minutes: int) -> NepaliDateTime:
        """Return a copy with the given number of minutes added."""
        return NepaliDateTime(self.dt + datetime.timedelta(minutes=minutes))

    def minus_minutes(self, minutes: int) -> NepaliDateTime:
        """Return a copy with the given number of minutes subtracted."""
        return self.plus_minutes(-minutes)

    # -- Second-level ---------------------------------------------------------

    def plus_seconds(self, seconds: int) -> NepaliDateTime:
        """Return a copy with the given number of seconds added."""
        return NepaliDateTime(self.dt + datetime.timedelta(seconds=seconds))

    def minus_seconds(self, seconds: int) -> NepaliDateTime:
        """Return a copy with the given number of seconds subtracted."""
        return self.plus_seconds(-seconds)


# ---------------------------------------------------------------------------
# GRANULARITY TIMEDELTA CONSTANTS
# ---------------------------------------------------------------------------

# Named interval sizes expressed as timedelta factory arguments.
# Keeping them as plain dicts means zero import overhead and easy extension.
_MILLISECOND = datetime.timedelta(milliseconds=1)
_SECOND = datetime.timedelta(seconds=1)
_MINUTE = datetime.timedelta(minutes=1)
_HOUR = datetime.timedelta(hours=1)
_DAY = datetime.timedelta(days=1)

# Week and fortnight are exact multiples
_WEEK = datetime.timedelta(weeks=1)
_FORTNIGHT = datetime.timedelta(weeks=2)

# "Month" and "year" are variable-length; handled specially in nepali_range.
_GRANULARITY_FIXED: dict[str, datetime.timedelta] = {
    FIELD_MILLISECOND: _MILLISECOND,
    FIELD_SECOND: _SECOND,
    FIELD_MINUTE: _MINUTE,
    FIELD_HOUR: _HOUR,
    FIELD_DAY: _DAY,
    FIELD_WEEK: _WEEK,
    FIELD_FORTNIGHT: _FORTNIGHT,
}


# ---------------------------------------------------------------------------
# ITERATOR FACTORIES
# ---------------------------------------------------------------------------

def _next_bs_month(ndt: NepaliDateTime) -> NepaliDateTime:
    """Advance by exactly one BS month, preserving H/M/S/ms."""
    year, month, day = ndt.bs_date
    next_month, next_year = (month + 1, year) if month < TOTAL_MONTHS else (UNIT_MONTH, year + 1)
    max_d = _days_in_bs_month(next_year, next_month)
    d_clamped = min(day, max_d)
    return NepaliDateTime.from_bs(
        next_year, next_month, d_clamped,
        ndt.hour, ndt.minute, ndt.second, ndt.millisecond
    )


def _next_bs_year(ndt: NepaliDateTime) -> NepaliDateTime:
    """Advance by exactly one BS year, preserving M/D/H/M/S/ms."""
    year, month, day = ndt.bs_date
    next_year = year + 1
    if next_year > _BS_MAX_YEAR:
        raise StopIteration
    max_d = _days_in_bs_month(next_year, month)
    d_clamped = min(day, max_d)
    return NepaliDateTime.from_bs(
        next_year, month, d_clamped,
        ndt.hour, ndt.minute, ndt.second, ndt.millisecond
    )


def nepali_range(
        start: NepaliDateTime,
        stop: Optional[NepaliDateTime] = None,
        *,
        granularity: str = "day",
        step: int = 1,
        count: Optional[int] = None,
) -> Generator[NepaliDateTime, None, None]:
    """
    A granularity-aware iterator over :class:`NepaliDateTime` values.

    The iterator walks forward (or backward if step is negative) from
    *start* until *stop* (exclusive) or *count* items are produced.

    Parameters
    ----------
    start       : NepaliDateTime  — starting point (inclusive)
    stop        : NepaliDateTime  — ending point   (exclusive); optional
    granularity : str             — one of:
                  'millisecond', 'second', 'minute', 'hour',
                  'day', 'week', 'fortnight', 'month', 'year'
    step        : int             — number of granularity units per tick (default 1)
    count       : int             — maximum items to yield (overrides stop)

    Yields
    ------
    NepaliDateTime
    """
    if step == 0:
        raise ValueError("step must not be zero.")

    gran_lower = granularity.lower()
    yielded = 0
    current = start

    def _should_continue(cur: NepaliDateTime) -> bool:
        if stop is None:
            return True
        return (cur < stop) if step > 0 else (cur > stop)

    def _advance(cur: NepaliDateTime, n: int = 1) -> NepaliDateTime:
        """Advance by |step| units of the chosen granularity."""
        if gran_lower == FIELD_MONTH:
            result = cur
            for _ in range(abs(n)):
                result = _next_bs_month(result)
            return result if n > 0 else NotImplemented  # backward month NYI
        if gran_lower == FIELD_YEAR:
            result = cur
            for _ in range(abs(n)):
                result = _next_bs_year(result)
            return result
        # fixed-width granularities
        delta = _GRANULARITY_FIXED.get(gran_lower)
        if delta is None:
            raise ValueError(
                f"Unknown granularity '{granularity}'. "
                f"Choose from: {sorted(_GRANULARITY_FIXED)} + ['{FIELD_MONTH}', '{FIELD_YEAR}']."
            )
        return NepaliDateTime(cur.dt + delta * n)

    while _should_continue(current):
        if count is not None and yielded >= count:
            return
        yield current
        current = _advance(current, step)
        yielded += 1


# ---------------------------------------------------------------------------
# CONVENIENCE ITERATOR CLASSES
# ---------------------------------------------------------------------------

class _BaseIterator:
    """
    Base class for all granularity iterators.

    All sub-classes share the same __iter__/__next__ mechanics; only
    the granularity string differs.
    """
    _granularity: str = FIELD_DAY  # overridden by subclasses

    def __init__(
            self,
            start: NepaliDateTime,
            stop: Optional[NepaliDateTime] = None,
            *,
            step: int = 1,
            count: Optional[int] = None,
    ) -> None:
        self._gen: Generator[NepaliDateTime, None, None] = nepali_range(
            start, stop,
            granularity=self._granularity,
            step=step,
            count=count,
        )

    def __iter__(self) -> Iterator[NepaliDateTime]:
        return self._gen

    def __next__(self) -> NepaliDateTime:
        return next(self._gen)

    def take(self, n: int) -> List[NepaliDateTime]:
        """Return up to *n* items as a list (collector style)."""
        return list(islice(self._gen, n))


class MillisecondIterator(_BaseIterator):
    """Iterate every millisecond."""
    _granularity = FIELD_MILLISECOND


class SecondIterator(_BaseIterator):
    """Iterate every second."""
    _granularity = FIELD_SECOND


class MinuteIterator(_BaseIterator):
    """Iterate every minute."""
    _granularity = FIELD_MINUTE


class HourIterator(_BaseIterator):
    """Iterate every hour."""
    _granularity = FIELD_HOUR


class DayIterator(_BaseIterator):
    """Iterate every day."""
    _granularity = FIELD_DAY


class WeekIterator(_BaseIterator):
    """Iterate every week."""
    _granularity = FIELD_WEEK


class FortnightIterator(_BaseIterator):
    """Iterate every fortnight (2 weeks)."""
    _granularity = FIELD_FORTNIGHT


class MonthIterator(_BaseIterator):
    """Iterate every BS calendar month (variable-length)."""
    _granularity = FIELD_MONTH


class YearIterator(_BaseIterator):
    """Iterate every BS calendar year (variable-length)."""
    _granularity = FIELD_YEAR


# ---------------------------------------------------------------------------
# FACTORY FUNCTION  (single public entry-point for iterators)
# ---------------------------------------------------------------------------

# Registry maps granularity name → iterator class  (constants-out principle)
_ITERATOR_REGISTRY: dict[str, type] = {
    FIELD_MILLISECOND: MillisecondIterator,
    FIELD_SECOND: SecondIterator,
    FIELD_MINUTE: MinuteIterator,
    FIELD_HOUR: HourIterator,
    FIELD_DAY: DayIterator,
    FIELD_WEEK: WeekIterator,
    FIELD_FORTNIGHT: FortnightIterator,
    FIELD_MONTH: MonthIterator,
    FIELD_YEAR: YearIterator,
}


def make_iterator(
        granularity: str,
        start: NepaliDateTime,
        stop: Optional[NepaliDateTime] = None,
        *,
        step: int = 1,
        count: Optional[int] = None,
) -> _BaseIterator:
    """
    Factory function to create a granularity-based Nepali date iterator.

    Parameters
    ----------
    granularity : str
        One of 'millisecond', 'second', 'minute', 'hour', 'day',
        'week', 'fortnight', 'month', 'year'.
    start, stop : NepaliDateTime
        Range bounds (stop is exclusive).
    step        : int  — ticks per granularity unit (default 1).
    count       : int  — cap on number of values yielded.

    Returns
    -------
    _BaseIterator  (iterable, supports .take(n))

    Examples
    --------
    >>> it = make_iterator("day",
    ...         NepaliDateTime.from_bs(2081, 1, 1),
    ...         count=7)
    >>> for ndt in it:
    ...     print(ndt.isoformat_bs())
    """
    key = granularity.lower()
    cls = _ITERATOR_REGISTRY.get(key)
    if cls is None:
        raise ValueError(
            f"Unknown granularity '{granularity}'. "
            f"Available: {sorted(_ITERATOR_REGISTRY)}."
        )
    return cls(start, stop, step=step, count=count)


# ---------------------------------------------------------------------------
# UTILITY: calendar month grid for a BS month
# ---------------------------------------------------------------------------

def bs_month_calendar(year: int, month: int) -> List[List[Optional[int]]]:
    """
    Return a 6×7 calendar grid for a BS year/month.

    Cells contain BS day numbers; None = padding.
    Columns: Mon Tue Wed Thu Fri Sat Sun  (standard Python weekday order)
    """
    first_ad = bs_to_ad(year, month, 1)
    start_dow = first_ad.weekday()  # 0=Mon … 6=Sun
    total_days = _days_in_bs_month(year, month)

    # flat list of day numbers with leading/trailing Nones — collector style
    cells: List[Optional[int]] = (
            [None] * start_dow + list(range(1, total_days + 1))
    )
    # pad to multiple of 7
    cells += [None] * ((-len(cells)) % 7)

    # chunk into weeks
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


# ---------------------------------------------------------------------------
# PHRASE ALIASES
# Maps English, Romanised Nepali, and Devanagari phrases to a single canonical key
# ---------------------------------------------------------------------------
_PHRASE_ALIASES: Dict[str, str] = {
    # Points
    TODAY_LITERAL: TODAY_LITERAL, AAJA_DEVA_LITERAL: TODAY_LITERAL,
    AAJA_LITERAL: TODAY_LITERAL,
    YESTERDAY_LITERAL: YESTERDAY_LITERAL, HIJO_DEVA_LITERAL: YESTERDAY_LITERAL,
    HIJO_LITERAL: YESTERDAY_LITERAL,
    TOMORROW_LITERAL: TOMORROW_LITERAL, BHOLI_DEVA_LITERAL: TOMORROW_LITERAL,
    BHOLI_LITERAL: TOMORROW_LITERAL,
    # Weekly
    THIS_WEEK_LITERAL: THIS_WEEK_LITERAL,
    YOHAPTA_DEVA_LITERAL: THIS_WEEK_LITERAL,
    CURRENT_WEEK_LITERAL: THIS_WEEK_LITERAL,
    LAST_WEEK_LITERAL: LAST_WEEK_LITERAL,
    GATAHAPTA_DEVA_LITERAL: LAST_WEEK_LITERAL,
    GATAHAPTA_LITERAL: LAST_WEEK_LITERAL,
    NEXT_WEEK_LITERAL: NEXT_WEEK_LITERAL,
    AAGAMIHAPTA_DEVA_LITERAL: NEXT_WEEK_LITERAL,
    AAGAMIHAPTA_LITERAL: NEXT_WEEK_LITERAL,
    # Monthly
    THIS_MONTH_LITERAL: THIS_MONTH_LITERAL,
    YOMAHINA_DEVA_LITERAL: THIS_MONTH_LITERAL,
    CURRENT_MONTH_LITERAL: THIS_MONTH_LITERAL,
    LAST_MONTH_LITERAL: LAST_MONTH_LITERAL,
    GATAMAHINA_DEVA_LITERAL: LAST_MONTH_LITERAL,
    GATAMAHINA_LITERAL: LAST_MONTH_LITERAL,
    NEXT_MONTH_LITERAL: NEXT_MONTH_LITERAL,
    AAGAMIMAHINA_DEVA_LITERAL: NEXT_MONTH_LITERAL,
    AAGAMIMAHINA_LITERAL: NEXT_MONTH_LITERAL,
    # Yearly
    THIS_YEAR_LITERAL: THIS_YEAR_LITERAL,
    YOBARSA_DEVA_LITERAL: THIS_YEAR_LITERAL, YOBARSA_LITERAL: THIS_YEAR_LITERAL,
    LAST_YEAR_LITERAL: LAST_YEAR_LITERAL,
    GATABARSA_DEVA_LITERAL: LAST_YEAR_LITERAL,
    GATABARSA_LITERAL: LAST_YEAR_LITERAL,
    NEXT_YEAR_LITERAL: NEXT_YEAR_LITERAL,
    AAGAMIBARSA_DEVA_LITERAL: NEXT_YEAR_LITERAL,
    AAGAMIBARSA_LITERAL: NEXT_YEAR_LITERAL,
    # Rolling Windows
    ROLLING_7_DAYS_LITERAL: ROLLING_7_LITERAL,
    PAST_7_DAYS_LITERAL: ROLLING_7_LITERAL,
    PASHILLO_7_DEVA_LITERAL: ROLLING_7_LITERAL,
    ROLLING_30_DAYS_LITERAL: ROLLING_30_LITERAL,
    PAST_30_DAYS_LITERAL: ROLLING_30_LITERAL,
    PASHILLO_30_DEVA_LITERAL: ROLLING_30_LITERAL,
}

# ---------------------------------------------------------------------------
# PHRASE RESOLVERS REGISTRY
# Maps canonical phrase -> lambda taking (ref_date, is_bs) explicitly returning DateRange
# ---------------------------------------------------------------------------
_DAY_DELTA = lambda n: datetime.timedelta(days=n)


def _resolve_month_relative(r: datetime.date, bs: bool,
                            offset: int = 0) -> DateRange:
    if bs:
        year, month = ad_to_bs(r)[:2]
        target_m = (month - 1 + offset) % TOTAL_MONTHS + 1
        target_y = year + (month - 1 + offset) // TOTAL_MONTHS
        return bs_month_to_ad_range(target_m, target_y)

    target_m = (r.month - 1 + offset) % TOTAL_MONTHS + 1
    target_y = r.year + (r.month - 1 + offset) // TOTAL_MONTHS
    return ad_month_to_bs_range(target_m, target_y)


def _resolve_year_relative(r: datetime.date, bs: bool,
                           offset: int = 0) -> DateRange:
    if bs:
        return bs_year_to_ad_range(ad_to_bs(r)[0] + offset)
    return ad_year_to_bs_range(r.year + offset)


_PHRASE_RESOLVERS: Dict[str, Callable[[datetime.date, bool], DateRange]] = {
    TODAY_LITERAL: lambda r, bs: DateRange(r, r, label="Today"),
    YESTERDAY_LITERAL: lambda r, bs: DateRange(r - _DAY_DELTA(1),
                                               r - _DAY_DELTA(1),
                                               label="Yesterday"),
    TOMORROW_LITERAL: lambda r, bs: DateRange(r + _DAY_DELTA(1),
                                              r + _DAY_DELTA(1),
                                              label="Tomorrow"),

    THIS_WEEK_LITERAL: lambda r, bs: DateRange(r - _DAY_DELTA(r.weekday()),
                                               r + _DAY_DELTA(6 - r.weekday()),
                                               label="This Week"),
    LAST_WEEK_LITERAL: lambda r, bs: DateRange(r - _DAY_DELTA(r.weekday() + 7),
                                               r - _DAY_DELTA(r.weekday() + 1),
                                               label="Last Week"),
    NEXT_WEEK_LITERAL: lambda r, bs: DateRange(r + _DAY_DELTA(7 - r.weekday()),
                                               r + _DAY_DELTA(13 - r.weekday()),
                                               label="Next Week"),

    ROLLING_7_LITERAL: lambda r, bs: DateRange(r - _DAY_DELTA(6), r,
                                               label="Last 7 Days"),
    ROLLING_30_LITERAL: lambda r, bs: DateRange(r - _DAY_DELTA(29), r,
                                                label="Last 30 Days"),

    # Calendar Aware Resolvers (Evaluates AD->BS or AD->AD dynamically)
    THIS_MONTH_LITERAL: lambda r, bs: _resolve_month_relative(r, bs, 0),
    LAST_MONTH_LITERAL: lambda r, bs: _resolve_month_relative(r, bs, -1),
    NEXT_MONTH_LITERAL: lambda r, bs: _resolve_month_relative(r, bs, 1),

    THIS_YEAR_LITERAL: lambda r, bs: _resolve_year_relative(r, bs, 0),
    LAST_YEAR_LITERAL: lambda r, bs: _resolve_year_relative(r, bs, -1),
    NEXT_YEAR_LITERAL: lambda r, bs: _resolve_year_relative(r, bs, 1),
}


# ---------------------------------------------------------------------------
# ABSOLUTE PERIOD GENERATORS
# Generate a sequence of contiguous buckets over an AD window
# ---------------------------------------------------------------------------
def _generate_months(min_d: datetime.date, max_d: datetime.date, is_bs: bool) -> \
        List[DateRange]:
    """Helper to calculate month intervals for both AD and BS calendars."""
    start_y, start_m = ad_to_bs(min_d)[:2] if is_bs else (min_d.year,
                                                          min_d.month)
    end_y, end_m = ad_to_bs(max_d)[:2] if is_bs else (max_d.year, max_d.month)
    total_months = (end_y - start_y) * 12 + (end_m - start_m) + 1

    return [
        bs_month_to_ad_range(
            (
                start_m - 1 + i) % 12 + 1,
                start_y + (start_m - 1 + i) // 12
         ) if is_bs
        else ad_month_to_bs_range(
            (start_m - 1 + i) % 12 + 1, start_y + (start_m - 1 + i) // 12
        )
        for i in range(total_months)
    ]


def _generate_quarters(min_d: datetime.date, max_d: datetime.date,
                       is_bs: bool) -> List[DateRange]:
    """Helper to calculate quarter (3-month) intervals for both AD and BS calendars."""
    start_y, start_m = ad_to_bs(min_d)[:2] if is_bs else (min_d.year, min_d.month)
    end_y, end_m = ad_to_bs(max_d)[:2] if is_bs else (max_d.year, max_d.month)
    start_q, end_q = (start_m - 1) // 3 + 1, (end_m - 1) // 3 + 1
    total_quarters = (end_y - start_y) * 4 + (end_q - start_q) + 1

    return [
        bs_quarter_to_ad_range(
            (start_q - 1 + i) % 4 + 1, start_y + (start_q - 1 + i) // 4
        ) if is_bs
        else ad_quarter_to_bs_range(
            (start_q - 1 + i) % 4 + 1, start_y + (start_q - 1 + i) // 4
        )
        for i in range(total_quarters)
    ]


def _generate_halves(min_d: datetime.date, max_d: datetime.date, is_bs: bool) -> \
        List[DateRange]:
    """Helper to calculate half-year (6-month) intervals for both AD and BS calendars."""
    start_y, start_m = ad_to_bs(min_d)[:2] if is_bs else (min_d.year, min_d.month)
    end_y, end_m = ad_to_bs(max_d)[:2] if is_bs else (max_d.year, max_d.month)
    start_h, end_h = (start_m - 1) // 6 + 1, (end_m - 1) // 6 + 1
    total_halves = (end_y - start_y) * 2 + (end_h - start_h) + 1

    return [
        bs_half_to_ad_range(
            (start_h - 1 + i) % 2 + 1, start_y + (start_h - 1 + i) // 2
        ) if is_bs
        else ad_half_to_bs_range(
            (start_h - 1 + i) % 2 + 1, start_y + (start_h - 1 + i) // 2
        )
        for i in range(total_halves)
    ]


def _generate_weeks(min_d: datetime.date, max_d: datetime.date, bs: bool) -> \
        List[DateRange]:
    start_w = min_d - _DAY_DELTA(min_d.weekday())
    total_weeks = (max_d - start_w).days // 7 + 1
    return [
        DateRange(
            start_w + _DAY_DELTA(i * 7), start_w + _DAY_DELTA(i * 7 + 6),
            label=f"Week of {start_w + _DAY_DELTA(i * 7)}"
        )
        for i in range(total_weeks)
    ]


_PERIOD_GENERATORS: Dict[str, Callable[
    [datetime.date, datetime.date, bool], Iterable[DateRange]]] = {
    DAY_LITERAL: lambda min_d, max_d, bs: [
        DateRange(
            min_d + _DAY_DELTA(i), min_d + _DAY_DELTA(i), label=str(min_d + _DAY_DELTA(i))
        )
        for i in range((max_d - min_d).days + 1)
    ],
    WEEK_LITERAL: _generate_weeks,
    MONTH_LITERAL: _generate_months,
    QUARTER_LITERAL: _generate_quarters,
    HALF_LITERAL: _generate_halves,
    YEAR_LITERAL: lambda min_d, max_d, bs: [
        bs_year_to_ad_range(year) if bs else ad_year_to_bs_range(year)
        for year in range(
            (ad_to_bs(min_d)[0] if bs else min_d.year),
            (ad_to_bs(max_d)[0] if bs else max_d.year) + 1
        )
    ]
}

_DEVA_TRANS_MAP = str.maketrans(
    _DEVANAGARI_DIGIT_REVERSE) if '_DEVANAGARI_DIGIT_REVERSE' in globals() else None


# Helper to process devanagari phrase conversion correctly
def _to_ascii_phrase(phrase: str) -> str:
    if not isinstance(phrase, str):
        return phrase
    # Convert devanagari to english mapping
    for key, val in {
        AAJA_DEVA_LITERAL: TODAY_LITERAL, HIJO_DEVA_LITERAL: YESTERDAY_LITERAL,
        BHOLI_DEVA_LITERAL: TOMORROW_LITERAL,
        PARSI_DEVA_LITERAL: DAY_AFTER_TOMORROW_LITERAL,
        YOHAPTA_DEVA_LITERAL: THIS_WEEK_LITERAL,
        GATAHAPTA_DEVA_LITERAL: LAST_WEEK_LITERAL,
        AAGAMIHAPTA_DEVA_LITERAL: NEXT_WEEK_LITERAL,
        YOMAHINA_DEVA_LITERAL: THIS_MONTH_LITERAL,
        GATAMAHINA_DEVA_LITERAL: LAST_MONTH_LITERAL,
        AAGAMIMAHINA_DEVA_LITERAL: NEXT_MONTH_LITERAL,
        YOBARSA_DEVA_LITERAL: THIS_YEAR_LITERAL,
        GATABARSA_DEVA_LITERAL: LAST_YEAR_LITERAL,
        AAGAMIBARSA_DEVA_LITERAL: NEXT_YEAR_LITERAL,
        PASHILLO_7_DEVA_LITERAL: ROLLING_7_LITERAL,
        PASHILLO_30_DEVA_LITERAL: ROLLING_30_LITERAL
    }.items():
        if phrase == key:
            return val
    return phrase.translate(
        _DEVA_TRANS_MAP).lower() if _DEVA_TRANS_MAP else phrase.lower()


def _normalize_input(entry: Any, fallback_bs: bool = True) -> datetime.date:
    """Safely extracts a naive datetime.date from various object sources."""
    try:
        if hasattr(entry, "dt"):
            return entry.dt.date()
        if hasattr(entry, "date") and callable(entry.date):
            return entry.date()
        if isinstance(entry, datetime.date):
            return entry

        str_val = str(entry).translate(
            _DEVA_TRANS_MAP) if _DEVA_TRANS_MAP else str(entry)
        if fallback_bs:
            return NepaliDateTime.parse(str_val).dt.date()
        return datetime.datetime.fromisoformat(str_val).date()
    except Exception as e:
        raise ValueError(
            f"Could not normalize input to canonical AD date: {entry}. Reason: {e}")


def _resolve_relative(phrase: str, ref_dt: datetime.date,
                      is_bs: bool) -> DateRange:
    """Resolve a relative string using the registry, or via regular expression offset fallback."""
    ascii_phr = _to_ascii_phrase(phrase.strip())
    key = _PHRASE_ALIASES.get(ascii_phr.replace(" ", "_"), ascii_phr)

    if key in _PHRASE_RESOLVERS:
        return _PHRASE_RESOLVERS[key](ref_dt, is_bs)

    match = _RELATIVE_PATTERN.match(key)
    if not match:
        raise ValueError(f"Unrecognised relative phrase: {phrase}")

    val, unit = int(match.group(1)), match.group(2)
    start_d = ref_dt - _DAY_DELTA(val * (7 if unit == WEEK_LITERAL else 1))

    if unit == WEEK_LITERAL:
        return DateRange(
            start_d - _DAY_DELTA(start_d.weekday()), 
            start_d + _DAY_DELTA(6 - start_d.weekday()),
            label=phrase
        )
    return DateRange(start_d, start_d, label=phrase)


def group_dates(
        dates: List[Any],
        by: str | List[str],
        calendar: Literal["BS", "AD"] = "BS",
        ref_date: datetime.date | None = None
) -> Dict[str, List[Any]]:
    """
    Groups a mixed list of AD/BS objects, strings & numerals into bucketed periods.
    """
    ref_dt = ref_date or datetime.date.today()
    is_bs = calendar.upper() == "BS"

    # 1. Normalize all inputs paired with original objects
    canonicals = [(orig, _normalize_input(orig, is_bs)) for orig in dates]
    if not canonicals:
        return {}

    # 2. Resolve buckets (either generated dynamically or explicitly requested)
    buckets: List[DateRange] = (
        [_resolve_relative(phrase, ref_dt, is_bs) for phrase in
         by] if isinstance(by, list) else
        _PERIOD_GENERATORS[by.lower()](
            min(ad_dt for _, ad_dt in canonicals),
            max(ad_dt for _, ad_dt in canonicals), 
            is_bs
        )
    )

    return {
        bucket.label: [
            item for item, ad_dt in canonicals if bucket.contains_date(ad_dt)
        ]
        for bucket in sorted(buckets, key=lambda b: b.start_ad)
    }
