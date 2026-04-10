from library.nepali_date import _BS_MONTH_ALIASES, _WEEKDAY_ALIASES, _AD_MONTH_ALIASES, _DEVANAGARI_DIGIT_MAP

_DEVANAGARI_DIGIT_REVERSE = {v: str(k - ord("0")) for k, v in _DEVANAGARI_DIGIT_MAP.items()}

_TEMPORAL_UNITS = {
    "वर्ष": "year", "बर्ष": "year", "साल": "year",
    "महिना": "month",
    "हप्ता": "week",
    "दिन": "day",
    "barsa": "year", "sal": "year",
    "mahina": "month",
    "hapta": "week",
    "din": "day",
    "year": "year", "month": "month", "week": "week", "day": "day",
    "years": "year", "months": "month", "weeks": "week", "days": "day",
    "fortnight": "fortnight", "quarter": "quarter", "पक्ष": "fortnight", "biweek": "fortnight",
    "त्रैमास": "quarter", "त्रैमासिक": "quarter", "चौमासिक": "third", "third": "third",
    "षाण्मासिक": "half", "अर्धवार्षिक": "half", "half": "half", "half_year": "half", "semester": "half",
    "भाग": "half", "आधा": "half", "तिहाई": "third",
}

_TEMPORAL_MODIFIERS = {
    "यो": "this", "यस": "this", "यही": "this",
    "त्यो": "that", "त्यस": "that", "उही": "that",
    "the": "this", "this": "this", "that": "that",
    "गत": "last", "गएको": "last", "बितेको": "last", "अघिल्लो": "last", "last": "last",
    "previous": "last", "past": "last",
    "आगामी": "next", "अर्को": "next", "आउने": "next", "next": "next",
    "coming": "next", "upcoming": "next",
    "अन्तिम": "last_of", "सुरुको": "first_of", "सुरुमा": "first_of", "शुरुमा": "first_of", "शुरुको": "first_of", "सुरुदेखि": "first_of", "शुरुदेखि": "first_of",
    "early": "first_of", "start_of": "first_of", "beginning_of": "first_of", "first_of": "first_of",
    "अन्त्यमा": "end_of", "अन्त्यको": "end_of", "अन्तमा": "end_of", "अन्तको": "end_of", "अन्तिममा": "end_of", "अन्तिमको": "end_of", "अन्तसम्म": "end_of",
    "late": "end_of", "close_of": "end_of", "end_of": "end_of",
    "अन्त्य": "end_of", "बीच": "middle_of", "मध्य": "middle_of", "बीचमा": "middle_of",
    "मध्यमा": "middle_of", "मध्यको": "middle_of", "मझेरीमा": "middle_of", "बीचको": "middle_of",
    "middle": "middle_of", "mid": "middle_of", "midpoint": "middle_of", "middle_of": "middle_of",
}

_ORDINALS = {
    "पहिलो": 1, "दोस्रो": 2, "तेस्रो": 3, "चौथो": 4,
    "पाँचौं": 5, "छैटौं": 6, "सातौं": 7, "आठौं": 8, "आठौ": 8,
    "नवौं": 9, "दशौं": 10, "एघारौं": 11, "बाह्रौं": 12,
    "तेह्रौं": 13, "चौधौं": 14, "पन्ध्रौं": 15, "सोह्रौं": 16, "सत्रौं": 17, "अठारौं": 18, "उन्नाइसौं": 19, "बीसौं": 20,
    "एक्काइसौं": 21, "बाइसौं": 22, "तेइसौं": 23, "चौबीसौं": 24, "पच्चीसौं": 25, "छब्बीसौं": 26,
    "सत्ताइसौं": 27, "अट्ठाइसौं": 28, "उनन्तीसौं": 29, "तीसौं": 30, "एकतीसौं": 31,
    "first": 1, "second": 2, "third": 3, "fourth": 4,
    "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12,
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6, "7th": 7, "8th": 8, "9th": 9, "10th": 10,
    "11th": 11, "12th": 12, "13th": 13, "14th": 14, "15th": 15, "16th": 16, "17th": 17, "18th": 18, "19th": 19, "20th": 20,
    "21st": 21, "22nd": 22, "23rd": 23, "24th": 24, "25th": 25, "26th": 26, "27th": 27, "28th": 28, "29th": 29, "30th": 30, "31st": 31,
}

_WORD_NUMBERS = {
    "एक": 1, "दुई": 2, "तीन": 3, "चार": 4, "पाँच": 5,
    "छ": 6, "सात": 7, "आठ": 8, "नौ": 9, "दश": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}

_POSTPOSITIONS = {
    "मा", "को", "सम्म", "देखि", "भित्र",
    "पछि", "अगाडि", "तिर", "बाट", "लाई", "ले",
    "in", "of", "to", "until", "till", "up to", "through", "from", "since", "as of", "within", "after", "before", "by", "between", "and"
}

_RANGE_BRIDGES = frozenset({
    "देखि", "सम्म", "बाट", "from", "to", "between", "and", "-",
    "until", "till", "through", "since", "as of"
})

_NON_TEMPORAL_RIGHT = {
    "वसुली", "असुली",
    "तोक्ने", "तोक्नु", "पर्ने", "पर्नु",
    "रुख", "काठ",
}

_RECURRENCE_WORDS = {
    "हरेक", "प्रत्येक", "every", "each",
}

_RELATIVE_ADVERBS = {
    "आज": "today", "aaja": "today", "today": "today",
    "हिजो": "yesterday", "hijo": "yesterday", "yesterday": "yesterday",
    "भोलि": "tomorrow", "bholi": "tomorrow", "tomorrow": "tomorrow",
    "परसि": "day_after_tomorrow", "parsi": "day_after_tomorrow", "पर्सि": "day_after_tomorrow",
    "day_after_tomorrow": "day_after_tomorrow",
    "अस्ति": "day_before_yesterday", "asti": "day_before_yesterday",
    "day_before_yesterday": "day_before_yesterday",
}

_DIRECTION_WORDS = {
    "अगाडि": -1, "अघि": -1, "पहिले": -1, "अघी": -1, "अगाडी": -1,
    "ago": -1, "back": -1, "before": -1, "earlier": -1,
    "पछि": +1, "पछाडि": +1, "पछी": +1,
    "after": +1, "later": +1,
}

_KEYWORD_TARIKH = {"तारिख", "tarikh", "मिति", "miti", "date"}
_KEYWORD_GATE = {"गते", "gate"}
_PUNCTUATIONS = {".", ",", "!", "?", ";", ":", "|", "।", "\n", "\t"}
