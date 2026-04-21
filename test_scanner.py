import unittest
import json
import os
import datetime
from wisedate.scanner import scan_text


class TestScannerRelativeAdverbs(unittest.TestCase):
    """
    Tests standalone temporal adverbs that are always temporal:
    आज, हिजो, भोलि, परसि, अस्ति and their romanized equivalents.
    """
    def setUp(self):
        self.ref_date = datetime.date(2026, 4, 9)

    def test_aaja_resolves_to_today(self):
        result = scan_text("आज बैठक छ", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "day")

    def test_hijo_resolves_to_yesterday(self):
        result = scan_text("हिजो बैठक भयो", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["text"], "हिजो")

    def test_bholi_resolves_to_tomorrow(self):
        result = scan_text("भोलि जाने हो", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["text"], "भोलि")

    def test_parsi_both_spellings(self):
        """Both परसि and पर्सि should resolve to day_after_tomorrow."""
        for spelling in ["परसि", "पर्सि"]:
            with self.subTest(spelling=spelling):
                result = scan_text(f"{spelling} आउनुस्", ref_date=self.ref_date)
                self.assertEqual(len(result.extractions), 1)
                self.assertEqual(result.extractions[0]["text"], spelling)

    def test_asti_resolves_to_day_before_yesterday(self):
        result = scan_text("अस्ति देखेको", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["text"], "अस्ति")

    def test_english_today(self):
        result = scan_text("today is the meeting", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["text"], "today")


class TestScannerModifierPlusUnit(unittest.TestCase):
    """
    Tests demonstrative/temporal modifiers combined with temporal units:
    यो हप्ता, गत महिना, अर्को वर्ष, etc.
    """
    def setUp(self):
        self.ref_date = datetime.date(2025, 4, 18)  # BS 2082-01-06

    def test_yo_hapta(self):
        result = scan_text("यो हप्ता काम छ", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "week")

    def test_gata_hapta(self):
        result = scan_text("गत हप्ता बैठक भयो", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "week")
        self.assertEqual(result.extractions[0]["text"], "गत हप्ता")

    def test_arko_mahina(self):
        result = scan_text("अर्को महिना फेरि हुन्छ", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "month")

    def test_gata_barsa(self):
        result = scan_text("गत वर्ष राम्रो भयो", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "year")

    def test_agglutinated_postposition(self):
        """'हप्तामा' should split into हप्ता + मा and still be recognized."""
        result = scan_text("यो हप्तामा काम छ", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "week")


class TestScannerOrdinalScoping(unittest.TestCase):
    """
    Tests ordinal + unit patterns within a scope:
    वर्षको पहिलो महिना, महिनाको अन्तिम दिन, etc.
    Supports up to 2-level nesting.
    """
    def setUp(self):
        self.ref_date = datetime.date(2025, 4, 18)  # BS 2082-01-06

    def test_first_month_of_year(self):
        result = scan_text("वर्षको पहिलो महिना मा मेरो बैठक छ", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        extraction = result.extractions[0]
        self.assertEqual(extraction["text"], "वर्षको पहिलो महिना")
        self.assertEqual(extraction["normalized"]["type"], "month")
        self.assertEqual(extraction["normalized"]["calendar"], "BS")
        self.assertEqual(extraction["normalized"]["year"], 2082)
        self.assertEqual(extraction["normalized"]["month"], 1)

    def test_normalized_text_replacement(self):
        result = scan_text("वर्षको पहिलो महिना मा मेरो बैठक छ", ref_date=self.ref_date)
        self.assertIn("२०८२-०१", result.normalized_text)
        self.assertIn("मा मेरो बैठक छ", result.normalized_text)


class TestScannerDirectionalOffset(unittest.TestCase):
    """
    Tests number + unit + direction patterns:
    ३ दिन अगाडि, 5 weeks later, etc.
    """
    def setUp(self):
        self.ref_date = datetime.date(2025, 4, 18)  # BS 2082-01-06

    def test_three_days_ago_nepali(self):
        result = scan_text("३ दिन अगाडि", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        extraction = result.extractions[0]
        self.assertEqual(extraction["normalized"]["type"], "day")
        self.assertEqual(extraction["normalized"]["calendar"], "BS")

    def test_three_days_ago_english(self):
        result = scan_text("3 days ago", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        extraction = result.extractions[0]
        self.assertEqual(extraction["normalized"]["type"], "day")

    def test_five_weeks_later(self):
        result = scan_text("5 weeks later", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "day")

    def test_devanagari_script_mirroring(self):
        """Devanagari input should produce Devanagari numerals in the normalized output."""
        result = scan_text("३ दिन अगाडि", ref_date=self.ref_date)
        for char in result.normalized_text:
            if '0' <= char <= '9':
                self.fail(f"Found Latin digit '{char}' in Devanagari-input output: {result.normalized_text}")

    def test_english_script_mirroring(self):
        """English input should produce Latin numerals in the normalized output."""
        result = scan_text("3 days ago", ref_date=self.ref_date)
        for char in result.normalized_text:
            if "\u0966" <= char <= "\u096F":
                self.fail(f"Found Devanagari digit '{char}' in English-input output: {result.normalized_text}")


class TestScannerDisambiguation(unittest.TestCase):
    """
    Tests that non-temporal uses of ambiguous words are correctly rejected:
    हप्ता वसुली, तारिख तोक्ने, साल रुख, etc.
    """
    def setUp(self):
        self.ref_date = datetime.date(2025, 4, 18)

    def test_hapta_wasuli_blocked(self):
        """'हप्ता वसुली' is extortion, NOT a week reference."""
        result = scan_text("यो हप्ता वसुली गर्ने", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 0)
        self.assertEqual(result.normalized_text, "यो हप्ता वसुली गर्ने")

    def test_tarikh_tokne_blocked(self):
        """'तारिख तोक्ने' is setting a court date, NOT a date reference."""
        result = scan_text("आजको तारिख तोक्ने", ref_date=self.ref_date)
        # आज should still be extracted, but तारिख तोक्ने should NOT
        # The exact behavior depends on FSM — आज triggers first, 
        # तारिख तोक्ने is a separate expression that gets blocked.
        for extraction in result.extractions:
            self.assertNotIn("तोक्ने", extraction["text"])

    def test_recurrence_skipped(self):
        """'हरेक हप्ता' (every week) cannot resolve to a specific date — skip."""
        result = scan_text("हरेक हप्ता जाने", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 0)

    def test_plain_text_passthrough(self):
        """Text with no temporal content should pass through completely unchanged."""
        text = "नमस्कार, कस्तो छ?"
        result = scan_text(text, ref_date=self.ref_date)
        self.assertEqual(result.normalized_text, text)
        self.assertEqual(len(result.extractions), 0)


class TestScannerCalendarDetection(unittest.TestCase):
    """
    Tests the calendar detection logic:
    BS by default, AD when तारिख is present.
    """
    def setUp(self):
        self.ref_date = datetime.date(2026, 4, 9)

    def test_tarikh_triggers_ad(self):
        """'आजको तारिख' should output Gregorian (AD) dates."""
        result = scan_text("आजको तारिख सम्ममा बुझाउने", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["calendar"], "AD")
        self.assertEqual(result.extractions[0]["normalized"]["year"], 2026)
        self.assertEqual(result.extractions[0]["normalized"]["month"], 4)

    def test_end_of_month_tarikh(self):
        """'यो महिनाको अन्त्य तारिखसम्म' should resolve to last day of current AD month."""
        result = scan_text("मेरो account renew gardinus यो महिनाको अन्त्य तारिखसम्म मा", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        extraction = result.extractions[0]
        self.assertEqual(extraction["normalized"]["calendar"], "AD")
        self.assertEqual(extraction["normalized"]["day"], 30)

    def test_default_calendar_is_bs(self):
        """Without तारिख, calendar should default to BS."""
        result = scan_text("यो महिना काम छ", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["calendar"], "BS")


class TestScannerMultiExtraction(unittest.TestCase):
    """
    Tests that multiple date expressions in one sentence are all extracted.
    """
    def setUp(self):
        self.ref_date = datetime.date(2025, 4, 18)

    def test_two_extractions(self):
        result = scan_text("गत हप्ता बैठक भयो र अर्को महिना फेरि हुन्छ", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 2)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "week")
        self.assertEqual(result.extractions[1]["normalized"]["type"], "month")

    def test_three_adverbs(self):
        result = scan_text("हिजो आयो आज गयो भोलि आउँछ", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 3)


class TestScannerRefDate(unittest.TestCase):
    """
    Tests that the ref_date parameter works with different input types:
    datetime.date, ISO string, and None (defaults to today).
    """
    def test_ref_date_as_iso_string(self):
        result = scan_text("आज", ref_date="2026-04-09")
        self.assertEqual(len(result.extractions), 1)

    def test_ref_date_as_datetime(self):
        result = scan_text("आज", ref_date=datetime.date(2026, 4, 9))
        self.assertEqual(len(result.extractions), 1)

    def test_ref_date_defaults_to_today(self):
        result = scan_text("आज")
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "day")


class TestScannerJSONL(unittest.TestCase):
    """
    Data-driven tests loaded from scanner_cases.jsonl.
    Each line defines an input, ref_date, expected normalized text,
    and expected extraction fields.
    """
    def test_scanner_from_jsonl(self):
        jsonl_path = os.path.join(os.path.dirname(__file__), "scanner_cases.jsonl")
        with open(jsonl_path, "r", encoding="utf-8") as f:
            cases = [json.loads(line) for line in f if line.strip()]
        for case_index, case in enumerate(cases):
            with self.subTest(case_index=case_index, input_text=case["input"]):
                result = scan_text(case["input"], ref_date=case["ref_date"])
                self._assert_normalized(result, case)
                self._assert_extractions(result, case)
    def _assert_normalized(self, result, case):
        """Assert normalized text matches expected."""
        self.assertEqual(
            result.normalized_text,
            case["expected_normalized"],
            f"Normalized text mismatch for: '{case['input']}'"
        )
    def _assert_extractions(self, result, case):
        """Assert extraction count and fields match expected."""
        expected = case["expected_extractions"]
        self.assertEqual(
            len(result.extractions),
            len(expected),
            f"Extraction count mismatch for: '{case['input']}'"
        )
        for idx, expected_ext in enumerate(expected):
            actual = result.extractions[idx]
            self.assertEqual(
                actual["text"],
                expected_ext["text"],
                f"Text mismatch at index {idx} for: '{case['input']}'"
            )
            for field, value in expected_ext.items():
                if field == "text":
                    continue
                self.assertEqual(
                    actual.get(field), value,
                    f"Field '{field}' mismatch at extraction {idx} for: '{case['input']}'"
                )


class TestScannerVocabularyExpansion(unittest.TestCase):
    """
    Tests for expanded vocabulary: Shrawan variations, AD month Devanagari names,
    Fiscal Year, and new temporal units.
    """
    def setUp(self):
        # BS 2082-01-06 (Baisakh 6)
        self.ref_date = datetime.date(2025, 4, 18)

    def test_shrawan_variations(self):
        """श्रावन and साऊन should resolve to month 4 (Shrawan)."""
        for month_name in ["श्रावन", "साऊन", "shrawn"]:
            with self.subTest(month_name=month_name):
                result = scan_text(f"{month_name} मा", ref_date=self.ref_date)
                self.assertEqual(len(result.extractions), 1, f"Failed for {month_name}")
                self.assertEqual(result.extractions[0]["normalized"]["month"], 4)

    def test_ad_month_devanagari(self):
        """जानवरी should resolve to January (AD 1)."""
        result = scan_text("जानवरी १ तारिख", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["calendar"], "AD")
        self.assertEqual(result.extractions[0]["normalized"]["month"], 1)

    def test_fiscal_year_resolution(self):
        """यो आर्थिक वर्ष should resolve to the current Nepali Fiscal Year."""
        # Today is BS 2082-01-06.
        # FY started in Shrawan 2081 and ends in Ashadh 2082.
        result = scan_text("यो आर्थिक वर्ष", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        extraction = result.extractions[0]
        self.assertEqual(extraction["normalized"]["type"], "fiscal_year")
        self.assertEqual(extraction["normalized"]["calendar"], "BS")
        self.assertEqual(extraction["normalized"]["start"], "2081-04-01")
        # End of Ashadh 2082 is 32 according to _BS_YEAR_DATA
        self.assertEqual(extraction["normalized"]["end"], "2082-03-32")

    def test_gatey_unit(self):
        """५ gatey should be recognized as a day extraction."""
        result = scan_text("५ gatey", ref_date=self.ref_date)
        self.assertEqual(len(result.extractions), 1)
        self.assertEqual(result.extractions[0]["normalized"]["type"], "day")


if __name__ == '__main__':
    unittest.main(verbosity=2)
