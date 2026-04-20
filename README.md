# Nepali Date Library: WiseYak

This library provides `conversions` and `operations` with `iterators` between Bikram Sambat (BS) and Gregorian (AD) dates. At its core is the `NepaliDateTime` class, a powerful, Java `LocalDateTime`-inspired API for working with Nepali dates and times.

## Installation

You can install the library directly from PyPI:

```bash
pip install wiseai-date

# Or with uv (recommended for speed)
uv pip install wiseai-date
```

### Installing from Source (GitHub)
If you need the latest development version:

```bash
# Via HTTPS
pip install git+https://github.com/wiseyak-core/wiseai-date.git

# Via SSH (if you have keys configured)
pip install git+ssh://git@github.com/wiseyak-core/wiseai-date.git
```

### Adding as a Project Dependency

**pyproject.toml (PEP 621):**

```toml
[project]
dependencies = [
    "wiseai-date",
]
```

**requirements.txt:**

```
wiseai-date
```

### Installing Inside Docker

Since this is now a public package, you can install it normally in your `Dockerfile`:

```dockerfile
# No special SSH forwarding required
RUN pip install wiseai-date
```

## `NepaliDateTime`

The `NepaliDateTime` class is a wrapper that internally stores a standard Python UTC/naive `datetime` object, but exposes properties and methods to easily manipulate and display dates in the Bikram Sambat calendar system.

### Key Features

- **Java-style API**: Features methods like `of()`, `now()`, `plus()`, `minus()`, `getYear()`, and `withDayOfMonth()`, mirroring `java.time.LocalDateTime`.
- **Devanagari Support**: Built-in methods to easily access Devanagari numerals, month names, and weekday names natively.
- **Robust Parsing & Output**: Supports formatting and parsing ISO-style timestamps for BS dates.
- **Flexible Constructors**: Create dates from AD, from BS, or from a parsed string.

### Examples

**1. Creating a `NepaliDateTime` Object**

```python
from wisedate.nepali_date import NepaliDateTime

# Current date and time
now = NepaliDateTime.now()

# From BS components (year, month, day, hour, minute, second, ms)
ndt = NepaliDateTime.from_bs(2081, 4, 15, 10, 30, 45)

# Using the Java-style 'of' method (supports month names)
ndt_named = NepaliDateTime.of(2081, 'Shrawan', 15)

# Parse from an ISO 8601-like string
parsed = NepaliDateTime.parse("2081-04-15T10:30:45.500")
```

**2. Accessing Date Properties**

```python
ndt = NepaliDateTime.from_bs(2081, 1, 1) # Baisakh 1, 2081

# Basic attributes
print(ndt.bs_year)           # 2081
print(ndt.bs_month)          # 1

# Latin/Romanized names
print(ndt.bs_month_name)     # "Baisakh"
print(ndt.bs_weekday_name)   # E.g. "Sombar"

# Devanagari translation
print(ndt.bs_month_name_devanagari)   # "बैशाख"
print(ndt.bs_year_devanagari)         # "२०८१"
```

**3. Modification and Arithmetic**

```python
# Add or subtract time elements
future = ndt.plus(years=1, months=2, days=5, hours=10)
past = ndt.minus(days=15)

# Update specific fields (creates a new immutable instance)
modified = ndt.with_(year=2082, month='Baisakh')
modified2 = ndt.withYear(2085).withMonth('Chaitra')
```

**4. String Representation and Formatting**

```python
# Format dates naturally
print(ndt.format_bs())                # "BS 2081-01-01 (Sombar, Baisakh)"
print(ndt.format_bs(deva=True))       # Uses Devanagari values

# Standardized ISO Output
print(ndt.isoformat_bs())             # "2081-01-01T00:00:00.000"
print(ndt.isoformat_bs_devanagari())  # "२०८१-०१-०१T००:००:००.०००"
```

## Iterators and Ranges

The library provides powerful iterators to walk backward or forward through time at various granularities (e.g., `'day'`, `'month'`, `'year'`, `'hour'`, `'minute'`).

### Using `make_iterator`

`make_iterator` provides an easy-to-use iterable across a specific granularity.

```python
from wisedate.nepali_date import make_iterator, NepaliDateTime

start_date = NepaliDateTime.from_bs(2081, 1, 1)

# Iterate day-by-day for 7 days
day_it = make_iterator("day", start_date, count=7)
for ndt in day_it:
    print(ndt.isoformat_bs())

# Or use the collector method to get a list
month_it = make_iterator("month", start_date)
next_5_months = month_it.take(5)
```

### Using `nepali_range`

For fine-grained control, specifically when providing a strict stop date or custom step size, use the lower-level generator `nepali_range`.

```python
from wisedate.nepali_date import nepali_range, NepaliDateTime

start = NepaliDateTime.from_bs(2081, 9, 1)
stop  = NepaliDateTime.from_bs(2081, 9, 6)

# Provide start, stop, granularity, and step size
days = list(nepali_range(start, stop, granularity="day", step=2))
print([d.bs_day for d in days]) # Output: [1, 3, 5]
```

## Grouping and Analytics (`group_dates`)

The library features a powerful bi-directional analytics engine capable of bucketing arrays of unstructured dates into standard business reporting periods (`month`, `quarter`, `half`, `year`) or dynamic relative windows (e.g., `"today"`, `"last_week"`, `"rolling_30"`, `"आज"`, `"गत_हप्ता"`, `"aaja"`).

It supports native English, Romanized Nepali, and strict Devanagari string queries.

### Examples of Data Grouping

```python
from wisedate.nepali_date import group_dates, NepaliDateTime
import datetime

dates_to_bucket = [
    datetime.date(2026, 1, 15),
    NepaliDateTime.from_bs(2082, 10, 15),
    datetime.date(2026, 4, 6)
]

# 1. Grouping by Relative Phrases (English, Romanized, or Devanagari)
# Evaluates phrases mathematically from a reference date (defaults to today)
res = group_dates(
    dates_to_bucket, 
    by=["today", "yesterday", "this_week"], 
    calendar="AD"
)
# Output: {'This Week': [...], 'Yesterday': [...], 'Today': [...]}

# Devanagari phrases are completely supported natively:
res_nepali = group_dates(dates_to_bucket, by=["आज", "गत_हप्ता", "पछिल्लो_३०_दिन"], calendar="BS")

# 2. Grouping by Financial Period (Quarters, Halves, Months)
res_quarters = group_dates(dates_to_bucket, by="quarter", calendar="BS")
# Output mappings dynamically label the financial quarters spanning specific months: 
# {'BS Q4 2082: Magh–Chaitra': [...], 'BS Q1 2082: Baisakh–Ashadh': [...]}
```

### Supported Grouping Parameters
- **Periods**: `"month"`, `"quarter"`, `"half"`, `"year"`, `"week"`, `"day"`
- **Relative English**: `"today"`, `"yesterday"`, `"tomorrow"`, `"this_week"`, `"last_week"`, `"next_week"`, `"this_month"`, `"last_month"`, `"next_month"`, `"rolling_7"`, `"rolling_30"`
- **Romanized Nepali**: `"aaja"`, `"hijo"`, `"bholi"`
- **Devanagari (Nepali)**: `"आज"`, `"हिजो"`, `"भोलि"`, `"यो_हप्ता"`, `"गत_हप्ता"`, `"आगामी_हप्ता"`, `"यो_महिना"`, `"गत_महिना"`, `"आगामी_महिना"`, `"पछिल्लो_७_दिन"`, `"पछिल्लो_३०_दिन"`

---

## Testing

The library relies on high-performance unit tests. The core logic has been rigorously tested against 130+ years of exact calendar offsets and extensive mathematical mappings.

### Data-Driven Testing (`test_cases.jsonl`)
To guarantee flawless parsing of complex Devanagari strings, Romanized formats, and grouping logic, the analytics engine is evaluated against a structured fixture file: [`test_cases.jsonl`](./test_cases.jsonl). 

Using JSONL (JSON Lines) ensures that complex Unicode (Devanagari) strings do not suffer from encoding corruptions. Each line acts as a complete, independent test scenario passing arrays of dates and asserting specific bucket counts.

A typical Devanagari test case in the file looks like this:
```json
{"input_dates": ["2082-12-22", "2082-12-23", "2082-12-24"], "by": ["आज", "हिजो", "भोलि"], "expected_keys": ["Yesterday", "Today", "Tomorrow"], "expected_counts": {"Yesterday": 1, "Today": 1, "Tomorrow": 1}, "calendar": "BS"}
```

To run the complete validation suite:

```bash
python test_calendar.py
```

Or via Pytest with standard output attached:
```bash
pytest -s test_calendar.py
```