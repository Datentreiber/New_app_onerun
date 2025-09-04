# blocks/components/gee/cool_spots_time.py
"""
Purpose
-------
Einheitliche Zeitlogik für den UC 'cool_spots':
Sommerfenster (Jun 1 inkl. → Sep 1 exkl.) aus einem Jahr ableiten.

Contracts
---------
def summer_window(year: int) -> tuple[ee.Date, ee.Date]

Args
----
year : int
    Kalenderjahr (z. B. 2020).

Returns
-------
(start, end) : tuple[ee.Date, ee.Date]
    Start inklusiv (1. Juni), Ende exklusiv (1. September).

Side Effects
------------
Keine.
"""

import ee

def summer_window(year: int) -> tuple[ee.Date, ee.Date]:
    """Return (start:ee.Date, end:ee.Date) for Jun–Sep window."""
    if not isinstance(year, int):
        raise ValueError("year must be int")
    start = ee.Date.fromYMD(int(year), 6, 1)   # inclusive
    end   = ee.Date.fromYMD(int(year), 9, 1)   # exclusive
    return start, end
