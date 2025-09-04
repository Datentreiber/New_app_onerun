# blocks/components/gee/s2_quarter_window.py
"""
Purpose
-------
Ableitung eines Quartalszeitfensters [start, end) aus (year, quarter).

Contracts
---------
def quarter_window(year: int, quarter: int) -> tuple[ee.Date, ee.Date]

Args
----
year : int     (z. B. 2023)
quarter : int  (1..4; Q1=Jan–Mar, Q2=Apr–Jun, Q3=Jul–Sep, Q4=Oct–Dec)

Returns
-------
(start, end): tuple[ee.Date, ee.Date]
  Start inkl. 1. Tag des Quartals; Ende exkl. erster Tag des Folgemonats nach Quartalsende.

Side Effects
-----------
Keine.
"""

import ee

def quarter_window(year: int, quarter: int) -> tuple[ee.Date, ee.Date]:
    if not (isinstance(year, int) and isinstance(quarter, int)):
        raise ValueError("year and quarter must be integers")
    if not (1 <= quarter <= 4):
        raise ValueError("quarter must be in 1..4")
    start_month = {1: 1, 2: 4, 3: 7, 4: 10}[quarter]
    start = ee.Date.fromYMD(int(year), start_month, 1)
    if quarter == 4:
        end = ee.Date.fromYMD(int(year) + 1, 1, 1)
    else:
        end = ee.Date.fromYMD(int(year), start_month + 3, 1)
    return start, end
