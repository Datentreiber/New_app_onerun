# blocks/components/gee/no2_time_window.py
"""
Purpose
-------
Ableitung eines Monats-Zeitfensters [start, end) aus (year, month).

Contracts
---------
def month2idx(name: str) -> int
def month_window(year: int, month: int) -> tuple[ee.Date, ee.Date]

Args
----
year : int  (z. B. 2023)
month: int  (1..12)

Returns
-------
(start, end): tuple[ee.Date, ee.Date]
  Start inkl. 1. Tag des Monats; Ende exkl. erster Tag des Folgemonats.

Side Effects
-----------
Keine.
"""

import calendar
import ee

def month2idx(name: str) -> int:
    """Map month name (English) to index (1..12); supports numeric strings too."""
    table = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
    if name.isdigit():
        v = int(name)
        return v if 1 <= v <= 12 else 1
    return table.get(name.strip().lower(), 1)

def month_window(year: int, month: int) -> tuple[ee.Date, ee.Date]:
    """Compute [start, end) ee.Date window for given year and month."""
    if not (isinstance(year, int) and isinstance(month, int)):
        raise ValueError("year and month must be integers")
    if not (1 <= month <= 12):
        raise ValueError("month must be in 1..12")
    start = ee.Date.fromYMD(int(year), int(month), 1)
    if month == 12:
        end = ee.Date.fromYMD(int(year) + 1, 1, 1)
    else:
        end = ee.Date.fromYMD(int(year), int(month) + 1, 1)
    return start, end
