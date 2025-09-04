# blocks/components/gee/no2_acquire_reduce.py
"""
Purpose
-------
NO₂-Monatsmittel als ee.Image bauen:
- Quelle: Sentinel-5P NRTI NO2 L3
- Band: NO2_column_number_density
- Reduktion: Monatsmittel (mean) über [start, end)

Contracts
---------
def build_no2_monthly_image(start: ee.Date, end: ee.Date) -> ee.Image

Args
----
start, end : ee.Date
  Zeitfenster [start, end) für Monatsmittel.

Returns
-------
ee.Image
  Monatsmittelbild (Band 'NO2_column_number_density').

Side Effects
-----------
Keine.

Notes
-----
Dataset/Band exakt wie Vorlage übernommen.
"""

import ee

def build_no2_monthly_image(start: ee.Date, end: ee.Date) -> ee.Image:
    """
    Acquire S5P NRTI NO2 column and compute monthly mean image for [start, end).
    Exact band: 'NO2_column_number_density'.
    """
    collection = (
        ee.ImageCollection("COPERNICUS/S5P/NRTI/L3_NO2")
        .select("NO2_column_number_density")
        .filterDate(start, end)
    )
    image = collection.mean().rename("NO2_column_number_density")
    return image
