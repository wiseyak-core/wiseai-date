import unittest
import datetime
from wisedate.nepali_date import (
    bs_to_ad, ad_to_bs, NepaliDateTime, make_iterator, nepali_range, bs_month_calendar,
    to_devanagari_numeral, from_devanagari_numeral, _BS_MONTH_NAMES, _BS_MONTH_NAMES_DEVANAGARI,
    _BS_WEEKDAY_NAMES, _BS_WEEKDAY_NAMES_DEVANAGARI, month_name_to_devanagari,
    month_name_from_devanagari, weekday_name_to_devanagari, weekday_name_from_devanagari,
    DateRange, ad_year_to_bs_range, bs_year_to_ad_range, bs_month_to_ad_range,
    ad_month_to_bs_range, bs_quarter_to_ad_range, ad_quarter_to_bs_range,
    bs_half_to_ad_range, ad_half_to_bs_range, current_bs_year, group_dates,
    _BS_YEAR_DATA, _BS_MIN_YEAR, _BS_MAX_YEAR
)

class TestCalendarDays(unittest.TestCase):
    def test_cumulative_days_bs_vs_ad(self):
        """
        Calculates cumulative days from 1970 BS up to each year,
        and ensures it matches the exact AD date offset.
        """
        cumulative_bs_days = 0
        ad_start_1970 = bs_to_ad(1970, 1, 1)
        
        for year in range(_BS_MIN_YEAR, _BS_MAX_YEAR + 1):
            with self.subTest(year=year):
                month_days = _BS_YEAR_DATA[year]
                yearly_bs_days = sum(month_days)
                
                ad_end = bs_to_ad(year, 12, month_days[-1])
                cumulative_bs_days += yearly_bs_days
                cumulative_ad_days = (ad_end - ad_start_1970).days + 1
                
                self.assertEqual(
                    cumulative_bs_days, 
                    cumulative_ad_days, 
                    f"Cumulative total mismatch at BS year {year}: BS={cumulative_bs_days}, AD={cumulative_ad_days}"
                )
    
    def test_yearly_days_bs_vs_ad(self):
        """
        Verifies that each individual BS year's total days
        equals the AD duration of that year.
        """
        for year in range(_BS_MIN_YEAR, _BS_MAX_YEAR + 1):
            with self.subTest(year=year):
                month_days = _BS_YEAR_DATA[year]
                yearly_bs_days = sum(month_days)
                
                ad_start = bs_to_ad(year, 1, 1)
                ad_end = bs_to_ad(year, 12, month_days[-1])
                
                yearly_ad_days = (ad_end - ad_start).days + 1
                
                self.assertEqual(
                    yearly_bs_days, 
                    yearly_ad_days,
                    f"Yearly mismatch at BS year {year}: BS={yearly_bs_days}, AD={yearly_ad_days}"
                )


class TestMainDemos(unittest.TestCase):
    """
    Test suite containing all scenarios from main.py's demo run.
    """
    def test_bs_to_ad_conversion(self):
        self.assertEqual(bs_to_ad(2081, 1, 1), datetime.date(2024, 4, 13))
        self.assertEqual(bs_to_ad(2080, 12, 30), datetime.date(2024, 4, 12))
        self.assertEqual(bs_to_ad(2000, 6, 15), datetime.date(1943, 10, 1))

    def test_ad_to_bs_conversion(self):
        self.assertEqual(ad_to_bs(datetime.date(2024, 4, 12)), (2080, 12, 30))
        self.assertEqual(ad_to_bs(datetime.date(1981, 3, 31)), (2037, 12, 18))
        self.assertEqual(ad_to_bs(datetime.date(1969, 12, 31)), (2026, 9, 16))

    def test_round_trip(self):
        test_dates = [(2037, 12, 19), (2081, 1, 1), (1980, 5, 20)]
        for test_bs in test_dates:
            with self.subTest(date=test_bs):
                ad_rt = bs_to_ad(*test_bs)
                bs_rt = ad_to_bs(ad_rt)
                self.assertEqual(bs_rt, test_bs)

    def test_nepali_datetime_properties(self):
        ndt = NepaliDateTime.from_bs(2081, 4, 15, 10, 30, 45, 500)
        self.assertEqual(ndt.dt.date(), datetime.date(2024, 7, 30))
        self.assertEqual(ndt.bs_month_name, "Shrawan")
        self.assertEqual(ndt.bs_weekday_name, "Mangalbar")

    def test_iterators(self):
        # Day
        it = make_iterator("day", NepaliDateTime.from_bs(2081, 1, 1), count=7)
        days = list(it)
        self.assertEqual(len(days), 7)
        self.assertEqual(days[0].bs_day, 1)
        self.assertEqual(days[-1].bs_day, 7)

        # Month
        it = make_iterator("month", NepaliDateTime.from_bs(2081, 1, 1), count=6)
        months = list(it)
        self.assertEqual(len(months), 6)
        self.assertEqual(months[-1].bs_month, 6)

        # Hour
        it = make_iterator("hour", NepaliDateTime.from_bs(2081, 6, 10, 8, 0, 0, 0), count=6)
        hours = list(it)
        self.assertEqual(len(hours), 6)
        self.assertEqual(hours[-1].dt.hour, 13)

        # Millisecond
        it = make_iterator("millisecond", NepaliDateTime.from_bs(2081, 6, 10, 12, 0, 0, 0), count=5)
        ticks = list(it)
        self.assertEqual(len(ticks), 5)
        self.assertEqual(ticks[-1].dt.microsecond, 4000)

    def test_nepali_range(self):
        start = NepaliDateTime.from_bs(2081, 9, 1)
        stop  = NepaliDateTime.from_bs(2081, 9, 6)
        days = list(nepali_range(start, stop, granularity="day"))
        self.assertEqual(len(days), 5)

    def test_bs_month_calendar(self):
        grid = bs_month_calendar(2081, 1)
        self.assertTrue(len(grid) >= 4)  # usually 4-6 weeks
        
        flat_days = [d for week in grid for d in week if d is not None]
        self.assertEqual(len(flat_days), 31) # 2081 Baisakh has 31 days

    def test_devanagari_conversions(self):
        self.assertEqual(to_devanagari_numeral(15), "१५")
        self.assertEqual(to_devanagari_numeral(2081), "२०८१")
        self.assertEqual(from_devanagari_numeral("२०८१"), 2081)

    def test_bidirectional_names(self):
        self.assertEqual(month_name_to_devanagari("Baisakh"), "बैशाख")
        self.assertEqual(month_name_from_devanagari("बैशाख"), "Baisakh")
        self.assertEqual(weekday_name_to_devanagari("Sombar"), "सोमबार")
        self.assertEqual(weekday_name_from_devanagari("सोमबार"), "Sombar")

    def test_partial_range_endpoints(self):
        ad_year_rng = ad_year_to_bs_range(2025)
        self.assertEqual(ad_year_rng.start_ad, datetime.date(2025, 1, 1))
        self.assertEqual(ad_year_rng.end_ad, datetime.date(2025, 12, 31))

        bs_month_rng = bs_month_to_ad_range('Shrawan', 2082)
        self.assertEqual(bs_month_rng.start_bs, (2082, 4, 1))

class TestDateGrouping(unittest.TestCase):
    def setUp(self):
        # We fix the reference date to a specific point for deterministic tests
        self.ref_date = datetime.date(2026, 4, 7) # Which is BS 2082-12-24
        
    def test_group_dates_by_ad_month(self):
        # Mixed AD and BS inputs
        dates = [
            datetime.date(2026, 1, 15),
            datetime.date(2026, 1, 20),
            datetime.date(2026, 2, 10),
            NepaliDateTime.from_bs(2082, 11, 25), # This falls in March 2026 usually
        ]
        res = group_dates(dates, by="month", calendar="AD")
        
        self.assertIn("AD January 2026", res)
        self.assertEqual(len(res["AD January 2026"]), 2)
        self.assertIn("AD February 2026", res)
        self.assertEqual(len(res["AD February 2026"]), 1)

    def test_group_dates_by_relative_phrases(self):
        dates = [
            datetime.date(2026, 4, 7), # today
            datetime.date(2026, 4, 6), # yesterday
            datetime.date(2026, 4, 5), # day before yesterday
            datetime.date(2026, 3, 20), # last month roughly
        ]
        
        phrases = ["today", "yesterday", "this_week"]
        res = group_dates(dates, by=phrases, ref_date=self.ref_date)
        
        self.assertIn("Today", res)
        self.assertEqual(res["Today"][0], datetime.date(2026, 4, 7))
        self.assertIn("Yesterday", res)
        self.assertEqual(res["Yesterday"][0], datetime.date(2026, 4, 6))

    def test_group_dates_by_bs_month(self):
        # Mixed AD and BS inputs for a BS Month bucket
        dates = [
            NepaliDateTime.from_bs(2082, 12, 15),
            NepaliDateTime.from_bs(2082, 12, 20),
            datetime.date(2026, 4, 1), # Falls in Chaitra 2082
        ]
        res = group_dates(dates, by="month", calendar="BS")

        self.assertIn("BS Chaitra 2082", res)
        self.assertEqual(len(res["BS Chaitra 2082"]), 3)

class TestExtensiveRangesAndGrouping(unittest.TestCase):
    def test_bs_year_to_ad_range(self):
        rng = bs_year_to_ad_range(2082)
        self.assertEqual(rng.start_ad, bs_to_ad(2082, 1, 1))
        self.assertEqual(rng.end_ad, bs_to_ad(2082, 12, _BS_YEAR_DATA[2082][11]))

    def test_ad_year_to_bs_range(self):
        rng = ad_year_to_bs_range(2025)
        self.assertEqual(rng.start_ad, datetime.date(2025, 1, 1))
        self.assertEqual(rng.end_ad, datetime.date(2025, 12, 31))

    def test_bs_month_to_ad_range(self):
        rng = bs_month_to_ad_range(1, 2082)
        self.assertEqual(rng.start_ad, bs_to_ad(2082, 1, 1))
        self.assertEqual(rng.end_ad, bs_to_ad(2082, 1, _BS_YEAR_DATA[2082][0]))

    def test_ad_month_to_bs_range(self):
        rng = ad_month_to_bs_range(4, 2026)
        self.assertEqual(rng.start_ad, datetime.date(2026, 4, 1))
        self.assertEqual(rng.end_ad, datetime.date(2026, 4, 30))

    def test_quarter_and_half_ranges(self):
        ad_q1 = ad_quarter_to_bs_range(1, 2026)
        self.assertEqual(ad_q1.start_ad, datetime.date(2026, 1, 1))
        self.assertEqual(ad_q1.end_ad, datetime.date(2026, 3, 31))

        bs_q1 = bs_quarter_to_ad_range(1, 2082)
        self.assertEqual(bs_q1.start_bs, (2082, 1, 1))
        self.assertEqual(bs_q1.end_bs, (2082, 3, _BS_YEAR_DATA[2082][2]))

        ad_h1 = ad_half_to_bs_range(1, 2026)
        self.assertEqual(ad_h1.start_ad, datetime.date(2026, 1, 1))
        self.assertEqual(ad_h1.end_ad, datetime.date(2026, 6, 30))

        bs_h2 = bs_half_to_ad_range(2, 2082)
        self.assertEqual(bs_h2.start_bs, (2082, 7, 1))
        self.assertEqual(bs_h2.end_bs, (2082, 12, _BS_YEAR_DATA[2082][11]))

    def test_current_bs_year(self):
        yr = current_bs_year()
        self.assertIsInstance(yr, int)
        self.assertGreaterEqual(yr, 2080)

    def test_nepali_relative_phrases(self):
        ref_date = datetime.date(2026, 4, 7) # BS 2082-12-24
        dates = [
            datetime.date(2026, 4, 7), # 'aaja'
            datetime.date(2026, 4, 6), # 'hijo' / 'हिजो'
            datetime.date(2026, 4, 8), # 'bholi'
            datetime.date(2026, 4, 1), # previous week/this month 
        ]
        
        phrases = ['aaja', 'हिजो', 'bholi', 'यो_हप्ता'] # Romanized + Devanagari test
        res = group_dates(dates, by=phrases, ref_date=ref_date, calendar="BS")
        
        self.assertIn("Today", res)
        self.assertEqual(res["Today"][0], datetime.date(2026, 4, 7))
        self.assertIn("Yesterday", res)
        self.assertEqual(res["Yesterday"][0], datetime.date(2026, 4, 6))
        self.assertIn("Tomorrow", res)
        self.assertEqual(res["Tomorrow"][0], datetime.date(2026, 4, 8))
        self.assertIn("This Week", res)

class TestDateGroupingJSONL(unittest.TestCase):
    def test_grouping_from_jsonl(self):
        import json
        import os
        jsonl_path = os.path.join(os.path.dirname(__file__), "test_cases.jsonl")
        
        with open(jsonl_path, "r", encoding="utf-8") as f:
            cases = [json.loads(line) for line in f if line.strip()]
        
        # We fix the reference date so "today" and "yesterday" are predictable
        ref_date = datetime.date(2026, 4, 7)

        for case in cases:
            # Run the algorithm directly on the raw strings (the engine parses them)
            # or pre-convert AD iso dates if calendar is AD
            calendar = case.get("calendar", "AD")
            
            if calendar == "AD":
                dates = [datetime.date.fromisoformat(d) for d in case['input_dates']]
            else:
                # Pass strings directly so the core library's `_normalize_input` uses NepaliDateTime.parse
                dates = case['input_dates']
            
            result = group_dates(dates, by=case['by'], calendar=calendar, ref_date=ref_date)

            # Assert the keys exist
            for key in case['expected_keys']:
                self.assertIn(key, result)
                
            # Assert the counts match
            for key, expected_count in case['expected_counts'].items():
                val = len(result.get(key, []))
                try:
                    self.assertEqual(val, expected_count)
                except AssertionError as e:
                    print(f"FAILED case input: {case['input_dates']} result keys: {result.keys()} trying to find key {key}")
                    raise e

if __name__ == '__main__':
    unittest.main(verbosity=2)

