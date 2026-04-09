import datetime
from library.nepali_date import (
    bs_to_ad,
    ad_to_bs,
    NepaliDateTime,
    make_iterator,
    nepali_range,
    bs_month_calendar,
    to_devanagari_numeral,
    from_devanagari_numeral,
    _BS_MONTH_NAMES,
    _BS_MONTH_NAMES_DEVANAGARI,
    _BS_WEEKDAY_NAMES,
    _BS_WEEKDAY_NAMES_DEVANAGARI,
    month_name_to_devanagari,
    month_name_from_devanagari,
    weekday_name_to_devanagari,
    weekday_name_from_devanagari,
    normalize_month_name,
    normalize_ad_month,
    normalize_weekday,
    # Partial date range converters
    DateRange,
    ad_year_to_bs_range,
    bs_year_to_ad_range,
    bs_month_to_ad_range,
    ad_month_to_bs_range,
    bs_quarter_to_ad_range,
    ad_quarter_to_bs_range,
    bs_half_to_ad_range,
    ad_half_to_bs_range,
    current_bs_year,
)

# ---------------------------------------------------------------------------
# SELF-TEST / DEMO
# ---------------------------------------------------------------------------

def _demo() -> None:
    SEP = "─" * 62

    print(SEP)
    print("  Nepali Date Library — Demo")
    print(SEP)

    # 1. BS → AD
    print("\n[1] BS → AD conversion")
    samples_bs = [
        (2081,  1,  1),   # BS New Year 2081
        (2080, 12, 30),   # last day of 2080
        (2000,  6, 15),
    ]
    for y, m, d in samples_bs:
        ad = bs_to_ad(y, m, d)
        print(f"  BS {y}-{m:02d}-{d:02d}  →  AD {ad}")

    # 2. AD → BS
    print("\n[2] AD → BS conversion")
    samples_ad = [
        datetime.date(2024, 4, 13),   # expected → BS 2081-01-01 (Baisakh) ✓
        datetime.date(1981, 4,  1),   # expected → BS 2037-12-19 (Chaitra) ✓
        datetime.date(1970, 1,  1),
    ]
    for ad in samples_ad:
        y, m, d = ad_to_bs(ad)
        print(f"  AD {ad}  →  BS {y}-{m:02d}-{d:02d}  ({_BS_MONTH_NAMES[m]})")

    # 3. Round-trip
    print("\n[3] Round-trip BS→AD→BS")
    test = (2037, 12, 19)
    ad_rt = bs_to_ad(*test)
    bs_rt = ad_to_bs(ad_rt)
    ok    = bs_rt == test
    print(f"  Original BS: {test}  →  AD: {ad_rt}  →  BS: {bs_rt}  {'✓' if ok else '✗'}")

    # 4. NepaliDateTime
    print("\n[4] NepaliDateTime")
    ndt = NepaliDateTime.from_bs(2081, 4, 15, 10, 30, 45, 500)
    print(f"  {ndt}")
    print(f"  Month name : {ndt.bs_month_name}")
    print(f"  Weekday    : {ndt.bs_weekday_name}")
    print(f"  Days/month : {ndt.bs_days_in_month()}")

    # 5. Day iterator (first 7 days of BS 2081 Baisakh)
    print("\n[5] Day iterator — first 7 days of BS 2081 Baisakh")
    it = make_iterator("day", NepaliDateTime.from_bs(2081, 1, 1), count=7)
    for ndt in it:
        print(f"  {ndt.isoformat_bs()}  ({ndt.bs_weekday_name})")

    # 6. Month iterator
    print("\n[6] Month iterator — 6 months starting BS 2081-01-01")
    it = make_iterator("month", NepaliDateTime.from_bs(2081, 1, 1), count=6)
    for ndt in it:
        print(f"  BS {ndt.bs_year}-{ndt.bs_month:02d}  ({ndt.bs_month_name})"
              f"  → AD {ndt.dt.date()}")

    # 7. Hour iterator — 6 hours
    print("\n[7] Hour iterator — 6 hours from BS 2081-06-10 08:00:00.000")
    it = make_iterator("hour",
                       NepaliDateTime.from_bs(2081, 6, 10, 8, 0, 0, 0),
                       count=6)
    for ndt in it:
        print(f"  {ndt.isoformat_bs()}")

    # 8. Millisecond iterator — 5 ticks
    print("\n[8] Millisecond iterator — 5 ms from BS 2081-06-10 12:00:00.000")
    it = make_iterator("millisecond",
                       NepaliDateTime.from_bs(2081, 6, 10, 12, 0, 0, 0),
                       count=5)
    for ndt in it:
        print(f"  {ndt.isoformat_bs()}")

    # 9. Range with stop
    print("\n[9] Day range with explicit stop")
    start = NepaliDateTime.from_bs(2081, 9, 1)
    stop  = NepaliDateTime.from_bs(2081, 9, 6)
    days  = list(nepali_range(start, stop, granularity="day"))
    print(f"  {[ndt.isoformat_bs() for ndt in days]}")

    # 10. BS calendar grid
    print("\n[10] BS Calendar — Baisakh 2081")
    grid = bs_month_calendar(2081, 1)
    header = "  Mon  Tue  Wed  Thu  Fri  Sat  Sun"
    print(f"  {_BS_MONTH_NAMES[1]} 2081")
    print(header)
    for week in grid:
        row = "".join(
            f"{'':>5}" if d is None else f"{d:>5}"
            for d in week
        )
        print(row)

    # 11. Devanagari digit / numeral conversion
    print("\n[11] Devanagari numeral conversion")
    for n in [0, 1, 9, 15, 2081, 20810101]:
        print(f"  {n:>10}  →  {to_devanagari_numeral(n)}"
              f"  →  {from_devanagari_numeral(to_devanagari_numeral(n))}")

    # 12. Full Devanagari month + weekday name mapping table
    print("\n[12] BS month name mapping (Latin ↔ Devanagari)")
    print(f"  {'No':>3}  {'Latin':<12}  {'Devanagari'}")
    print(f"  {'─'*3}  {'─'*12}  {'─'*12}")
    for i in range(1, 13):
        print(f"  {i:>3}  {_BS_MONTH_NAMES[i]:<12}  {_BS_MONTH_NAMES_DEVANAGARI[i]}")

    print("\n[13] BS weekday name mapping (Latin ↔ Devanagari)")
    print(f"  {'No':>3}  {'Latin':<12}  {'Devanagari'}")
    print(f"  {'─'*3}  {'─'*12}  {'─'*14}")
    for i in range(7):
        print(f"  {i:>3}  {_BS_WEEKDAY_NAMES[i]:<12}  {_BS_WEEKDAY_NAMES_DEVANAGARI[i]}")

    # 14. NepaliDateTime Devanagari properties
    print("\n[14] NepaliDateTime — Devanagari properties")
    ndt2 = NepaliDateTime.from_bs(2081, 4, 15, 10, 30, 45, 500)
    print(f"  Latin  : {ndt2.format_bs(devanagari=False)}")
    print(f"  Deva   : {ndt2.format_bs(devanagari=True)}")
    print(f"  Year   : {ndt2.bs_year}  →  {ndt2.bs_year_devanagari}")
    print(f"  Month# : {ndt2.bs_month:02d}  →  {ndt2.bs_month_devanagari}")
    print(f"  Day#   : {ndt2.bs_day:02d}  →  {ndt2.bs_day_devanagari}")
    print(f"  Month  : {ndt2.bs_month_name}  →  {ndt2.bs_month_name_devanagari}")
    print(f"  Weekday: {ndt2.bs_weekday_name}  →  {ndt2.bs_weekday_name_devanagari}")
    print(f"  ISO-BS : {ndt2.isoformat_bs()}")
    print(f"  ISO-dev: {ndt2.isoformat_bs_devanagari()}")

    # 15. Bidirectional name lookups
    print("\n[15] Bidirectional name lookups")
    for lat in ["Baisakh", "Shrawan", "Chaitra"]:
        dv = month_name_to_devanagari(lat)
        back = month_name_from_devanagari(dv)
        print(f"  {lat:<10} → {dv}  → {back}")
    for lat_w in ["Sombar", "Sukrabar", "Aaitabar"]:
        dv_w = weekday_name_to_devanagari(lat_w)
        back_w = weekday_name_from_devanagari(dv_w)
        print(f"  {lat_w:<12} → {dv_w}  → {back_w}")

    # 16. Day iterator with Devanagari display
    print("\n[16] Day iterator — first 5 days of BS 2081 with Devanagari")
    it2 = make_iterator("day", NepaliDateTime.from_bs(2081, 1, 1), count=5)
    for ndt in it2:
        print(f"  {ndt.isoformat_bs_devanagari()}  {ndt.bs_weekday_name_devanagari}")

    print(f"\n{SEP}")
    print("  All demos complete.")
    print(SEP)

    # 17. Partial date range conversions
    print(f"\n{SEP}")
    print("  [17] Partial Date Range Conversions")
    print(SEP)

    print("\n--- Year ranges ---")
    r = ad_year_to_bs_range(2025)
    print(f"  AD 2025 year →")
    print(r)

    r = bs_year_to_ad_range(2082)
    print(f"\n  BS 2082 year →")
    print(r)

    print("\n--- Month ranges ---")
    r = bs_month_to_ad_range('Shrawan', 2082)
    print(f"  BS Shrawan 2082 →")
    print(r)

    r = ad_month_to_bs_range('January', 2026)
    print(f"\n  AD January 2026 →")
    print(r)

    r = bs_month_to_ad_range('Poush', 2081)
    print(f"\n  BS Poush 2081 (name variant: 'Push') →")
    print(bs_month_to_ad_range('Push', 2081))

    print("\n--- Quarter ranges ---")
    r = bs_quarter_to_ad_range(1, 2082)
    print(f"  BS Q1 2082 →")
    print(r)

    r = ad_quarter_to_bs_range(2, 2025)
    print(f"\n  AD Q2 2025 →")
    print(r)

    print("\n--- Half-year ranges ---")
    r = bs_half_to_ad_range(1, 2082)
    print(f"  BS H1 2082 →")
    print(r)

    r = ad_half_to_bs_range('second', 2025)
    print(f"\n  AD H2 2025 →")
    print(r)

    print(f"\n  Current BS year: {current_bs_year()}")
    r = bs_month_to_ad_range('Baisakh')   # no year → uses current BS year
    print(f"  Baisakh (current BS year) →")
    print(r)

    print(f"\n{SEP}")
    print("  All demos complete.")
    print(SEP)


if __name__ == "__main__":
    _demo()
